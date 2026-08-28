"""Pruebas del ciclo de vida de una cuenta y de los umbrales normativos.

Crear una cuenta era lo único que se podía hacer; ahora también se corrige, se
da de baja y se le restablece la clave. Cada verbo trae sus propios candados.
"""
import random

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CLAVE = "yaku2026"
ATM, ADMIN = "70100020", "70100099"


def _auth(dni: str, grupo: str) -> dict:
    r = client.post("/auth/login", json={"dni": dni, "clave": CLAVE, "grupo_rol": grupo})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _atm() -> dict:
    return _auth(ATM, "ATM")


def _admin() -> dict:
    return _auth(ADMIN, "ADMIN")


def _identidad() -> tuple[str, str]:
    n = random.randint(10_000_000, 79_999_999)
    return str(n), f"9{n % 100_000_000:08d}"


def _crear_operador(headers: dict) -> dict:
    dni, telefono = _identidad()
    r = client.post("/admin/usuarios", headers=headers, json={
        "nombres": "Operador de prueba", "dni": dni, "telefono": telefono,
        "clave": "clave12345", "rol": "OPERADOR",
    })
    assert r.status_code == 201, r.text
    return r.json()


# ─── Corrección y baja de cuentas ────────────────────────────────
def test_la_atm_corrige_los_datos_de_una_cuenta():
    h = _atm()
    u = _crear_operador(h)
    r = client.patch(f"/admin/usuarios/{u['usuario_id']}", headers=h,
                     json={"nombres": "Nombre corregido", "entidad": "JASS Comunidad 02"})
    assert r.status_code == 200, r.text
    assert r.json()["nombres"] == "Nombre corregido"
    assert r.json()["entidad"] == "JASS Comunidad 02"


def test_dar_de_baja_impide_entrar_pero_conserva_la_cuenta():
    """La baja no borra: el historial de mediciones debe seguir en pie."""
    h = _atm()
    u = _crear_operador(h)
    dni = u["dni"]
    assert client.post("/auth/login", json={"dni": dni, "clave": "clave12345"}).status_code == 200

    r = client.patch(f"/admin/usuarios/{u['usuario_id']}", headers=h, json={"activo": False})
    assert r.status_code == 200 and r.json()["activo"] is False

    assert client.post("/auth/login", json={"dni": dni, "clave": "clave12345"}).status_code != 200
    # Y sigue existiendo para quien administra.
    assert any(x["usuario_id"] == u["usuario_id"]
               for x in client.get("/admin/usuarios", headers=h).json())


def test_la_reactivacion_devuelve_el_acceso():
    h = _atm()
    u = _crear_operador(h)
    client.patch(f"/admin/usuarios/{u['usuario_id']}", headers=h, json={"activo": False})
    client.patch(f"/admin/usuarios/{u['usuario_id']}", headers=h, json={"activo": True})
    assert client.post("/auth/login",
                       json={"dni": u["dni"], "clave": "clave12345"}).status_code == 200


def test_nadie_se_desactiva_a_si_mismo():
    """Evita dejar al sistema sin quien lo administre."""
    h = _atm()
    yo = client.get("/auth/me", headers=h).json()
    r = client.patch(f"/admin/usuarios/{yo['usuario_id']}", headers=h, json={"activo": False})
    assert r.status_code == 409


def test_la_atm_no_da_de_baja_cuentas_regionales():
    """La DESA es de rango superior: no está bajo su mando."""
    h = _atm()
    desa = next(u for u in client.get("/admin/usuarios", headers=_admin()).json()
                if u["rol"] == "DESA")
    r = client.patch(f"/admin/usuarios/{desa['usuario_id']}", headers=h, json={"activo": False})
    assert r.status_code == 403


def test_una_correccion_vacia_se_rechaza():
    h = _atm()
    u = _crear_operador(h)
    assert client.patch(f"/admin/usuarios/{u['usuario_id']}", headers=h, json={}).status_code == 400


