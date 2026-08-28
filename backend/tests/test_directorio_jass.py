"""Pruebas del directorio de JASS que acompaña la ATM.

Regla del dominio: **una JASS por comunidad** (administra un solo sistema de
agua) y **una ATM por distrito**, que acompaña a todas las de su jurisdicción.
"""
import random

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CLAVE = "yaku2026"
ATM = "70100020"
OPERADOR = "70100001"
SALUD = "70100040"

GRUPO = {ATM: "ATM", OPERADOR: "JASS", SALUD: "IPRESS_SALUD"}


def _auth(dni: str) -> dict:
    r = client.post("/auth/login", json={"dni": dni, "clave": CLAVE, "grupo_rol": GRUPO[dni]})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _admin() -> dict:
    r = client.post("/auth/login", json={"telefono": "987000099", "clave": CLAVE})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _jass_de(headers: dict) -> list[dict]:
    r = client.get("/admin/jass", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_la_atm_ve_las_jass_de_su_distrito():
    """Varias juntas bajo una sola ATM."""
    jass = _jass_de(_auth(ATM))
    assert len(jass) >= 3
    assert {j["comunidad"] for j in jass} >= {"COM-01", "COM-02", "COM-03"}


def test_cada_comunidad_tiene_una_sola_jass():
    """La relación comunidad↔JASS es 1:1: ninguna comunidad se repite."""
    jass = _jass_de(_auth(ATM))
    comunidades = [j["comunidad_id"] for j in jass]
    assert len(comunidades) == len(set(comunidades))


def test_cada_jass_trae_a_su_gente():
    """Cada junta lista a los suyos, y solo a los suyos."""
    jass = {j["comunidad"]: j for j in _jass_de(_auth(ATM))}
    uno = jass["COM-01"]
    assert "OPERADOR" in {m["rol"] for m in uno["miembros"]}

    # Nadie de otra comunidad se cuela en esta junta.
    ajenos = {m["usuario_id"] for j in jass.values() if j["comunidad"] != "COM-01"
              for m in j["miembros"]}
    assert not ajenos & {m["usuario_id"] for m in uno["miembros"]}


def test_la_jass_reporta_su_estado_y_su_silencio():
    jass = {j["comunidad"]: j for j in _jass_de(_auth(ATM))}
    assert jass["COM-03"]["nivel"] == "ROJO"      # medición turbia del seed
    assert jass["COM-01"]["reservorios"] >= 1
    for j in jass.values():
        assert j["en_silencio"] is (j["dias_sin_medir"] is None
                                    or j["dias_sin_medir"] > 7)


def test_una_jass_nueva_aparece_en_el_directorio_de_su_atm():
    h = _auth(ATM)
    ubigeo = client.get("/admin/ubigeos", headers=h).json()[0]["ubigeo_id"]
    nombre = f"Comunidad de prueba {random.randint(1000, 9999)}"
    r = client.post("/admin/comunidades", headers=h, json={
        "ubigeo_id": ubigeo, "nombre": nombre,
        "jass_nombre": f"JASS {nombre}", "poblacion_servida": 150,
    })
    assert r.status_code == 201, r.text

    nueva = next(j for j in _jass_de(h) if j["comunidad"] == nombre)
    assert nueva["jass_nombre"] == f"JASS {nombre}"
    # Sin reservorios ni mediciones nace en silencio: la ATM la ve pendiente.
    assert nueva["reservorios"] == 0
    assert nueva["en_silencio"] is True
    assert nueva["miembros"] == []


def test_el_admin_ve_las_jass_de_toda_la_region():
    assert len(_jass_de(_admin())) >= len(_jass_de(_auth(ATM)))


def test_salud_no_administra_el_directorio_de_jass():
    """El directorio es administración: no es el ámbito de Salud."""
    assert client.get("/admin/jass", headers=_auth(SALUD)).status_code == 403


def test_el_operador_no_administra_el_directorio():
    """La JASS opera su sistema; no administra el padrón del distrito."""
    assert client.get("/admin/jass", headers=_auth(OPERADOR)).status_code == 403


def test_el_directorio_exige_sesion():
    assert client.get("/admin/jass").status_code in (401, 403)
