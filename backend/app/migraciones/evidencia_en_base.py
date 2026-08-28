"""Traslada a la base las fotos de evidencia que quedaron en disco.

La evidencia pasó de guardarse como archivo en ``uploads/`` a guardarse dentro
de la propia base. Este módulo cierra el paso para las bases que ya existían:

1. Agrega las columnas nuevas si faltan (``create_all`` no altera tablas ya
   creadas, así que un ALTER explícito es la única vía).
2. Libera ``ruta_archivo`` de su NOT NULL, porque las fotos nuevas ya no tienen
   archivo. SQLite no sabe relajar una restricción, así que ahí la tabla se
   reconstruye copiando las filas.
3. Lee cada archivo referenciado y lo guarda en su fila.

Es idempotente: puede ejecutarse cuantas veces haga falta. Las filas cuyo
archivo ya no esté en disco se dejan intactas y se informan, porque perder el
rastro de una evidencia debe notarse, no pasar en silencio.
"""
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from ..database import SessionLocal, engine
from ..models import EvidenciaFoto

log = logging.getLogger("yakuni.migracion")

# Columnas nuevas, con el tipo que entiende cada motor.
COLUMNAS = {
    "contenido": {"sqlite": "BLOB", "postgresql": "BYTEA"},
    "tipo_mime": {"sqlite": "VARCHAR(40)", "postgresql": "VARCHAR(40)"},
    "tamano_bytes": {"sqlite": "INTEGER", "postgresql": "INTEGER"},
}


def _agregar_columnas() -> list[str]:
    """Añade las columnas que falten. Devuelve las que tuvo que crear."""
    inspector = inspect(engine)
    if "evidencia_foto" not in inspector.get_table_names():
        return []

    existentes = {c["name"] for c in inspector.get_columns("evidencia_foto")}
    motor = engine.dialect.name
    creadas: list[str] = []

    with engine.begin() as conexion:
        for nombre, tipos in COLUMNAS.items():
            if nombre in existentes:
                continue
            tipo = tipos.get(motor, tipos["sqlite"])
            conexion.execute(
                text(f"ALTER TABLE evidencia_foto ADD COLUMN {nombre} {tipo}"))
            creadas.append(nombre)
    return creadas


def _liberar_ruta_archivo() -> bool:
    """Permite que ``ruta_archivo`` quede vacía. Devuelve si hubo que tocar algo.

    Las fotos nuevas no tienen archivo, pero la tabla creada por el esquema
    anterior exige la ruta. PostgreSQL lo resuelve con un ALTER; SQLite no sabe
    modificar restricciones, así que la tabla se reconstruye: se aparta la
    vieja, se crea la nueva desde el modelo y se copian las filas.
    """
    inspector = inspect(engine)
    if "evidencia_foto" not in inspector.get_table_names():
        return False

    columnas = {c["name"]: c for c in inspector.get_columns("evidencia_foto")}
    if columnas.get("ruta_archivo", {}).get("nullable", True):
        return False

    if engine.dialect.name == "postgresql":
        with engine.begin() as conexion:
            conexion.execute(text(
                "ALTER TABLE evidencia_foto ALTER COLUMN ruta_archivo DROP NOT NULL"))
        return True

    campos = ", ".join(columnas)
    with engine.begin() as conexion:
        conexion.execute(text("ALTER TABLE evidencia_foto RENAME TO evidencia_foto_previa"))
    EvidenciaFoto.__table__.create(bind=engine)
    with engine.begin() as conexion:
        conexion.execute(text(
            f"INSERT INTO evidencia_foto ({campos}) "
            f"SELECT {campos} FROM evidencia_foto_previa"))
        conexion.execute(text("DROP TABLE evidencia_foto_previa"))
    return True


def _tipo_de(ruta: Path) -> str:
    return mimetypes.guess_type(ruta.name)[0] or "image/jpeg"


def _trasladar(db: Session) -> tuple[int, list[str]]:
    """Guarda en la base las fotos que todavía viven en disco."""
    pendientes = (
        db.query(EvidenciaFoto)
        .filter(EvidenciaFoto.contenido.is_(None),
                EvidenciaFoto.ruta_archivo.isnot(None))
        .all()
    )
    movidas, perdidas = 0, []
    for e in pendientes:
        ruta = Path(e.ruta_archivo)
        if not ruta.exists():
            perdidas.append(e.ruta_archivo)
            continue
        datos = ruta.read_bytes()
        e.contenido = datos
        e.tipo_mime = _tipo_de(ruta)
        e.tamano_bytes = len(datos)
        movidas += 1
    if movidas:
        db.commit()
    return movidas, perdidas


def migrar() -> None:
    """Ejecuta la migración completa y deja constancia de lo ocurrido."""
    creadas = _agregar_columnas()
    if creadas:
        log.info("evidencia_foto: columnas añadidas → %s", ", ".join(creadas))
    if _liberar_ruta_archivo():
        log.info("evidencia_foto: ruta_archivo pasa a ser opcional")

    db = SessionLocal()
    try:
        movidas, perdidas = _trasladar(db)
        if movidas:
            log.info("evidencia_foto: %d foto(s) trasladadas del disco a la base", movidas)
        for ruta in perdidas:
            log.warning("evidencia_foto: el archivo ya no está en disco → %s", ruta)
    finally:
        db.close()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    migrar()
