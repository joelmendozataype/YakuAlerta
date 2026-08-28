"""Pruebas de la administración delegada al Área Técnica Municipal.

La ATM administra su distrito, pero no puede salir de él ni crear cuentas de
rango superior al suyo (RNF-05, mínimo privilegio).
"""
import random

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CLAVE = "yaku2026"


def _auth(dni: str) -> dict:
    grupo = {"70100020": "ATM", "70100001": "JASS", "70100040": "IPRESS_SALUD"}[dni]
    r = client.post("/auth/login", json={"dni": dni, "clave": CLAVE, "grupo_rol": grupo})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _admin() -> dict:
    r = client.post("/auth/login", json={"telefono": "987000099", "clave": CLAVE})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


ATM = "70100020"


def _identidad_nueva() -> tuple[str, str]:
    """DNI y celular libres, para que las pruebas puedan repetirse."""
    n = random.randint(10_000_000, 79_999_999)
    return str(n), f"9{n % 100_000_000:08d}"


def test_la_atm_administra_su_distrito():
    h = _auth(ATM)
    assert client.get("/admin/comunidades", headers=h).status_code == 200
    assert client.get("/admin/reservorios", headers=h).status_code == 200
    assert client.get("/admin/usuarios", headers=h).status_code == 200


def test_la_atm_solo_ve_su_distrito():
    """Sus listados quedan acotados a su ubigeo."""
    h = _auth(ATM)
    ubigeos = client.get("/admin/ubigeos", headers=h).json()
    assert len(ubigeos) == 1 and ubigeos[0]["distrito"] == "LIRCAY"


def test_la_atm_registra_perfiles_de_campo():
    h = _auth(ATM)
    dni, telefono = _identidad_nueva()
    r = client.post("/admin/usuarios", headers=h, json={
        "nombres": "Operador de prueba", "dni": dni,
        "telefono": telefono, "clave": "clave12345",
        "rol": "OPERADOR",
    })
    assert r.status_code == 201, r.text
    # La cuenta nace en el distrito de la ATM que la registró.
    assert r.json()["ubigeo_id"] is not None


@pytest.mark.parametrize("rol", ["ADMIN", "DESA", "DRVCS"])
def test_la_atm_no_puede_crear_cuentas_de_rango_superior(rol):
    """Impide el escalamiento de privilegios."""
    h = _auth(ATM)
    dni, telefono = _identidad_nueva()
    r = client.post("/admin/usuarios", headers=h, json={
        "nombres": f"Intento {rol}", "dni": dni,
        "telefono": telefono, "clave": "clave12345", "rol": rol,
    })
    assert r.status_code == 403
    assert "DIRESA" in r.json()["detail"] or "campo" in r.json()["detail"]


def test_la_atm_no_puede_crear_en_otro_distrito():
    h = _auth(ATM)
    r = client.post("/admin/comunidades", headers=h,
                    json={"ubigeo_id": 9999, "nombre": "Comunidad ajena"})
    assert r.status_code == 403
    assert "distrito" in r.json()["detail"]


def test_el_administrador_regional_conserva_alcance_total():
    dni, telefono = _identidad_nueva()
    r = client.post("/admin/usuarios", headers=_admin(), json={
        "nombres": "Especialista regional", "dni": dni,
        "telefono": telefono, "clave": "clave12345", "rol": "DESA",
    })
    assert r.status_code == 201


@pytest.mark.parametrize("dni", ["70100001", "70100040"])
def test_los_demas_roles_no_administran(dni):
    """Operador y salud no acceden a la administración."""
    assert client.get("/admin/usuarios", headers=_auth(dni)).status_code == 403
