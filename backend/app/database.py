"""Motor de base de datos y sesión (SQLAlchemy 2.0).

Soporta PostgreSQL (producción / entrega) y SQLite (desarrollo sin instalar
nada). El motor se elige según ``DATABASE_URL``:
    postgresql+psycopg://...   → PostgreSQL
    sqlite:///./yakualerta.db  → SQLite (archivo local)
"""
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from .config import settings

_es_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    # SQLite necesita permitir el uso entre hilos (FastAPI usa varios).
    connect_args={"check_same_thread": False} if _es_sqlite else {},
)

# SQLite no exige claves foráneas por defecto: lo activamos para respetar
# las restricciones ON DELETE del modelo.
if _es_sqlite:
    @event.listens_for(engine, "connect")
    def _fk_pragma(dbapi_conn, _record):  # pragma: no cover
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def crear_tablas() -> None:
    """Crea el esquema si no existe (usado con SQLite; en PostgreSQL lo hace init.sql)."""
    from . import models  # noqa: F401 — registra los modelos en el metadata
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI: una sesión por petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