def test_usuario_inexistente():
    assert client.patch("/admin/usuarios/999999", headers=_atm(),
                        json={"activo": False}).status_code == 404


# ─── Clave provisional ───────────────────────────────────────────
def test_la_clave_provisional_reemplaza_a_la_anterior():
    """Salida para el operador sin señal que no puede recibir el SMS."""
    h = _atm()
    u = _crear_operador(h)
    r = client.post(f"/admin/usuarios/{u['usuario_id']}/clave", headers=h)
    assert r.status_code == 200, r.text
    temporal = r.json()["clave_temporal"]

    assert client.post("/auth/login", json={"dni": u["dni"], "clave": temporal}).status_code == 200
    assert client.post("/auth/login",
                       json={"dni": u["dni"], "clave": "clave12345"}).status_code != 200


def test_la_atm_no_restablece_la_clave_de_una_cuenta_regional():
    h = _atm()
    drvcs = next(u for u in client.get("/admin/usuarios", headers=_admin()).json()
                 if u["rol"] == "DRVCS")
    assert client.post(f"/admin/usuarios/{drvcs['usuario_id']}/clave",
                       headers=h).status_code == 403


# ─── Umbrales normativos (RNF-07) ────────────────────────────────
def test_las_instituciones_consultan_los_umbrales():
    for dni, grupo in ((ATM, "ATM"), ("70100030", "DESA"), ("70100070", "DRVCS")):
        r = client.get("/parametros", headers=_auth(dni, grupo))
        assert r.status_code == 200, r.text
        assert {p["parametro"] for p in r.json()} >= {"cloro_residual", "turbidez"}


def test_solo_el_admin_mueve_un_umbral():
    """No es una decisión distrital: cambia para toda la región."""
    p = client.get("/parametros", headers=_admin()).json()[0]
    r = client.patch(f"/parametros/{p['parametro_id']}", headers=_atm(),
                     json={"umbral_rojo": 0.25})
    assert r.status_code == 403


def test_el_admin_ajusta_un_umbral_y_reclasifica_lo_que_viene():
    h = _admin()
    cloro = next(p for p in client.get("/parametros", headers=h).json()
                 if p["parametro"] == "cloro_residual")
    original = cloro["umbral_rojo"]
    try:
        r = client.patch(f"/parametros/{cloro['parametro_id']}", headers=h,
                         json={"umbral_rojo": 0.20})
        assert r.status_code == 200, r.text
        assert r.json()["umbral_rojo"] == 0.20

        from app.database import SessionLocal
        from app.services.procesamiento import cargar_umbrales
        db = SessionLocal()
        try:
            assert cargar_umbrales(db).cloro_rojo == 0.20
        finally:
            db.close()
    finally:
        client.patch(f"/parametros/{cloro['parametro_id']}", headers=h,
                     json={"umbral_rojo": original})


def test_en_el_cloro_el_rojo_va_por_debajo_del_amarillo():
    """Menos cloro es más riesgo: invertirlos dejaría de clasificar bien."""
    h = _admin()
    cloro = next(p for p in client.get("/parametros", headers=h).json()
                 if p["parametro"] == "cloro_residual")
    r = client.patch(f"/parametros/{cloro['parametro_id']}", headers=h,
                     json={"umbral_rojo": 9.0})
    assert r.status_code == 422
    assert "menor" in r.json()["detail"]


def test_en_la_turbidez_el_rojo_va_por_encima():
    h = _admin()
    turb = next(p for p in client.get("/parametros", headers=h).json()
                if p["parametro"] == "turbidez")
    r = client.patch(f"/parametros/{turb['parametro_id']}", headers=h,
                     json={"umbral_rojo": 0.1, "umbral_amarillo": 5.0})
    assert r.status_code == 422
    assert "mayor" in r.json()["detail"]


def test_un_umbral_negativo_se_rechaza():
    h = _admin()
    p = client.get("/parametros", headers=h).json()[0]
    assert client.patch(f"/parametros/{p['parametro_id']}", headers=h,
                        json={"umbral_rojo": -1}).status_code == 422


