"""Pruebas del inicio de sesión por código QR (vinculación web ↔ móvil).

Cubren el camino feliz y las defensas: un solo uso, secreto de cliente,
rechazo desde la app y estados inválidos.

Quien vincula un dispositivo es quien trabaja en el tablero (ATM, Salud, DESA,
DRVCS, población). La JASS no: su trabajo ocurre en la app móvil.
"""
import hashlib
import random
import secrets

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CLAVE = "yaku2026"


def _sha(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def _auth_movil(telefono: str = "987000020") -> dict:
    r = client.post("/auth/login", json={"telefono": telefono, "clave": CLAVE})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def qr():
    """Crea una sesión QR nueva y devuelve (token, client_secret)."""
    client_secret = secrets.token_urlsafe(24)
    r = client.post("/auth/qr/nueva", json={"client_hash": _sha(client_secret)})
    assert r.status_code == 201, r.text
    return r.json()["token"], client_secret


def test_flujo_completo_de_vinculacion(qr):
    token, client_secret = qr
    h = _auth_movil()

    # La web sondea: aún nadie escaneó.
    assert client.get(f"/auth/qr/{token}").json()["estado"] == "PENDIENTE"

    # La app escanea: la web ya puede mostrar de quién es la sesión.
    r = client.post(f"/auth/qr/{token}/escanear", headers=h)
    assert r.status_code == 200
    assert r.json()["estado"] == "ESCANEADO"
    assert r.json()["usuario_nombres"]

    # El usuario confirma en la app.
    r = client.post(f"/auth/qr/{token}/confirmar", headers=h, json={"aprobar": True})
    assert r.json()["estado"] == "APROBADO"

    # El sondeo NUNCA entrega el token de sesión.
    assert client.get(f"/auth/qr/{token}").json()["sesion"] is None

    # La web reclama presentando su secreto y obtiene el acceso.
    r = client.post(f"/auth/qr/{token}/reclamar", json={"client_secret": client_secret})
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]
    assert r.json()["usuario"]["rol"] == "ATM"


def test_el_codigo_es_de_un_solo_uso(qr):
    token, client_secret = qr
    h = _auth_movil()
    client.post(f"/auth/qr/{token}/escanear", headers=h)
    client.post(f"/auth/qr/{token}/confirmar", headers=h, json={"aprobar": True})
    client.post(f"/auth/qr/{token}/reclamar", json={"client_secret": client_secret})

    # El segundo intento debe fallar: la sesión quedó consumida.
    r = client.post(f"/auth/qr/{token}/reclamar", json={"client_secret": client_secret})
    assert r.status_code == 409


def test_sin_el_secreto_no_se_obtiene_la_sesion(qr):
    """Fotografiar el QR no basta: hace falta el secreto del navegador."""
    token, _ = qr
    h = _auth_movil()
    client.post(f"/auth/qr/{token}/escanear", headers=h)
    client.post(f"/auth/qr/{token}/confirmar", headers=h, json={"aprobar": True})

    r = client.post(f"/auth/qr/{token}/reclamar", json={"client_secret": "secreto-falso"})
    assert r.status_code == 403


def test_el_usuario_puede_rechazar_desde_la_app(qr):
    token, client_secret = qr
    h = _auth_movil()
    client.post(f"/auth/qr/{token}/escanear", headers=h)
    r = client.post(f"/auth/qr/{token}/confirmar", headers=h, json={"aprobar": False})
    assert r.json()["estado"] == "RECHAZADO"

    r = client.post(f"/auth/qr/{token}/reclamar", json={"client_secret": client_secret})
    assert r.status_code == 409


def test_escanear_exige_sesion_en_el_movil(qr):
    token, _ = qr
    r = client.post(f"/auth/qr/{token}/escanear")   # sin cabecera de autenticación
    assert r.status_code == 401


