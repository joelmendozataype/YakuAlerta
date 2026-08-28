"""Detección de silencio de datos — HU-15 / RF-11.

Un reservorio sin mediciones en más de ``umbral_silencio_dias`` (por defecto 7)
se considera en silencio: se recuerda al operador y se avisa a la ATM.
Se ejecuta como verificación diaria (APScheduler en main.py).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..enums import CanalNotif
from ..models import Medicion, Reservorio, Usuario, AsignacionOperador
from ..enums import RolUsuario
from ..timeutils import aware_utc
from . import notificaciones as notif

log = logging.getLogger("yakuni.silencio")


def reservorios_en_silencio(db: Session, ahora: datetime | None = None) -> list[tuple[Reservorio, int]]:
    """Devuelve (reservorio, días_sin_medir) para los que superan su umbral."""
    ahora = ahora or datetime.now(timezone.utc)
    ultimas = dict(
        db.query(Medicion.reservorio_id, func.max(Medicion.fecha_hora))
        .group_by(Medicion.reservorio_id)
        .all()
    )
    fuera: list[tuple[Reservorio, int]] = []
    for r in db.query(Reservorio).all():
        ultima = aware_utc(ultimas.get(r.reservorio_id))
        dias = (ahora - ultima).days if ultima else 9999
        if dias > r.umbral_silencio_dias:
            fuera.append((r, dias))
    return fuera


def verificar_silencio(db: Session) -> int:
    """Verificación diaria: notifica los silencios detectados. Devuelve el conteo."""
    fuera = reservorios_en_silencio(db)
    atms = db.query(Usuario).filter(Usuario.rol == RolUsuario.ATM, Usuario.activo.is_(True)).all()

    for reservorio, dias in fuera:
        txt = (f"⏰ Yakuni — SILENCIO DE DATOS\nReservorio {reservorio.codigo}: "
               f"{dias} días sin medición (umbral {reservorio.umbral_silencio_dias}). "
               f"Programar supervisión.")
        # Aviso al operador asignado
        for asig in db.query(AsignacionOperador).filter_by(reservorio_id=reservorio.reservorio_id, vigente=True):
            op = db.get(Usuario, asig.usuario_id)
            if op:
                notif.enviar(CanalNotif.SMS, op.telefono, txt)
        # Aviso a la ATM
        for atm in atms:
            notif.enviar(CanalNotif.WHATSAPP, atm.telefono, txt)

    if fuera:
        log.info("Silencio de datos: %d reservorios notificados.", len(fuera))
    return len(fuera)
