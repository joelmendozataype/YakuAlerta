"""Pruebas del cierre de sesiones vinculadas (patrón «dispositivos» de WhatsApp).

El móvil es la llave maestra: puede revocar cualquier tablero web que haya
autorizado, y el token revocado deja de valer de inmediato.
"""
import hashlib
import secrets

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CLAVE = "yaku2026"


def _sha(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def _auth_movil(telefono: str = "987000001") -> dict:
    r = client.post("/auth/login", json={"telefono": telefono, "clave": CLAVE})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _vincular_web(headers_movil: dict) -> dict:
    """Completa una vinculación por QR y devuelve la cabecera de la sesión web."""
    secreto = secrets.token_urlsafe(24)
    token = client.post("/auth/qr/nueva",
                        json={"client_hash": _sha(secreto)}).json()["token"]
    client.post(f"/auth/qr/{token}/escanear", headers=headers_movil)
    client.post(f"/auth/qr/{token}/confirmar", headers=headers_movil,
                json={"aprobar": True})
    sesion = client.post(f"/auth/qr/{token}/reclamar",
                         json={"client_secret": secreto}).json()
    return {"Authorization": f"Bearer {sesion['access_token']}"}


def test_la_sesion_vinculada_aparece_en_el_listado():
    movil = _auth_movil()
    web = _vincular_web(movil)

    sesiones = client.get("/auth/qr/sesiones/activas", headers=movil).json()
    assert len(sesiones) >= 1
    assert sesiones[0]["dispositivo"]           # nombre legible del equipo
    assert sesiones[0]["vinculado_en"]

    # Desde la propia web, esa sesión se identifica como la actual.
    propias = client.get("/auth/qr/sesiones/activas", headers=web).json()
    assert any(s["es_sesion_actual"] for s in propias)


def test_cerrar_una_sesion_invalida_su_token_al_instante():
    movil = _auth_movil()
    web = _vincular_web(movil)

    # La sesión web funciona antes del cierre.
    assert client.get("/auth/me", headers=web).status_code == 200

    sesiones = client.get("/auth/qr/sesiones/activas", headers=movil).json()
    sid = next(s["sesion_id"] for s in sesiones)
    r = client.delete(f"/auth/qr/sesiones/activas/{sid}", headers=movil)
    assert r.status_code == 200 and r.json()["cerradas"] == 1

    # Tras el cierre, el mismo token deja de valer aunque no haya expirado.
    assert client.get("/auth/me", headers=web).status_code == 401


def test_cerrar_todas_las_sesiones():
    movil = _auth_movil("987000002")
    web1 = _vincular_web(movil)
    web2 = _vincular_web(movil)

    r = client.delete("/auth/qr/sesiones/activas", headers=movil)
    assert r.json()["cerradas"] >= 2

    assert client.get("/auth/me", headers=web1).status_code == 401
    assert client.get("/auth/me", headers=web2).status_code == 401
    # El móvil conserva su acceso: su sesión no se vincula por QR.
    assert client.get("/auth/me", headers=movil).status_code == 200


def test_no_se_puede_cerrar_la_sesion_de_otro_usuario():
    movil_a = _auth_movil("987000001")
    _vincular_web(movil_a)
    sid = client.get("/auth/qr/sesiones/activas", headers=movil_a).json()[0]["sesion_id"]

    movil_b = _auth_movil("987000002")
    assert client.delete(f"/auth/qr/sesiones/activas/{sid}",
                         headers=movil_b).status_code == 404


def test_una_sesion_ya_cerrada_no_se_cierra_dos_veces():
    movil = _auth_movil()
    _vincular_web(movil)
    sid = client.get("/auth/qr/sesiones/activas", headers=movil).json()[0]["sesion_id"]

    client.delete(f"/auth/qr/sesiones/activas/{sid}", headers=movil)
    assert client.delete(f"/auth/qr/sesiones/activas/{sid}",
                         headers=movil).status_code == 409
