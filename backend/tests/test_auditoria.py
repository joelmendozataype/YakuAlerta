"""Pruebas del rastro de auditoría.

El sistema registraba cada hecho sensible y nadie podía leerlo. Estas pruebas
fijan que el rastro sea consultable, que diga quién hizo qué, y que cada quien
solo vea lo de su ámbito.
"""
import random

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CLAVE = "yaku2026"


def _auth(dni: str, grupo: str) -> dict:
    r = client.post("/auth/login", json={"dni": dni, "clave": CLAVE, "grupo_rol": grupo})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _atm() -> dict:
    return _auth("70100020", "ATM")


def _admin() -> dict:
    return _auth("70100099", "ADMIN")


def _rastro(headers: dict, **filtros) -> list[dict]:
    r = client.get("/auditoria", headers=headers, params=filtros)
    assert r.status_code == 200, r.text
    return r.json()


def test_el_rastro_se_puede_leer():
    filas = _rastro(_admin())
    assert filas, "el rastro no debería estar vacío: los ingresos ya se registran"
    assert filas[0]["fecha_hora"] >= filas[-1]["fecha_hora"]  # lo reciente primero


def test_cada_hecho_dice_quien_lo_hizo_y_en_palabras():
    """Un rastro de códigos en mayúsculas no sirve para rendir cuentas."""
    fila = next(f for f in _rastro(_admin(), accion="LOGIN") if f["usuario_id"])
    assert fila["titulo"] == "Inició sesión"
    assert fila["usuario"] and fila["rol"]


def test_dar_de_baja_una_cuenta_deja_rastro():
    h = _atm()
    n = random.randint(10_000_000, 79_999_999)
    comunidad = client.get("/admin/comunidades", headers=h).json()[0]
    alta = client.post("/admin/usuarios", headers=h, json={
        "nombres": "Cuenta auditada", "dni": str(n),
        "telefono": f"9{n % 100_000_000:08d}", "clave": "clave12345",
        "rol": "OPERADOR", "comunidad_id": comunidad["comunidad_id"],
    })
    assert alta.status_code == 201, alta.text
    uid = alta.json()["usuario_id"]

    client.patch(f"/admin/usuarios/{uid}", headers=h, json={"activo": False})

    baja = _rastro(h, entidad="usuario", registro_id=str(uid))
    assert any(f["accion"] == "BAJA_USUARIO" for f in baja)
    assert baja[0]["titulo"] == "Dio de baja una cuenta"


def test_mover_un_umbral_deja_su_valor_anterior():
    """Sin ese dato no se puede explicar por qué una comunidad cambió de color."""
    h = _admin()
    p = next(x for x in client.get("/parametros", headers=h).json()
             if x["parametro"] == "cloro_residual")
    original = p["umbral_rojo"]
    try:
        client.patch(f"/parametros/{p['parametro_id']}", headers=h, json={"umbral_rojo": 0.22})
        fila = _rastro(h, accion="CAMBIA_UMBRAL")[0]
        assert fila["titulo"] == "Modificó un umbral normativo"
        assert "cloro_residual" in fila["detalle"]
        assert f"rojo={original}" in fila["detalle"]
    finally:
        client.patch(f"/parametros/{p['parametro_id']}", headers=h,
                     json={"umbral_rojo": original})


def test_el_filtro_de_sensibles_esconde_los_ingresos():
    filas = _rastro(_admin(), solo_sensibles=True, limite=200)
    assert filas
    assert not any(f["accion"].startswith("LOGIN") for f in filas)


def test_el_rastro_de_una_sola_cuenta():
    h = _admin()
    yo = client.get("/auth/me", headers=h).json()
    filas = _rastro(h, usuario_id=yo["usuario_id"])
    assert filas
    assert {f["usuario_id"] for f in filas} == {yo["usuario_id"]}


def test_la_atm_no_ve_el_rastro_de_cuentas_regionales():
    """El rastro no puede ser una ventana a otra jurisdicción."""
    regionales = {u["usuario_id"] for u in client.get("/admin/usuarios", headers=_admin()).json()
                  if u["rol"] in ("DESA", "DRVCS", "ADMIN")}
    vistos = {f["usuario_id"] for f in _rastro(_atm(), limite=500)}
    assert not (vistos & regionales)


def test_el_catalogo_de_acciones_alimenta_los_filtros():
    r = client.get("/auditoria/acciones", headers=_admin())
    assert r.status_code == 200
    assert r.json()["CIERRE_ALERTA"] == "Cerró una alerta"


def test_la_jass_no_lee_el_rastro():
    assert client.get("/auditoria", headers=_auth("70100001", "JASS")).status_code == 403


def test_el_rastro_exige_sesion():
    assert client.get("/auditoria").status_code in (401, 403)
