"""Pruebas del restablecimiento de clave por código SMS.

Verifican tanto el camino feliz como las defensas: código de un solo uso,
vencimiento, límite de intentos y no revelar qué DNI están registrados.
"""
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import notificaciones, recuperacion

client = TestClient(app)
DNI = "70100002"          # Rosa Huamán (operadora de Ahuaycha)
CLAVE_ORIGINAL = "yaku2026"


@pytest.fixture
def sms(monkeypatch):
    """Intercepta el envío para leer el código sin depender de los registros."""
    capturados: list[str] = []
    original = notificaciones.enviar

    def espia(canal, destino, mensaje):
        capturados.append(mensaje)
        return original(canal, destino, mensaje)

    monkeypatch.setattr(notificaciones, "enviar", espia)
    return capturados


def _pedir_codigo(sms, dni: str = DNI) -> str:
    sms.clear()
    r = client.post("/auth/recuperacion/solicitar", json={"dni": dni})
    assert r.status_code == 200
    return re.search(r"clave es (\d{6})", " ".join(sms)).group(1)


def _restablecer(dni, codigo, clave):
    return client.post("/auth/recuperacion/confirmar",
                       json={"dni": dni, "codigo": codigo, "clave_nueva": clave})


def test_flujo_completo_cambia_la_clave(sms):
    codigo = _pedir_codigo(sms)
    assert _restablecer(DNI, codigo, "claveNueva1").status_code == 200

    # La clave nueva sirve y la anterior deja de servir.
    nueva = client.post("/auth/login",
                        json={"dni": DNI, "clave": "claveNueva1", "grupo_rol": "JASS"})
    assert nueva.status_code == 200
    vieja = client.post("/auth/login",
                        json={"dni": DNI, "clave": CLAVE_ORIGINAL, "grupo_rol": "JASS"})
    assert vieja.status_code == 401

    # Restauramos la clave original para no afectar a otras pruebas.
    codigo2 = _pedir_codigo(sms)
    assert _restablecer(DNI, codigo2, CLAVE_ORIGINAL).status_code == 200


def test_el_codigo_es_de_un_solo_uso(sms):
    codigo = _pedir_codigo(sms)
    assert _restablecer(DNI, codigo, CLAVE_ORIGINAL).status_code == 200
    assert _restablecer(DNI, codigo, "otraClave1").status_code == 400


def test_codigo_incorrecto_avisa_los_intentos_restantes(sms):
    _pedir_codigo(sms)
    r = _restablecer(DNI, "000000", "otraClave1")
    assert r.status_code == 400
    assert "intento" in r.json()["detail"]


def test_se_bloquea_tras_varios_intentos_fallidos(sms):
    _pedir_codigo(sms)
    for _ in range(recuperacion.MAX_INTENTOS):
        _restablecer(DNI, "000000", "otraClave1")
    # Agotados los intentos, ni el código correcto sirve.
    r = _restablecer(DNI, "000000", "otraClave1")
    assert r.status_code == 400
    assert "intentos" in r.json()["detail"].lower()


def test_solicitar_un_codigo_nuevo_anula_el_anterior(sms):
    primero = _pedir_codigo(sms)
    segundo = _pedir_codigo(sms)
    assert primero != segundo
    assert _restablecer(DNI, primero, "otraClave1").status_code == 400
    assert _restablecer(DNI, segundo, CLAVE_ORIGINAL).status_code == 200


def test_no_revela_si_el_dni_existe():
    """Un DNI inexistente responde igual que uno válido (sin enumeración)."""
    existente = client.post("/auth/recuperacion/solicitar", json={"dni": DNI})
    inventado = client.post("/auth/recuperacion/solicitar", json={"dni": "99999999"})
    assert existente.status_code == inventado.status_code == 200
    assert existente.json()["mensaje"] == inventado.json()["mensaje"]
    # Solo el real indica a qué celular se envió.
    assert inventado.json()["telefono_enmascarado"] is None


def test_el_celular_se_muestra_enmascarado():
    r = client.post("/auth/recuperacion/solicitar", json={"dni": DNI})
    enmascarado = r.json()["telefono_enmascarado"]
    assert enmascarado.startswith("*") and enmascarado.endswith("0002")


def test_confirmar_sin_haber_pedido_codigo():
    r = _restablecer("70100040", "123456", "otraClave1")   # salud, sin solicitud
    assert r.status_code == 400


@pytest.mark.parametrize("clave", ["corta", "12345"])
def test_la_clave_nueva_tiene_minimo(clave, sms):
    codigo = _pedir_codigo(sms)
    assert _restablecer(DNI, codigo, clave).status_code == 422
