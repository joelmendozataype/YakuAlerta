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
log = logging.getLogger("yakuni.seed")

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
        ubigeo = Ubigeo(codigo_ubigeo="090201", departamento="HUANCAVELICA",
                        provincia="ANGARAES", distrito="LIRCAY")
        db.add(ubigeo)
        db.flush()

        # ── Comunidades ─────────────────────────────────────────
        # Cada comunidad tiene su propia JASS: una junta administra un solo
        # sistema de agua. La ATM de Lircay las acompaña a las tres.
        comunidades_def = [
            ("Comunidad 01", "JASS Comunidad 01", -12.9833, -74.7167, 420),
            ("Comunidad 02", "JASS Comunidad 02", -12.9705, -74.7042, 610),
            ("Comunidad 03", "JASS Comunidad 03", -13.0012, -74.7290, 260),
        ]
        comunidades = {}
        for nombre, jass, lat, lon, pob in comunidades_def:
            c = Comunidad(ubigeo_id=ubigeo.ubigeo_id, nombre=nombre, jass_nombre=jass,
                          latitud=lat, longitud=lon, poblacion_servida=pob)
            db.add(c)
            db.flush()
            comunidades[nombre] = c

        # ── Reservorios (uno por comunidad) ─────────────────────
        reservorios = {}
        volumenes = [12, 8, 15]
        for i, (nombre, c) in enumerate(comunidades.items(), start=1):
            r = Reservorio(comunidad_id=c.comunidad_id,
                           codigo=f"R{i} - LIRCAY - COM - {i:02d}",
                           volumen_m3=volumenes[i - 1],
                           tipo_sistema="Gravedad", estado_infra="Operativo",
                           umbral_silencio_dias=7)
            db.add(r)
            db.flush()
            reservorios[nombre] = r

        # ── Usuarios (todos los roles) ──────────────────────────
        #  (nombres, DNI, teléfono, rol, entidad, comunidad, ámbito distrital)
        ub = ubigeo.ubigeo_id
        cid = lambda n: comunidades[n].comunidad_id  # noqa: E731
        usuarios_def = [
            ("Máximo Quispe (operador)", "70100001", "987000001", RolUsuario.OPERADOR, "JASS Comunidad 01", cid("Comunidad 01"), ub),
            ("Rosa Huamán (operador)", "70100002", "987000002", RolUsuario.OPERADOR, "JASS Comunidad 02", cid("Comunidad 02"), ub),
            ("Julián Ccanto (operador)", "70100003", "987000003", RolUsuario.OPERADOR, "JASS Comunidad 03", cid("Comunidad 03"), ub),
            ("Directivo JASS Comunidad 01", "70100010", "987000010", RolUsuario.DIRECTIVO_JASS, "JASS Comunidad 01", cid("Comunidad 01"), ub),
            ("Directivo JASS Comunidad 02", "70100011", "987000011", RolUsuario.DIRECTIVO_JASS, "JASS Comunidad 02", cid("Comunidad 02"), ub),
            ("Directivo JASS Comunidad 03", "70100012", "987000012", RolUsuario.DIRECTIVO_JASS, "JASS Comunidad 03", cid("Comunidad 03"), ub),
            ("Ing. Pazos (ATM)", "70100020", "987000020", RolUsuario.ATM, "Municipalidad de Lircay", None, ub),
            ("Esp. Ccora (DESA)", "70100030", "987000030", RolUsuario.DESA, "DIRESA Huancavelica", None, None),
            ("Tec. Salud Pampas", "70100040", "987000040", RolUsuario.SALUD, "C.S. Lircay", None, ub),
            ("Teniente gobernador Lircay", "70100050", "987000050", RolUsuario.AUTORIDAD_LOCAL, "Autoridad comunal", cid("Comunidad 01"), ub),
            ("Promotor comunal Comunidad 01", "70100060", "987000060", RolUsuario.POBLACION, "Difusión a la población", cid("Comunidad 01"), ub),
            ("Promotor comunal Comunidad 02", "70100061", "987000061", RolUsuario.POBLACION, "Difusión a la población", cid("Comunidad 02"), ub),
            ("Esp. Saneamiento (DRVCS)", "70100070", "987000070", RolUsuario.DRVCS, "Dir. Reg. Vivienda y Saneamiento", None, None),
            ("Administrador", "70100099", "987000099", RolUsuario.ADMIN, "Yakuni", None, None),
        ]
        usuarios = {}
        for nombres, dni, tel, rol, entidad, com_id, ubi_id in usuarios_def:
            u = Usuario(nombres=nombres, dni=dni, telefono=tel, clave_hash=hash_clave(CLAVE_DEMO),
                        rol=rol, entidad=entidad, comunidad_id=com_id, ubigeo_id=ubi_id)
            db.add(u)
            db.flush()
            usuarios[tel] = u

        # ── Asignaciones operador ↔ reservorio ──────────────────
        # Cada operador mide el reservorio de su propia comunidad: la JASS no
        # opera fuera de su sistema.
        for tel, com in (("987000001", "Comunidad 01"),
                         ("987000002", "Comunidad 02"),
                         ("987000003", "Comunidad 03")):
            db.add(AsignacionOperador(usuario_id=usuarios[tel].usuario_id,
                                      reservorio_id=reservorios[com].reservorio_id))
        db.flush()

        # ── Mediciones demo (verde/amarillo/rojo) ───────────────
        # Cada medición la firma el operador de esa JASS, no uno prestado.
        operador_de = {"Comunidad 01": "987000001",
                       "Comunidad 02": "987000002",
                       "Comunidad 03": "987000003"}
        ahora = datetime.now(timezone.utc)
        muestras = [
            ("Comunidad 01", 0.72, 2.0, None, 0),                        # verde
            ("Comunidad 02", 0.41, 3.0, None, 1),                        # amarillo
            ("Comunidad 03", 0.10, 8.0, "agua turbia tras lluvia", 0),   # rojo
            ("Comunidad 01", 0.60, 2.2, None, 3),                        # histórico verde
        ]
        for nombre, cl, tb, obs, dias in muestras:
            datos = MedicionIn(
                uuid_registro=str(uuid.uuid4()),
                reservorio_id=reservorios[nombre].reservorio_id,
                fecha_hora=ahora - timedelta(days=dias),
                cloro_mg_l=cl, turbidez_unt=tb,
                metodo_cloro=MetodoLectura.MANUAL, observaciones=obs,
            )
            registrar_medicion(db, datos, usuarios[operador_de[nombre]].usuario_id)

        # Nota: si se agrega una cuarta comunidad sin mediciones, aparecerá
        # como silencio de datos (demo HU-15).

        db.commit()
        log.info("✅ Datos demo cargados: distrito LIRCAY (Angaraes), %d comunidades, %d usuarios.",
                 len(comunidades), len(usuarios))
        log.info("   Login tablero → ATM: 987000020 / %s  ·  Admin: 987000099 / %s",
                 CLAVE_DEMO, CLAVE_DEMO)
        log.info("   Login app (operador) → DNI 70100001 / %s", CLAVE_DEMO)
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
