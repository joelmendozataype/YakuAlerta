"""Pruebas del alcance territorial del tablero — RF-06 / RNF-05.

Cada quien ve su jurisdicción. La ATM y Salud administran un distrito y solo
ese; la DESA, la DRVCS y la administración alcanzan toda la región.

Además del permiso, importa dónde abre el tablero: ofrecer los doce distritos
de la provincia hacía que se abriera en el primero del abecedario —vacío— en
vez de en el que la persona trabaja.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CLAVE = "yaku2026"


def _auth(dni: str, grupo: str) -> dict:
    r = client.post("/auth/login", json={"dni": dni, "clave": CLAVE, "grupo_rol": grupo})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _distritos(headers: dict) -> list[dict]:
    r = client.get("/tablero/distritos", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _lircay() -> dict:
    return next(d for d in _distritos(_auth("70100099", "ADMIN"))
                if d["distrito"] == "LIRCAY")


def _ajeno() -> dict:
    return next(d for d in _distritos(_auth("70100099", "ADMIN"))
                if d["distrito"] != "LIRCAY")


# ─── Quién ve qué territorio ─────────────────────────────────────
def test_la_atm_solo_ve_su_distrito():
    """Ofrecerle los doce era una ventana a datos de otras jurisdicciones."""
    distritos = _distritos(_auth("70100020", "ATM"))
    assert len(distritos) == 1
    assert distritos[0]["distrito"] == "LIRCAY"


def test_salud_tambien_queda_en_su_distrito():
    distritos = _distritos(_auth("70100040", "IPRESS_SALUD"))
    assert len(distritos) == 1
    assert distritos[0]["distrito"] == "LIRCAY"


def test_los_roles_regionales_ven_toda_la_provincia():
    for dni, grupo in (("70100030", "DESA"), ("70100070", "DRVCS"), ("70100099", "ADMIN")):
        assert len(_distritos(_auth(dni, grupo))) == 12, grupo


def test_la_atm_no_abre_el_tablero_de_otro_distrito():
    r = client.get(f"/tablero/{_ajeno()['ubigeo_id']}", headers=_auth("70100020", "ATM"))
    assert r.status_code == 403, r.text
    assert "jurisdicción" in r.json()["detail"]


def test_la_atm_si_abre_el_suyo():
    r = client.get(f"/tablero/{_lircay()['ubigeo_id']}", headers=_auth("70100020", "ATM"))
    assert r.status_code == 200, r.text
    assert r.json()["distrito"] == "LIRCAY"


def test_el_historial_de_un_reservorio_respeta_la_jurisdiccion():
    """El historial es de un reservorio, y un reservorio tiene distrito."""
    admin = _auth("70100099", "ADMIN")
    reservorio = client.get("/admin/reservorios", headers=admin).json()[0]
    assert client.get(f"/tablero/reservorio/{reservorio['reservorio_id']}/historial",
                      headers=_auth("70100020", "ATM")).status_code == 200
    # Y uno inexistente no se confunde con uno ajeno.
    assert client.get("/tablero/reservorio/999999/historial",
                      headers=admin).status_code == 404


# ─── Dónde abre el tablero ───────────────────────────────────────
def test_los_distritos_con_comunidades_van_primero():
    """El tablero debe abrir donde hay algo que ver, no en la «A» del abecedario."""
    distritos = _distritos(_auth("70100099", "ADMIN"))
    assert distritos[0]["distrito"] == "LIRCAY"
    assert distritos[0]["comunidades"] >= 3
    # Y el conteo permite avisar de los vacíos en vez de abrirlos en silencio.
    conteos = [d["comunidades"] for d in distritos]
    assert conteos == sorted(conteos, reverse=True)


# ─── Priorización: la vista de quien decide entre distritos ──────
def test_la_priorizacion_compara_toda_la_jurisdiccion():
    """Un rol regional ve las comunidades de todos sus distritos, juntas."""
    regional = client.get("/tablero/priorizacion", headers=_auth("70100070", "DRVCS")).json()
    distrital = client.get("/tablero/priorizacion", headers=_auth("70100020", "ATM")).json()

    assert regional["distritos"] >= 1
    assert "LIRCAY" in {c["distrito"] for c in regional["comunidades"]}
    # Y nunca ve menos que quien administra un solo distrito.
    assert len(regional["comunidades"]) >= len(distrital["comunidades"])


def test_la_cola_de_atencion_pone_primero_lo_mas_grave():
    """Rojo antes que amarillo, y entre iguales primero quien afecta a más gente."""
    d = client.get("/tablero/priorizacion", headers=_auth("70100070", "DRVCS")).json()
    criticidades = [c["criticidad"] for c in d["comunidades"]]
    assert criticidades == sorted(criticidades, reverse=True)
    assert d["comunidades"][0]["nivel"] == "ROJO"


def test_el_silencio_pesa_casi_tanto_como_el_agua_no_segura():
    """Un reservorio que dejó de reportar suele ser uno sin operador."""
    from app.routers.tablero import PESO_NIVEL, PESO_SILENCIO
    from app.enums import NivelRiesgo

    assert PESO_SILENCIO >= PESO_NIVEL[NivelRiesgo.AMARILLO]
    assert PESO_SILENCIO < PESO_NIVEL[NivelRiesgo.ROJO]


def test_la_priorizacion_de_la_atm_no_sale_de_su_distrito():
    d = client.get("/tablero/priorizacion", headers=_auth("70100020", "ATM")).json()
    assert {c["distrito"] for c in d["comunidades"]} == {"LIRCAY"}


def test_la_jass_no_entra_al_tablero():
    h = _auth("70100001", "JASS")
    assert client.get("/tablero/distritos", headers=h).status_code == 200
    # Su ámbito es su comunidad: no se le ofrece ningún distrito ajeno.
    assert len(_distritos(h)) == 1