def test_la_jass_no_ve_los_umbrales():
    assert client.get("/parametros", headers=_auth("70100001", "JASS")).status_code == 403


def test_el_padron_se_lee_por_comunidad_y_distrito():
    """La columna de ámbito debe decir dónde trabaja cada quien, no un id."""
    usuarios = {u["nombres"]: u for u in client.get("/admin/usuarios", headers=_admin()).json()}
    operador = usuarios["Máximo Quispe (operador)"]
    assert operador["comunidad"] == "Comunidad 01"
    assert operador["distrito"] == "LIRCAY"
    # Una cuenta regional no tiene distrito, y eso también debe verse.
    assert usuarios["Esp. Ccora (DESA)"]["distrito"] is None


# ─── Catálogo de actores ─────────────────────────────────────────
def test_el_panel_muestra_los_siete_actores():
    r = client.get("/admin/actores", headers=_admin())
    assert r.status_code == 200, r.text
    actores = r.json()
    assert len(actores) == 7
    assert [a["actor"] for a in actores] == [
        "JASS", "ATM", "IPRESS / Salud", "Usuario / vecino",
        "DESA", "DRVCS", "Administrador",
    ]
    assert [a["orden"] for a in actores] == list(range(1, 8))


def test_cada_actor_declara_su_superficie():
    """Debe coincidir con lo que ofrecen las dos pantallas de ingreso."""
    a = {x["actor"]: x for x in client.get("/admin/actores", headers=_admin()).json()}

    # Solo la app: trabajan en campo.
    assert (a["JASS"]["movil"], a["JASS"]["tablero"]) == (True, False)
    assert (a["Usuario / vecino"]["movil"], a["Usuario / vecino"]["tablero"]) == (True, False)
    # Ambas: verifican en campo y deciden en oficina.
    for nombre in ("ATM", "IPRESS / Salud"):
        assert a[nombre]["movil"] and a[nombre]["tablero"], nombre
    # Solo el tablero: nunca salen de la oficina.
    for nombre in ("DESA", "DRVCS", "Administrador"):
        assert not a[nombre]["movil"] and a[nombre]["tablero"], nombre

    assert sum(x["movil"] for x in a.values()) == 4
    assert sum(x["tablero"] for x in a.values()) == 5


def test_el_catalogo_cuenta_las_cuentas_de_cada_actor():
    a = {x["actor"]: x for x in client.get("/admin/actores", headers=_admin()).json()}
    # La JASS agrupa operadores y directivos de las tres comunidades.
    assert a["JASS"]["cuentas"] >= 6
    assert set(a["JASS"]["roles"]) == {"OPERADOR", "DIRECTIVO_JASS"}
    assert a["Administrador"]["cuentas"] >= 1


def test_una_baja_se_refleja_en_el_catalogo():
    """Las activas y el total deben separarse cuando alguien deja el sistema."""
    h = _atm()
    u = _crear_operador(h)
    antes = next(x for x in client.get("/admin/actores", headers=h).json()
                 if x["actor"] == "JASS")
    client.patch(f"/admin/usuarios/{u['usuario_id']}", headers=h, json={"activo": False})
    despues = next(x for x in client.get("/admin/actores", headers=h).json()
                   if x["actor"] == "JASS")
    assert despues["cuentas"] == antes["cuentas"]
    assert despues["activas"] == antes["activas"] - 1


def test_la_atm_ve_el_catalogo_acotado_a_su_distrito():
    """Las cuentas regionales no son suyas, aunque el actor exista igual."""
    a = {x["actor"]: x for x in client.get("/admin/actores", headers=_atm()).json()}
    assert len(a) == 7                    # el catálogo es el mismo
    assert a["DESA"]["cuentas"] == 0      # pero sin cuentas fuera de su ámbito
    assert a["JASS"]["cuentas"] >= 6


def test_la_jass_no_ve_el_catalogo_de_actores():
    assert client.get("/admin/actores",
                      headers=_auth("70100001", "JASS")).status_code == 403
