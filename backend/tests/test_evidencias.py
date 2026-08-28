"""Pruebas de la evidencia fotográfica — HU-08 / RF-14.

La foto respalda lo que una persona vio en el reservorio. Por eso la adjunta
quien firmó la medición, y la ven quienes deciden con ella. Son imágenes
georreferenciadas de comunidades: no se exponen más allá (Ley N.° 29733).
"""
import io
import uuid as uuidlib
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CLAVE = "yaku2026"


def _auth(dni: str, grupo: str) -> dict:
    r = client.post("/auth/login", json={"dni": dni, "clave": CLAVE, "grupo_rol": grupo})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _operador() -> dict:
    return _auth("70100001", "JASS")


def _otro_operador() -> dict:
    return _auth("70100002", "JASS")


def _atm() -> dict:
    return _auth("70100020", "ATM")


def _jpeg() -> bytes:
    """Un JPEG mínimo válido, suficiente para que el tipo se acepte."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (30, 120, 200)).save(buf, format="JPEG")
    return buf.getvalue()


def _medir(headers: dict) -> dict:
    """Registra una medición del primer reservorio asignado a quien firma."""
    reservorios = client.get("/admin/reservorios", headers=_atm()).json()
    r = client.post("/mediciones", headers=headers, json={
        "uuid_registro": str(uuidlib.uuid4()),
        "reservorio_id": reservorios[0]["reservorio_id"],
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "cloro_mg_l": 0.72, "turbidez_unt": 2.0, "metodo_cloro": "MANUAL",
    })
    assert r.status_code in (200, 201), r.text
    return r.json()


def _adjuntar(headers: dict, uuid: str, contenido: bytes | None = None,
              tipo: str = "image/jpeg"):
    return client.post(
        f"/mediciones/{uuid}/evidencia", headers=headers,
        files={"archivo": ("foto.jpg", contenido or _jpeg(), tipo)},
        data={"latitud": "-12.9833", "longitud": "-74.7167"},
    )


# ─── Dónde se guarda ─────────────────────────────────────────────
def test_la_carpeta_no_depende_del_directorio_de_arranque():
    """Con una ruta relativa, arrancar desde otra carpeta perdía las fotos.

    Peor aún: las escribía fuera de backend/uploads/, que es lo único que el
    .gitignore excluye, camino de acabar versionadas en el repositorio.
    """
    from app.routers.evidencias import UPLOAD_DIR

    assert UPLOAD_DIR.is_absolute()
    assert UPLOAD_DIR.name == "uploads"
    assert UPLOAD_DIR.parent.name == "backend"
    assert UPLOAD_DIR.exists()


def test_la_foto_queda_en_disco_y_se_puede_recuperar():
    h = _operador()
    medicion = _medir(h)
    r = _adjuntar(h, medicion["uuid_registro"])
    assert r.status_code == 201, r.text

    evidencias = client.get(f"/mediciones/{medicion['medicion_id']}/evidencias",
                            headers=h).json()
    assert len(evidencias) == 1
    assert evidencias[0]["latitud"] == -12.9833

    descarga = client.get(evidencias[0]["url"], headers=h)
    assert descarga.status_code == 200
    assert descarga.headers["content-type"].startswith("image/")


# ─── Quién puede adjuntar ────────────────────────────────────────
def test_solo_quien_midio_adjunta_su_evidencia():
    """Si otro pudiera adjuntarla, la foto dejaría de probar nada."""
    medicion = _medir(_operador())
    r = _adjuntar(_otro_operador(), medicion["uuid_registro"])
    assert r.status_code == 403, r.text
    assert "quien tomó la medición" in r.json()["detail"]


def test_ni_siquiera_la_atm_adjunta_por_el_operador():
    medicion = _medir(_operador())
    assert _adjuntar(_atm(), medicion["uuid_registro"]).status_code == 403


def test_una_medicion_inexistente_no_admite_foto():
    r = _adjuntar(_operador(), str(uuidlib.uuid4()))
    assert r.status_code == 404
    assert "sincroniza la medición" in r.json()["detail"]


def test_solo_se_aceptan_imagenes():
    h = _operador()
    medicion = _medir(h)
    r = _adjuntar(h, medicion["uuid_registro"], b"no soy una imagen",
                  tipo="application/pdf")
    assert r.status_code == 415


def test_una_imagen_enorme_se_rechaza():
    from app.routers.evidencias import MAX_BYTES

    h = _operador()
    medicion = _medir(h)
    r = _adjuntar(h, medicion["uuid_registro"], b"\xff\xd8" + b"0" * (MAX_BYTES + 10))
    assert r.status_code == 413


# ─── Quién puede verla ───────────────────────────────────────────
def test_quien_decide_con_la_evidencia_puede_verla():
    h = _operador()
    medicion = _medir(h)
    _adjuntar(h, medicion["uuid_registro"])

    for dni, grupo in (("70100020", "ATM"), ("70100040", "IPRESS_SALUD"),
                       ("70100030", "DESA"), ("70100099", "ADMIN")):
        r = client.get(f"/mediciones/{medicion['medicion_id']}/evidencias",
                       headers=_auth(dni, grupo))
        assert r.status_code == 200, f"{grupo}: {r.text}"
        assert len(r.json()) == 1


def test_un_operador_no_ve_la_evidencia_de_otro():
    """Son fotos georreferenciadas de comunidades ajenas a su trabajo."""
    h = _operador()
    medicion = _medir(h)
    _adjuntar(h, medicion["uuid_registro"])

    r = client.get(f"/mediciones/{medicion['medicion_id']}/evidencias",
                   headers=_otro_operador())
    assert r.status_code == 403, r.text


def test_la_evidencia_exige_sesion():
    assert client.get("/evidencias/1").status_code in (401, 403)