def test_solo_quien_escaneo_puede_confirmar(qr):
    token, _ = qr
    client.post(f"/auth/qr/{token}/escanear", headers=_auth_movil("987000020"))
    otro = _auth_movil("987000040")
    r = client.post(f"/auth/qr/{token}/confirmar", headers=otro, json={"aprobar": True})
    assert r.status_code == 403


def test_token_inexistente(qr):
    assert client.get("/auth/qr/token-que-no-existe").status_code == 404


def test_la_jass_no_vincula_dispositivos_web(qr):
    """El QR no puede reabrir la puerta que el tablero ya no le ofrece."""
    token, client_secret = qr
    operador = client.post("/auth/login", json={"telefono": "987000001", "clave": CLAVE})
    h = {"Authorization": f"Bearer {operador.json()['access_token']}"}

    # Escanea y aprueba desde su app sin problema: el corte llega al final.
    assert client.post(f"/auth/qr/{token}/escanear", headers=h).status_code == 200
    assert client.post(f"/auth/qr/{token}/confirmar", headers=h,
                       json={"aprobar": True}).status_code == 200

    r = client.post(f"/auth/qr/{token}/reclamar", json={"client_secret": client_secret})
    assert r.status_code == 403
    assert "app móvil" in r.json()["detail"]

    # La sesión queda inutilizable: no se puede reintentar.
    r = client.post(f"/auth/qr/{token}/reclamar", json={"client_secret": client_secret})
    assert r.status_code != 200


def test_el_directivo_jass_tampoco_vincula(qr):
    token, client_secret = qr
    atm = client.post("/auth/login", json={"telefono": "987000020", "clave": CLAVE})
    n = random.randint(10_000_000, 79_999_999)
    alta = client.post("/admin/usuarios",
                       headers={"Authorization": f"Bearer {atm.json()['access_token']}"},
                       json={"nombres": "Directivo de prueba", "dni": str(n),
                             "telefono": f"9{n % 100_000_000:08d}", "clave": "clave12345",
                             "rol": "DIRECTIVO_JASS"})
    assert alta.status_code == 201, alta.text

    d = client.post("/auth/login", json={"dni": str(n), "clave": "clave12345"})
    h = {"Authorization": f"Bearer {d.json()['access_token']}"}
    client.post(f"/auth/qr/{token}/escanear", headers=h)
    client.post(f"/auth/qr/{token}/confirmar", headers=h, json={"aprobar": True})
    r = client.post(f"/auth/qr/{token}/reclamar", json={"client_secret": client_secret})
    assert r.status_code == 403
    assert "app móvil" in r.json()["detail"]


def test_salud_si_vincula_su_dispositivo(qr):
    """La regla corta a la JASS, no al resto: Salud sí trabaja en el tablero."""
    token, client_secret = qr
    h = _auth_movil("987000040")
    client.post(f"/auth/qr/{token}/escanear", headers=h)
    client.post(f"/auth/qr/{token}/confirmar", headers=h, json={"aprobar": True})
    r = client.post(f"/auth/qr/{token}/reclamar", json={"client_secret": client_secret})
    assert r.status_code == 200, r.text
    assert r.json()["usuario"]["rol"] == "SALUD"


def test_el_vecino_tampoco_vincula_dispositivos_web(qr):
    """Su rol existe para recibir la alerta, no para navegar un tablero."""
    token, client_secret = qr
    v = client.post("/auth/login", json={"telefono": "987000060", "clave": CLAVE})
    h = {"Authorization": f"Bearer {v.json()['access_token']}"}
    client.post(f"/auth/qr/{token}/escanear", headers=h)
    client.post(f"/auth/qr/{token}/confirmar", headers=h, json={"aprobar": True})
    r = client.post(f"/auth/qr/{token}/reclamar", json={"client_secret": client_secret})
    assert r.status_code == 403
    # Se le indica su propia puerta, que no es la de la JASS.
    assert "QR del aviso" in r.json()["detail"]
