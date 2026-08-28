"""Pruebas de la entidad y el ámbito de una cuenta.

La entidad no se teclea: se deduce del actor y del territorio, igual que el
código de un reservorio. Escrita a mano, la misma junta acabaría registrada
como «JASS COM-01», «Jass com 01» y «JASS de la comunidad 01», y el padrón
dejaría de poder agruparse por entidad.
"""
import random

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CLAVE = "yaku2026"


def _auth(dni: str, grupo: str) -> dict:
    r = client.post("/auth/login", json={"dni": dni, "clave": CLAVE, "grupo_rol": grupo})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _atm() -> dict:
    return _auth("70100020", "ATM")


def _admin() -> dict:
    return _auth("70100099", "ADMIN")


def _identidad() -> tuple[str, str]:
    n = random.randint(10_000_000, 79_999_999)
    return str(n), f"9{n % 100_000_000:08d}"


def _alta(headers: dict, rol: str, **extra):
    dni, telefono = _identidad()
    cuerpo = {"nombres": "Cuenta de prueba", "dni": dni, "telefono": telefono,
              "clave": "clave12345", "rol": rol}
    cuerpo.update(extra)
    return client.post("/admin/usuarios", headers=headers, json=cuerpo)


def _comunidad(headers: dict, nombre: str = "COM-01") -> dict:
    return next(c for c in client.get("/admin/comunidades", headers=headers).json()
                if c["nombre"] == nombre)


# ─── La entidad se deduce ────────────────────────────────────────
def test_una_cuenta_de_jass_hereda_el_nombre_de_su_junta():
    h = _atm()
    com = _comunidad(h)
    r = _alta(h, "OPERADOR", comunidad_id=com["comunidad_id"])
    assert r.status_code == 201, r.text
    assert r.json()["entidad"] == com["jass_nombre"] == "JASS COM-01"


def test_la_atm_se_nombra_por_su_municipalidad():
    """Las cuentas ATM las crea el ADMIN, indicando de qué distrito son."""
    h = _admin()
    lircay = next(u for u in client.get("/admin/ubigeos", headers=h).json()
                  if u["distrito"] == "LIRCAY")
    r = _alta(h, "ATM", ubigeo_id=lircay["ubigeo_id"])
    assert r.status_code == 201, r.text
    assert r.json()["entidad"] == "Municipalidad Distrital de Lircay"


def test_las_cuentas_regionales_no_dependen_del_territorio():
    h = _admin()
    assert _alta(h, "DESA").json()["entidad"] == "DIRESA Huancavelica"
    assert _alta(h, "DRVCS").json()["entidad"] == "Dirección Regional de Vivienda y Saneamiento"


def test_el_promotor_dice_a_que_comunidad_difunde():
    h = _atm()
    com = _comunidad(h, "COM-02")
    r = _alta(h, "POBLACION", comunidad_id=com["comunidad_id"])
    assert r.status_code == 201, r.text
    assert r.json()["entidad"] == "Difusión a la población · COM-02"


def test_una_entidad_explicita_se_respeta():
    """Para cargas históricas, donde el nombre real ya existe."""
    h = _atm()
    com = _comunidad(h)
    r = _alta(h, "OPERADOR", comunidad_id=com["comunidad_id"],
              entidad="JASS Santa Rosa (padrón 2019)")
    assert r.json()["entidad"] == "JASS Santa Rosa (padrón 2019)"


# ─── El ámbito decide qué territorio hace falta ──────────────────
def test_una_cuenta_comunal_sin_comunidad_se_rechaza():
    """Un operador sin comunidad no tiene reservorio que medir."""
    r = _alta(_atm(), "OPERADOR")
    assert r.status_code == 422, r.text
    assert "comunidad concreta" in r.json()["detail"]


def test_un_promotor_sin_comunidad_se_rechaza():
    """Sin comunidad no tiene a quién avisar."""
    assert _alta(_atm(), "POBLACION").status_code == 422


def test_una_cuenta_distrital_no_se_encierra_en_una_comunidad():
    """Asignarla a una la dejaría fuera de las demás del distrito."""
    h = _admin()
    r = _alta(h, "ATM", comunidad_id=_comunidad(h)["comunidad_id"])
    assert r.status_code == 422, r.text
    assert "distrital o regional" in r.json()["detail"]


def test_una_cuenta_comunal_hereda_el_distrito_de_su_comunidad():
    h = _atm()
    com = _comunidad(h, "COM-03")
    r = _alta(h, "OPERADOR", comunidad_id=com["comunidad_id"])
    assert r.json()["distrito"] == "LIRCAY"
    assert r.json()["comunidad"] == "COM-03"


# ─── El catálogo lo anticipa ─────────────────────────────────────
def test_cada_actor_publica_su_ambito_y_como_se_nombrara():
    actores = {a["actor"]: a for a in client.get("/admin/actores", headers=_atm()).json()}
    assert actores["JASS"]["ambito"] == "comunidad"
    assert actores["ATM"]["ambito"] == "distrito"
    assert actores["DESA"]["ambito"] == "regional"
    assert actores["JASS"]["entidad_ejemplo"].startswith("JASS ")
    assert actores["ATM"]["entidad_ejemplo"] == "Municipalidad Distrital de Lircay"


def test_el_admin_ve_un_ejemplo_concreto_pese_a_no_tener_distrito():
    """Sin esto el ejemplo decía «Municipalidad Distrital de su distrito»."""
    actores = {a["actor"]: a for a in client.get("/admin/actores", headers=_admin()).json()}
    assert "su distrito" not in actores["ATM"]["entidad_ejemplo"]
    assert actores["ATM"]["entidad_ejemplo"].startswith("Municipalidad Distrital de ")
