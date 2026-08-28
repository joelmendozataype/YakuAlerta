"""Pruebas del acceso de los perfiles regionales (DESA y DRVCS) al tablero.

Cada uno accede a lo que su función requiere y nada más: la DESA aporta el
laboratorio y el dictamen sanitario; la DRVCS consulta consolidados y silencio
de datos para focalizar la inversión.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CLAVE = "yaku2026"

# Los perfiles regionales entran por el tablero web, con celular.
TELEFONOS = {"DESA": "987000030", "DRVCS": "987000070", "ATM": "987000020"}


def _auth(rol: str) -> dict:
    r = client.post("/auth/login", json={"telefono": TELEFONOS[rol], "clave": CLAVE})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.parametrize("rol", ["DESA", "DRVCS"])
def test_los_perfiles_regionales_consultan_el_tablero(rol):
    assert client.get("/tablero/1", headers=_auth(rol)).status_code == 200


@pytest.mark.parametrize("rol", ["DESA", "DRVCS", "ATM"])
def test_pueden_descargar_el_consolidado(rol):
    r = client.get("/reportes/vigilancia?ubigeo_id=1&periodo=2026-08&formato=pdf",
                   headers=_auth(rol))
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")


def test_la_drvcs_consulta_el_silencio_de_datos():
    """Es su señal de priorización: dónde la vigilancia dejó de reportar."""
    r = client.get("/reportes/silencio", headers=_auth("DRVCS"))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_solo_la_desa_registra_laboratorio():
    cuerpo = {
        "reservorio_id": 1, "parametro": "coliformes_totales", "valor": 12,
        "unidad": "UFC/100mL", "dictamen": "CONFORME", "fecha_muestreo": "2026-08-20",
    }
    assert client.post("/laboratorio", headers=_auth("DESA"), json=cuerpo).status_code == 201
    # La DRVCS es rectoría de saneamiento, no autoridad sanitaria.
    assert client.post("/laboratorio", headers=_auth("DRVCS"), json=cuerpo).status_code == 403


def test_la_drvcs_no_cierra_alertas():
    """El cierre sanitario corresponde a la ATM y a la DESA."""
    alertas = client.get("/alertas?estado=ACTIVA", headers=_auth("DRVCS")).json()
    if not alertas:
        pytest.skip("No hay alertas activas en la base de demostración")
    r = client.post(f"/alertas/{alertas[0]['alerta_id']}/cerrar",
                    headers=_auth("DRVCS"),
                    json={"resultado_cierre": "intento", "dictamen_desa": False})
    assert r.status_code == 403


def test_los_regionales_no_administran_entidades():
    """La administración del directorio es de la ATM en su distrito."""
    for rol in ("DESA", "DRVCS"):
        assert client.get("/admin/usuarios", headers=_auth(rol)).status_code == 403
