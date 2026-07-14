"""Registro de una medición con deduplicación por UUID — HU-12 / RF-08.

Deduplicación: si ya existe una medición con el mismo ``uuid_registro`` (por
ejemplo, porque el registro viajó primero por SMS y luego por datos), no se
inserta un duplicado; se actualiza su vía de recepción a SINCRONIZADO.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..enums import EstadoSync, NivelRiesgo
from ..models import Medicion
from ..schemas import MedicionIn
from .procesamiento import procesar_medicion


def registrar_medicion(db: Session, datos: MedicionIn, usuario_id: int) -> tuple[Medicion, bool]:
    """Inserta (o deduplica) una medición y ejecuta el pipeline de riesgo.

    Devuelve ``(medicion, duplicada)``. No hace commit (lo hace el router).
    """
    existente = db.query(Medicion).filter(Medicion.uuid_registro == datos.uuid_registro).first()
    if existente:
        # Ya llegó antes (p. ej. por SMS): promover a sincronizado, sin duplicar.
        if existente.estado_sync != EstadoSync.SINCRONIZADO and datos.origen == EstadoSync.SINCRONIZADO:
            existente.estado_sync = EstadoSync.SINCRONIZADO
        return existente, True

    medicion = Medicion(
        uuid_registro=datos.uuid_registro,
        reservorio_id=datos.reservorio_id,
        usuario_id=usuario_id,
        fecha_hora=datos.fecha_hora,
        cloro_mg_l=datos.cloro_mg_l,
        turbidez_unt=datos.turbidez_unt,
        metodo_cloro=datos.metodo_cloro,
        observaciones=datos.observaciones,
        estado_sync=datos.origen,
        nivel_riesgo=NivelRiesgo.VERDE,  # provisional; procesar_medicion lo fija
    )
    db.add(medicion)
    db.flush()
    procesar_medicion(db, medicion)
    return medicion, False
