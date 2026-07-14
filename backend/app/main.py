"""YakuAlerta — API REST (FastAPI).

Punto de entrada: CORS, routers, healthcheck y verificación diaria de silencio.
"""
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import settings
from .database import SessionLocal
from .routers import (
    admin, alertas, auth, laboratorio, mediciones, reportes, sync, tablero,
)
from .services.silencio import verificar_silencio

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
log = logging.getLogger("yakualerta")

scheduler = BackgroundScheduler(timezone="America/Lima")


def _job_silencio() -> None:
    db = SessionLocal()
    try:
        verificar_silencio(db)
        db.commit()
    except Exception as exc:  # pragma: no cover
        log.error("Job de silencio falló: %s", exc)
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Con SQLite u otros motores sin init.sql, aseguramos el esquema al arrancar.
    if settings.database_url.startswith("sqlite"):
        from .database import crear_tablas
        crear_tablas()
    # Verificación diaria de silencio de datos (HU-15) a las 06:00.
    scheduler.add_job(_job_silencio, "cron", hour=6, minute=0, id="silencio_diario",
                      replace_existing=True)
    scheduler.start()
    log.info("YakuAlerta API v%s lista. Modo SMS: %s", __version__, settings.sms_modo)
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="YakuAlerta API",
    description="Sistema de alerta temprana para agua no segura — Hackathon UNH 2026.",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, admin, mediciones, sync, alertas, tablero, laboratorio, reportes):
    app.include_router(r.router)


@app.get("/", tags=["health"])
def raiz():
    return {"servicio": "YakuAlerta API", "version": __version__, "docs": "/docs"}


@app.get("/health", tags=["health"])
def health():
    from sqlalchemy import text
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        estado_db = "ok"
    except Exception as exc:  # pragma: no cover
        estado_db = f"error: {exc}"
    finally:
        db.close()
    return {"status": "ok", "db": estado_db}
