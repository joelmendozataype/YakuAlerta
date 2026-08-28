"""Pruebas del cierre de alertas — CA-HU16-02.

Cerrar una alerta roja significa decirle a la comunidad que puede volver a
beber el agua. Por eso no basta con afirmar que el problema se resolvió: tiene
que existir un hecho registrado que lo acredite —una remedición en verde del
mismo reservorio, o un dictamen CONFORME de laboratorio— y el servidor lo
verifica por su cuenta.
"""
import random
import uuid
from datetime import date, datetime, timedelta, timezone

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


def _desa() -> dict:
    return _auth("70100030", "DESA")


def _operador() -> dict:
    return _auth("70100001", "JASS")


def _reservorios(headers: dict) -> list[dict]:
    r = client.get("/admin/reservorios", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _medir(reservorio_id: int, cloro: float, turbidez: float, dias: int = 0,
           observaciones: str | None = None) -> dict:
    """Registra una medición como operador y devuelve lo que respondió la API."""
    r = client.post("/mediciones", headers=_operador(), json={
        "uuid_registro": str(uuid.uuid4()),
        "reservorio_id": reservorio_id,
        "fecha_hora": (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat(),
        "cloro_mg_l": cloro, "turbidez_unt": turbidez,
        "metodo_cloro": "MANUAL", "observaciones": observaciones,
    })
    assert r.status_code in (200, 201), r.text
    return r.json()


def _alerta_roja() -> tuple[int, int]:
    """Deja una alerta roja abierta y devuelve (alerta_id, reservorio_id).

    Usa un reservorio recién creado en cada prueba: las alertas se agrupan por
    reservorio (antifatiga), así que compartir uno haría que una prueba
    heredara la alerta de otra.
    """
    reservorio_id = _reservorio_nuevo()
    medicion = _medir(reservorio_id, cloro=0.05, turbidez=2.0)

    activas = client.get("/alertas?estado=ACTIVA", headers=_atm()).json()
    alerta = next((a for a in activas if a["medicion_id"] == medicion["medicion_id"]), None)
    assert alerta, f"la medición {medicion['medicion_id']} no generó alerta"
    assert alerta["nivel"] == "ROJO"
    return alerta["alerta_id"], reservorio_id


def _reservorio_nuevo() -> int:
    """Un reservorio propio, asignado al operador que firma las mediciones."""
    h = _atm()
    comunidad = client.get("/admin/comunidades", headers=h).json()[0]
    r = client.post("/admin/reservorios", headers=h, json={
        "comunidad_id": comunidad["comunidad_id"],
        "codigo": f"RT-{random.randint(100000, 999999)}",
        "volumen_m3": 10, "tipo_sistema": "Gravedad",
        "estado_infra": "Operativo", "umbral_silencio_dias": 7,
    })
    assert r.status_code == 201, r.text
    reservorio_id = r.json()["reservorio_id"]

    operador = next(u for u in client.get("/admin/usuarios", headers=h).json()
                    if u["rol"] == "OPERADOR")
    asignar = client.post(
        f"/admin/asignaciones?usuario_id={operador['usuario_id']}"
        f"&reservorio_id={reservorio_id}", headers=h)
    assert asignar.status_code == 201, asignar.text
    return reservorio_id


def _cerrar(alerta_id: int, headers: dict, **payload):
    cuerpo = {"resultado_cierre": "Se recloró el reservorio y se verificó."}
    cuerpo.update(payload)
    return client.post(f"/alertas/{alerta_id}/cerrar", headers=headers, json=cuerpo)


# ─── El camino que antes se podía falsificar ─────────────────────
def test_no_se_cierra_una_roja_declarando_un_dictamen_inexistente():
    """El campo `dictamen_desa` era un booleano del cliente: abría el candado."""
    alerta_id, _ = _alerta_roja()
    r = _cerrar(alerta_id, _atm(), dictamen_desa=True)
    assert r.status_code == 422, r.text
    assert "sin evidencia" in r.json()["detail"]

    # Y la alerta sigue activa: nadie le dijo a la comunidad que puede beber.
    assert client.get(f"/alertas/{alerta_id}", headers=_atm()).json()["estado"] == "ACTIVA"


def test_no_se_cierra_una_roja_sin_nada():
    alerta_id, _ = _alerta_roja()
    r = _cerrar(alerta_id, _atm())
    assert r.status_code == 422
    assert "CA-HU16-02" in r.json()["detail"]


# ─── Camino 1: remedición ────────────────────────────────────────
def test_la_remedicion_en_verde_cierra_el_caso():
    alerta_id, reservorio_id = _alerta_roja()
    rem = _medir(reservorio_id, cloro=0.80, turbidez=1.0)

    r = _cerrar(alerta_id, _atm(), medicion_cierre_id=rem["medicion_id"])
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "CERRADA"


def test_la_remedicion_debe_ser_del_mismo_reservorio():
    """Una medición verde de otra comunidad no dice nada sobre esta agua."""
    alerta_id, reservorio_id = _alerta_roja()
    ajena = _medir(_reservorio_nuevo(), cloro=0.90, turbidez=1.0)

    r = _cerrar(alerta_id, _atm(), medicion_cierre_id=ajena["medicion_id"])
    assert r.status_code == 422, r.text
    assert "otro reservorio" in r.json()["detail"]


def test_la_remedicion_no_puede_seguir_en_riesgo():
    alerta_id, reservorio_id = _alerta_roja()
    floja = _medir(reservorio_id, cloro=0.40, turbidez=1.0)   # amarillo
    r = _cerrar(alerta_id, _atm(), medicion_cierre_id=floja["medicion_id"])
    assert r.status_code == 422
    assert "AMARILLO" in r.json()["detail"]


def test_la_remedicion_no_puede_ser_anterior_a_la_alerta():
    """Una medición vieja no acredita que el problema se resolvió."""
    alerta_id, reservorio_id = _alerta_roja()
    vieja = _medir(reservorio_id, cloro=0.85, turbidez=1.0, dias=30)
    r = _cerrar(alerta_id, _atm(), medicion_cierre_id=vieja["medicion_id"])
    assert r.status_code == 422, r.text
    assert "anterior a la alerta" in r.json()["detail"]


def test_remedicion_inexistente():
    alerta_id, _ = _alerta_roja()
    assert _cerrar(alerta_id, _atm(), medicion_cierre_id=999_999).status_code == 404


# ─── Camino 2: dictamen de laboratorio ───────────────────────────
def test_un_dictamen_conforme_registrado_cierra_el_caso():
    """El servidor lo busca en resultado_laboratorio; nadie lo declara."""
    alerta_id, reservorio_id = _alerta_roja()

    lab = client.post("/laboratorio", headers=_desa(), json={
        "reservorio_id": reservorio_id, "parametro": "Coliformes totales",
        "valor": 0, "unidad": "UFC/100mL", "dictamen": "CONFORME",
        "fecha_muestreo": date.today().isoformat(),
        "laboratorio": "DIRESA Huancavelica",
    })
    assert lab.status_code in (200, 201), lab.text

    r = _cerrar(alerta_id, _atm())
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "CERRADA"


def test_un_dictamen_no_conforme_no_cierra_nada():
    alerta_id, reservorio_id = _alerta_roja()
    client.post("/laboratorio", headers=_desa(), json={
        "reservorio_id": reservorio_id, "parametro": "E. coli",
        "valor": 12, "unidad": "UFC/100mL", "dictamen": "NO_CONFORME",
        "fecha_muestreo": date.today().isoformat(),
        "laboratorio": "DIRESA Huancavelica",
    })
    r = _cerrar(alerta_id, _atm())
    assert r.status_code == 422, r.text


# ─── Reglas generales ────────────────────────────────────────────
def test_una_alerta_no_se_cierra_dos_veces():
    alerta_id, reservorio_id = _alerta_roja()
    rem = _medir(reservorio_id, cloro=0.80, turbidez=1.0)
    assert _cerrar(alerta_id, _atm(), medicion_cierre_id=rem["medicion_id"]).status_code == 200
    assert _cerrar(alerta_id, _atm(), medicion_cierre_id=rem["medicion_id"]).status_code == 409


def test_la_jass_no_cierra_alertas():
    """Quien mide no es quien declara resuelto el caso."""
    alerta_id, _ = _alerta_roja()
    assert _cerrar(alerta_id, _operador()).status_code == 403


def test_el_cierre_exige_decir_que_se_hizo():
    alerta_id, reservorio_id = _alerta_roja()
    rem = _medir(reservorio_id, cloro=0.80, turbidez=1.0)
    r = client.post(f"/alertas/{alerta_id}/cerrar", headers=_atm(), json={
        "resultado_cierre": "ok", "medicion_cierre_id": rem["medicion_id"],
    })
    assert r.status_code == 422, r.text


def test_alerta_inexistente():
    assert _cerrar(999_999, _atm()).status_code == 404


def test_un_dictamen_del_mismo_segundo_que_la_alerta_tambien_cierra():
    """Caso límite que falló 18 de 40 veces antes de corregirse.

    SQLite guarda CURRENT_TIMESTAMP sin microsegundos, pero el parámetro se
    enlaza con ellos; comparados como texto, «…58» quedaba por debajo de
    «…58.000000». Un dictamen emitido en el mismo segundo que la alerta se
    volvía invisible y el caso no se podía cerrar. Se repite el ciclo varias
    veces porque el fallo dependía de en qué momento del segundo caía cada uno.
    """
    for _ in range(12):
        alerta_id, reservorio_id = _alerta_roja()
        lab = client.post("/laboratorio", headers=_desa(), json={
            "reservorio_id": reservorio_id, "parametro": "Coliformes totales",
            "valor": 0, "unidad": "UFC/100mL", "dictamen": "CONFORME",
            "fecha_muestreo": date.today().isoformat(),
            "laboratorio": "DIRESA Huancavelica",
        })
        assert lab.status_code in (200, 201), lab.text
        r = _cerrar(alerta_id, _atm())
        assert r.status_code == 200, r.text
