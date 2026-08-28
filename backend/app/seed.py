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
from .services.codigo_reservorio import siguiente_codigo
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
        # 5 UNT es el límite del D.S.; 10 es el criterio del proyecto, a
        # partir del cual las partículas protegen a los patógenos del cloro.
        db.add(ParametroNormativo(parametro="turbidez", unidad="UNT",
                                  umbral_amarillo=5, umbral_rojo=10))


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

        # ── Territorio: provincia de Angaraes, Huancavelica ─────
        # Se siembran los doce distritos de la provincia, no solo el del
        # piloto: así el sistema nace con el territorio completo y sumar el
        # segundo distrito no exige tocar la base. Lircay es el que arranca
        # con datos; los once restantes esperan a su ATM.
        #
        # Los códigos son los del INEI para la provincia 0902.
        DISTRITOS_ANGARAES = [
            ("090201", "LIRCAY"),
            ("090202", "ANCHONGA"),
            ("090203", "CALLANMARCA"),
            ("090204", "CCOCHACCASA"),
            ("090205", "CHINCHO"),
            ("090206", "CONGALLA"),
            ("090207", "HUANCA-HUANCA"),
            ("090208", "HUAYLLAY GRANDE"),
            ("090209", "JULCAMARCA"),
            ("090210", "SAN ANTONIO DE ANTAPARCO"),
            ("090211", "SANTO TOMAS DE PATA"),
            ("090212", "SECCLLA"),
        ]
        distritos = {}
        for codigo, nombre in DISTRITOS_ANGARAES:
            u = Ubigeo(codigo_ubigeo=codigo, departamento="HUANCAVELICA",
                       provincia="ANGARAES", distrito=nombre)
            db.add(u)
            db.flush()
            distritos[nombre] = u
        ubigeo = distritos["LIRCAY"]

        # ── Comunidades del piloto (distrito de Lircay) ─────────
        # Cada comunidad tiene su propia JASS: una junta administra un solo
        # sistema de agua. La ATM de Lircay las acompaña a las tres.
        comunidades_def = [
            ("COM-01", "JASS COM-01", -12.9833, -74.7167, 420),
            ("COM-02", "JASS COM-02", -12.9705, -74.7042, 610),
            ("COM-03", "JASS COM-03", -13.0012, -74.7290, 260),
        ]
        comunidades = {}
        for nombre, jass, lat, lon, pob in comunidades_def:
            c = Comunidad(ubigeo_id=ubigeo.ubigeo_id, nombre=nombre, jass_nombre=jass,
                          latitud=lat, longitud=lon, poblacion_servida=pob)
            db.add(c)
            db.flush()
            comunidades[nombre] = c

        # ── Reservorios (uno por comunidad) ─────────────────────
        # El código dice dónde está: reservorio, distrito y comunidad.
        reservorios = {}
        volumenes = [12, 8, 15]
        for i, (nombre, c) in enumerate(comunidades.items(), start=1):
            r = Reservorio(comunidad_id=c.comunidad_id,
                           codigo=siguiente_codigo(db, c),
                           volumen_m3=volumenes[i - 1],
                           tipo_sistema="Gravedad", estado_infra="Operativo",
                           umbral_silencio_dias=7)
            db.add(r)
            db.flush()
            reservorios[nombre] = r

        # ── Usuarios: una cuenta por actor ──────────────────────
        # Nueve cuentas para siete actores. La JASS lleva tres porque son tres
        # juntas —una por comunidad—; el resto, una cada uno. Los demás roles
        # que el sistema admite (directivo JASS, autoridad local) se dan de
        # alta desde el panel cuando el piloto los necesite.
        #  (nombres, DNI, teléfono, rol, entidad, comunidad, ámbito distrital)
        ub = ubigeo.ubigeo_id
        cid = lambda n: comunidades[n].comunidad_id  # noqa: E731
        usuarios_def = [
            # JASS: una junta por comunidad, representada por quien mide.
            ("Máximo Quispe", "70100001", "987000001", RolUsuario.OPERADOR, "JASS COM-01", cid("COM-01"), ub),
            ("Rosa Huamán", "70100002", "987000002", RolUsuario.OPERADOR, "JASS COM-02", cid("COM-02"), ub),
            ("Julián Ccanto", "70100003", "987000003", RolUsuario.OPERADOR, "JASS COM-03", cid("COM-03"), ub),
            # Un actor institucional por entidad.
            ("Ing. Pazos (ATM)", "70100020", "987000020", RolUsuario.ATM, "Municipalidad de Lircay", None, ub),
            ("Tec. Salud Pampas", "70100040", "987000040", RolUsuario.SALUD, "C.S. Lircay", None, ub),
            ("Promotor comunal", "70100060", "987000060", RolUsuario.POBLACION, "Difusión a la población", cid("COM-01"), ub),
            ("Esp. Ccora (DESA)", "70100030", "987000030", RolUsuario.DESA, "DIRESA Huancavelica", None, None),
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
        for tel, com in (("987000001", "COM-01"),
                         ("987000002", "COM-02"),
                         ("987000003", "COM-03")):
            db.add(AsignacionOperador(usuario_id=usuarios[tel].usuario_id,
                                      reservorio_id=reservorios[com].reservorio_id))
        db.flush()

        # ── Mediciones demo (verde/amarillo/rojo) ───────────────
        # Cada medición la firma el operador de esa JASS, no uno prestado.
        operador_de = {"COM-01": "987000001",
                       "COM-02": "987000002",
                       "COM-03": "987000003"}
        ahora = datetime.now(timezone.utc)
        muestras = [
            ("COM-01", 0.72, 2.0, None, 0),                        # verde
            ("COM-02", 0.41, 3.0, None, 1),                        # amarillo
            ("COM-03", 0.10, 8.0, "agua turbia tras lluvia", 0),   # rojo
            ("COM-01", 0.60, 2.2, None, 3),                        # histórico verde
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
