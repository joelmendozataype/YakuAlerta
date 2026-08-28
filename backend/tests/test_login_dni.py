"""Pruebas del ingreso por DNI y grupo de rol (pantalla de la app).

Reglas verificadas: el DNI identifica al usuario, el grupo elegido debe
corresponder a su rol, y el tablero web conserva el acceso por celular.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CLAVE = "yaku2026"


def _login(**kwargs):
    return client.post("/auth/login", json={"clave": CLAVE, **kwargs})


@pytest.mark.parametrize("dni,grupo,rol_esperado", [
    ("70100001", "JASS", "OPERADOR"),          # operador de la JASS
    ("70100010", "JASS", "DIRECTIVO_JASS"),    # directivo, mismo grupo
    ("70100020", "ATM", "ATM"),
    ("70100050", "ATM", "AUTORIDAD_LOCAL"),    # autoridad local, grupo ATM
    ("70100040", "IPRESS_SALUD", "SALUD"),
    ("70100060", "USUARIO", "POBLACION"),
])
def test_ingreso_por_dni_con_su_grupo(dni, grupo, rol_esperado):
    r = _login(dni=dni, grupo_rol=grupo)
    assert r.status_code == 200, r.text
    assert r.json()["usuario"]["rol"] == rol_esperado
    assert r.json()["usuario"]["dni"] == dni


def test_el_grupo_equivocado_no_deja_entrar():
    """Un operador que elige «IPRESS/SALUD» no debe acceder."""
    r = _login(dni="70100001", grupo_rol="IPRESS_SALUD")
    assert r.status_code == 403
    assert "rol seleccionado" in r.json()["detail"]


def test_el_mensaje_sugiere_el_grupo_correcto():
    r = _login(dni="70100040", grupo_rol="JASS")
    assert r.status_code == 403
    assert "IPRESS_SALUD" in r.json()["detail"]


def test_dni_inexistente():
    r = _login(dni="99999999", grupo_rol="JASS")
    assert r.status_code == 401
    assert "DNI" in r.json()["detail"]


def test_clave_incorrecta():
    r = client.post("/auth/login",
                    json={"dni": "70100001", "clave": "otra", "grupo_rol": "JASS"})
    assert r.status_code == 401


@pytest.mark.parametrize("dni", ["70100", "abcdefgh", "701000011"])
def test_dni_con_formato_invalido(dni):
    assert _login(dni=dni, grupo_rol="JASS").status_code == 422


def test_sin_identificador():
    assert client.post("/auth/login", json={"clave": CLAVE}).status_code == 422


def test_el_tablero_web_sigue_entrando_por_celular():
    r = _login(telefono="987000020")
    assert r.status_code == 200
    assert r.json()["usuario"]["rol"] == "ATM"


def test_el_dni_es_unico_por_usuario():
    dnis = [_login(dni=d, grupo_rol=g).json()["usuario"]["dni"]
            for d, g in [("70100001", "JASS"), ("70100002", "JASS")]]
    assert len(set(dnis)) == 2


# ── Perfiles regionales: ingresan al tablero web con su propio grupo ──
@pytest.mark.parametrize("dni,grupo,rol_esperado", [
    ("70100030", "DESA", "DESA"),
    ("70100070", "DRVCS", "DRVCS"),
    ("70100099", "ADMIN", "ADMIN"),
])
def test_ingreso_de_los_perfiles_regionales(dni, grupo, rol_esperado):
    r = _login(dni=dni, grupo_rol=grupo)
    assert r.status_code == 200, r.text
    assert r.json()["usuario"]["rol"] == rol_esperado


def test_un_perfil_regional_no_entra_por_un_grupo_de_campo():
    """La DESA que elige «JASS» recibe el mismo rechazo que cualquiera."""
    r = _login(dni="70100030", grupo_rol="JASS")
    assert r.status_code == 403
    assert "DESA" in r.json()["detail"]


def test_la_sesion_indica_el_territorio():
    """La app y el tablero encabezan sus pantallas con provincia y distrito."""
    u = _login(dni="70100001", grupo_rol="JASS").json()["usuario"]
    assert u["departamento"] == "HUANCAVELICA"
    assert u["provincia"] == "ANGARAES"
    assert u["distrito"] == "LIRCAY"
