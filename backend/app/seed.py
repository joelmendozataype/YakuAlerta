"""Carga de datos demo idempotente para el MVP / Demo Day.

Ejecutar:  python -m app.seed
Crea un distrito de Huancavelica con comunidades, reservorios, usuarios de
todos los roles y mediciones de ejemplo (verde/amarillo/rojo) que ejercitan
el motor de reglas, generan alertas, recomendaciones y notificaciones.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .config import settings
from .database import SessionLocal, crear_tablas, engine
from .enums import MetodoLectura, RolUsuario
from .models import (
    AsignacionOperador, Comunidad, ParametroNormativo, Reservorio, Ubigeo, Usuario,
)
from .schemas import MedicionIn
from .security import hash_clave
from .services.registro import registrar_medicion

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("yakualerta.seed")

CLAVE_DEMO = "yaku2026"


def _esperar_db(intentos: int = 30) -> None:
    import time
    from sqlalchemy import text
    for i in range(intentos):
        try:
            with engine.connect() as c:
                c.execute(text("SELECT 1"))
            return
        except Exception:
            log.info("Esperando la base de datos... (%d/%d)", i + 1, intentos)
            time.sleep(2)
    raise RuntimeError("La base de datos no respondió a tiempo")


def _param(db) -> None:
    """Asegura los umbrales normativos (por si se ejecuta sin init.sql)."""
    existentes = {p.parametro for p in db.query(ParametroNormativo).all()}
    if "cloro_residual" not in existentes:
        db.add(ParametroNormativo(parametro="cloro_residual", unidad="mg/L",
                                  umbral_amarillo=0.5, umbral_rojo=0.3))
    if "turbidez" not in existentes:
        db.add(ParametroNormativo(parametro="turbidez", unidad="UNT",
                                  umbral_amarillo=5, umbral_rojo=5))


def sembrar() -> None:
    _esperar_db()
    # En SQLite (o cualquier motor sin init.sql) creamos el esquema aquí.
    # Es idempotente: no toca tablas que ya existen (p. ej. en PostgreSQL).
    crear_tablas()
    db = SessionLocal()
    try:
        _param(db)

        if db.query(Usuario).count() > 0:
            log.info("Datos demo ya presentes; se omite la siembra.")
            db.commit()
            return

        # ── Ubigeo (distrito de Pampas, Tayacaja) ───────────────
        ubigeo = Ubigeo(codigo_ubigeo="090701", departamento="HUANCAVELICA",
                        provincia="TAYACAJA", distrito="PAMPAS")
        db.add(ubigeo)
        db.flush()

        # ── Comunidades ─────────────────────────────────────────
        comunidades_def = [
            ("Chocce", -12.400, -74.870, 420),
            ("Ahuaycha", -12.383, -74.865, 610),
            ("Pichccahuasi", -12.430, -74.900, 260),
            ("Colpapampa", -12.415, -74.845, 350),
            ("La Merced", -12.395, -74.880, 500),
            ("Huaribamba", -12.360, -74.910, 300),
        ]
        comunidades = {}
        for nombre, lat, lon, pob in comunidades_def:
            c = Comunidad(ubigeo_id=ubigeo.ubigeo_id, nombre=nombre,
                          latitud=lat, longitud=lon, poblacion_servida=pob)
            db.add(c)
            db.flush()
            comunidades[nombre] = c

        # ── Reservorios (uno por comunidad) ─────────────────────
        reservorios = {}
        for i, (nombre, c) in enumerate(comunidades.items(), start=1):
            r = Reservorio(comunidad_id=c.comunidad_id, codigo=f"RES-{i:03d}",
                           volumen_m3=[12, 20, 8, 15, 25, 10][i - 1],
                           tipo_sistema="Gravedad", estado_infra="Operativo",
                           umbral_silencio_dias=7)
            db.add(r)
            db.flush()
            reservorios[nombre] = r

        # ── Usuarios (todos los roles) ──────────────────────────
        #  (nombres, teléfono, rol, entidad, comunidad, ámbito distrital)
        ub = ubigeo.ubigeo_id
        cid = lambda n: comunidades[n].comunidad_id  # noqa: E731
        usuarios_def = [
            ("Máximo Quispe (operador)", "987000001", RolUsuario.OPERADOR, "JASS Chocce", cid("Chocce"), ub),
            ("Rosa Huamán (operador)", "987000002", RolUsuario.OPERADOR, "JASS Ahuaycha", cid("Ahuaycha"), ub),
            ("Directivo JASS Chocce", "987000010", RolUsuario.DIRECTIVO_JASS, "JASS Chocce", cid("Chocce"), ub),
            ("Ing. Pazos (ATM)", "987000020", RolUsuario.ATM, "Municipalidad de Pampas", None, ub),
            ("Esp. Ccora (DESA)", "987000030", RolUsuario.DESA, "DIRESA Huancavelica", None, None),
            ("Tec. Salud Pampas", "987000040", RolUsuario.SALUD, "C.S. Pampas", None, ub),
            ("Teniente gobernador Chocce", "987000050", RolUsuario.AUTORIDAD_LOCAL, "Autoridad comunal", cid("Chocce"), ub),
            ("Promotor comunal Chocce", "987000060", RolUsuario.POBLACION, "Difusión a la población", cid("Chocce"), ub),
            ("Promotor comunal Ahuaycha", "987000061", RolUsuario.POBLACION, "Difusión a la población", cid("Ahuaycha"), ub),
            ("Esp. Saneamiento (DRVCS)", "987000070", RolUsuario.DRVCS, "Dir. Reg. Vivienda y Saneamiento", None, None),
            ("Administrador", "987000099", RolUsuario.ADMIN, "YakuAlerta", None, None),
        ]
        usuarios = {}
        for nombres, tel, rol, entidad, com_id, ubi_id in usuarios_def:
            u = Usuario(nombres=nombres, telefono=tel, clave_hash=hash_clave(CLAVE_DEMO),
                        rol=rol, entidad=entidad, comunidad_id=com_id, ubigeo_id=ubi_id)
            db.add(u)
            db.flush()
            usuarios[tel] = u

        # ── Asignaciones operador ↔ reservorio ──────────────────
        db.add(AsignacionOperador(usuario_id=usuarios["987000001"].usuario_id,
                                  reservorio_id=reservorios["Chocce"].reservorio_id))
        db.add(AsignacionOperador(usuario_id=usuarios["987000001"].usuario_id,
                                  reservorio_id=reservorios["Pichccahuasi"].reservorio_id))
        db.add(AsignacionOperador(usuario_id=usuarios["987000002"].usuario_id,
                                  reservorio_id=reservorios["Ahuaycha"].reservorio_id))
        db.flush()

        # ── Mediciones demo (verde/amarillo/rojo) ───────────────
        op_id = usuarios["987000001"].usuario_id
        ahora = datetime.now(timezone.utc)
        muestras = [
            ("Chocce",        0.72, 2.0, None,                    0),   # verde
            ("Ahuaycha",      0.41, 3.0, None,                    1),   # amarillo
            ("Pichccahuasi",  0.10, 8.0, "agua turbia tras lluvia", 0), # rojo
            ("Colpapampa",    0.55, 1.5, None,                    2),   # verde
            ("La Merced",     0.28, 4.0, None,                    1),   # rojo (cloro bajo)
            ("Chocce",        0.60, 2.2, None,                    3),   # histórico verde
        ]
        for nombre, cl, tb, obs, dias in muestras:
            datos = MedicionIn(
                uuid_registro=str(uuid.uuid4()),
                reservorio_id=reservorios[nombre].reservorio_id,
                fecha_hora=ahora - timedelta(days=dias),
                cloro_mg_l=cl, turbidez_unt=tb,
                metodo_cloro=MetodoLectura.MANUAL, observaciones=obs,
            )
            registrar_medicion(db, datos, op_id)

        # Comunidad Huaribamba: sin mediciones → silencio de datos (demo HU-15)

        db.commit()
        log.info("✅ Datos demo cargados: distrito PAMPAS, %d comunidades, %d usuarios.",
                 len(comunidades), len(usuarios))
        log.info("   Login tablero → ATM: 987000020 / %s  ·  Admin: 987000099 / %s",
                 CLAVE_DEMO, CLAVE_DEMO)
        log.info("   Login app (operador) → 987000001 / %s", CLAVE_DEMO)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if settings.seed_demo:
        sembrar()
    else:
        log.info("SEED_DEMO=false; no se cargan datos demo.")
