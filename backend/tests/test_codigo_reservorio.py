"""Pruebas de la estructura del código de reservorio.

    R1-LIRCAY-COM-01
    │  │      └── comunidad
    │  └───────── distrito
    └──────────── correlativo dentro del distrito

El código es el rótulo con el que la JASS identifica el tanque en campo y con
el que la ATM lo busca en el tablero. Lo arma el servidor: tecleado a mano,
cada quien lo escribiría distinto y dejaría de servir.
"""
import random

from fastapi.testclient import TestClient

from app.main import app
from app.services.codigo_reservorio import _normalizar

client = TestClient(app)
CLAVE = "yaku2026"


def _auth(dni: str, grupo: str) -> dict:
    r = client.post("/auth/login", json={"dni": dni, "clave": CLAVE, "grupo_rol": grupo})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _atm() -> dict:
    return _auth("70100020", "ATM")


def _admin() -> dict:
    return _auth("70100099", "ADMIN")


def _crear_comunidad(headers: dict, ubigeo_id: int, nombre: str) -> int:
    r = client.post("/admin/comunidades", headers=headers, json={
        "ubigeo_id": ubigeo_id, "nombre": nombre, "jass_nombre": f"JASS {nombre}",
    })
    assert r.status_code == 201, r.text
    return r.json()["comunidad_id"]


def _crear_reservorio(headers: dict, comunidad_id: int) -> str:
    r = client.post("/admin/reservorios", headers=headers, json={
        "comunidad_id": comunidad_id, "volumen_m3": 10,
        "tipo_sistema": "Gravedad", "estado_infra": "Operativo",
    })
    assert r.status_code == 201, r.text
    return r.json()["codigo"]


def test_el_piloto_conserva_los_codigos_del_padron():
    codigos = {r["codigo"] for r in client.get("/admin/reservorios", headers=_atm()).json()}
    assert {"R1-LIRCAY-COM-01", "R2-LIRCAY-COM-02", "R3-LIRCAY-COM-03"} <= codigos


def test_el_codigo_se_arma_solo_sin_que_nadie_lo_escriba():
    h = _atm()
    ubigeo = client.get("/admin/ubigeos", headers=h).json()[0]["ubigeo_id"]
    nombre = f"COM-{random.randint(50, 99)}{random.randint(100, 999)}"
    comunidad = _crear_comunidad(h, ubigeo, nombre)

    codigo = _crear_reservorio(h, comunidad)
    partes = codigo.split("-")
    assert partes[0].startswith("R")
    assert "LIRCAY" in codigo
    assert codigo.endswith(nombre)


def test_el_correlativo_avanza_dentro_del_distrito():
    """El número identifica al reservorio en la jurisdicción que lo administra."""
    h = _atm()
    ubigeo = client.get("/admin/ubigeos", headers=h).json()[0]["ubigeo_id"]
    c1 = _crear_comunidad(h, ubigeo, f"COM-A{random.randint(1000, 9999)}")
    c2 = _crear_comunidad(h, ubigeo, f"COM-B{random.randint(1000, 9999)}")

    n1 = int(_crear_reservorio(h, c1).split("-")[0][1:])
    n2 = int(_crear_reservorio(h, c2).split("-")[0][1:])
    assert n2 == n1 + 1, "el correlativo no continúa entre comunidades del mismo distrito"


def test_dos_reservorios_de_la_misma_comunidad_no_chocan():
    h = _atm()
    ubigeo = client.get("/admin/ubigeos", headers=h).json()[0]["ubigeo_id"]
    comunidad = _crear_comunidad(h, ubigeo, f"COM-C{random.randint(1000, 9999)}")
    assert _crear_reservorio(h, comunidad) != _crear_reservorio(h, comunidad)


def test_un_distrito_de_nombre_largo_produce_un_codigo_valido():
    """«SAN ANTONIO DE ANTAPARCO» daba 34 caracteres y la columna admitía 30."""
    h = _admin()
    largo = next(u for u in client.get("/admin/ubigeos", headers=h).json()
                 if u["distrito"] == "SAN ANTONIO DE ANTAPARCO")
    comunidad = _crear_comunidad(h, largo["ubigeo_id"], f"COM-{random.randint(10, 99)}")
    codigo = _crear_reservorio(h, comunidad)
    assert " " not in codigo
    assert len(codigo) <= 40
    assert "SAN-ANTONIO-DE-ANTAPARCO" in codigo


def test_la_normalizacion_quita_tildes_y_espacios():
    assert _normalizar("LIRCAY") == "LIRCAY"
    assert _normalizar("San Antonio de Antaparco") == "SAN-ANTONIO-DE-ANTAPARCO"
    assert _normalizar("HUANCA-HUANCA") == "HUANCA-HUANCA"
    assert _normalizar("Ccochaccasa") == "CCOCHACCASA"
    assert _normalizar("Comunidad Ñuñunhuayo") == "COMUNIDAD-NUNUNHUAYO"


def test_cada_junta_declara_su_distrito():
    """La pantalla anticipa el código antes de crearlo, y necesita el distrito."""
    juntas = client.get("/admin/jass", headers=_atm()).json()
    assert juntas
    assert all(j["distrito"] == "LIRCAY" for j in juntas)
