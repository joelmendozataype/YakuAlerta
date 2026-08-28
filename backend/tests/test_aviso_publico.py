"""Pruebas del aviso comunitario y de la consulta pública del estado del agua.

El QR del afiche debe poder abrirse **sin credenciales** por cualquier vecino,
y no debe exponer datos personales ni valores técnicos.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _auth_atm() -> dict:
    r = client.post("/auth/login", json={"telefono": "987000020", "clave": "yaku2026"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_la_pagina_publica_no_exige_credenciales():
    r = client.get("/publico/comunidad/1")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Yakuni" in r.text


def test_la_pagina_publica_es_apta_para_celular():
    texto = client.get("/publico/comunidad/1").text
    assert 'name="viewport"' in texto          # responsive
    assert "<style" in texto                   # estilos incrustados, sin descargas


def test_el_estado_publico_no_expone_datos_personales_ni_cifras():
    d = client.get("/publico/comunidad/3/estado").json()
    crudo = str(d)
    assert "telefono" not in crudo and "usuario" not in crudo
    assert "cloro" not in crudo and "turbidez" not in crudo
    # Sí entrega lo que la población necesita.
    assert d["etiqueta"] and d["instruccion"] and d["acciones"]


def test_el_mensaje_corresponde_al_nivel_de_riesgo():
    for cid in (1, 2, 3):
        d = client.get(f"/publico/comunidad/{cid}/estado").json()
        if d["nivel"] == "ROJO":
            assert "HIERVA" in d["instruccion"].upper()
            assert d["etiqueta"] == "AGUA NO SEGURA"
        elif d["nivel"] == "VERDE":
            assert d["etiqueta"] == "AGUA SEGURA"


def test_comunidad_inexistente():
    assert client.get("/publico/comunidad/99999").status_code == 404
    assert client.get("/publico/comunidad/99999/estado").status_code == 404


def test_el_afiche_se_genera_en_pdf():
    r = client.get("/avisos/comunidad/1", headers=_auth_atm())
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")      # PDF válido
    assert len(r.content) > 3000              # incluye el mapa de bits del QR
    assert "attachment" in r.headers["content-disposition"]


def test_el_afiche_exige_sesion_institucional():
    assert client.get("/avisos/comunidad/1").status_code == 401
