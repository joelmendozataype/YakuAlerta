"""Directorio de JASS que acompaña la ATM — HU-04 / RF-01.

Modelo del dominio
------------------
La **JASS es única por comunidad**: administra el sistema de agua de esa
comunidad y de ninguna otra. Por eso no existe una tabla ``jass``; la junta es
un atributo de la comunidad (relación 1:1).

La **ATM administra varias JASS**, todas las de su distrito. Este módulo arma
esa vista agregada: por cada junta, quién la integra, cuántos reservorios
cuida, cómo está su agua y hace cuánto no reporta.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..enums import NivelRiesgo, RolUsuario
from ..models import Comunidad, Medicion, Reservorio, Usuario
from ..schemas import JassOut, MiembroJass
from ..timeutils import aware_utc

# Quiénes integran la JASS: quien mide y quien preside.
ROLES_JASS = (RolUsuario.OPERADOR, RolUsuario.DIRECTIVO_JASS)

_SEVERIDAD = {NivelRiesgo.VERDE: 1, NivelRiesgo.AMARILLO: 2, NivelRiesgo.ROJO: 3}


def _peor_estado(db: Session, reservorios: list[Reservorio]):
    """Peor caso de la comunidad y fecha de la medición más reciente."""
    peor: NivelRiesgo | None = None
    ultima: datetime | None = None

    for r in reservorios:
        m = (
            db.query(Medicion).filter_by(reservorio_id=r.reservorio_id)
            .order_by(Medicion.fecha_hora.desc()).first()
        )
        if m is None:
            continue
        if peor is None or _SEVERIDAD[m.nivel_riesgo] > _SEVERIDAD[peor]:
            peor = m.nivel_riesgo
        fecha = aware_utc(m.fecha_hora)
        if ultima is None or fecha > ultima:
            ultima = fecha
    return peor, ultima


def _nombre_por_defecto(comunidad: Comunidad) -> str:
    """Una JASS sin nombre registrado se muestra por su comunidad."""
    return comunidad.jass_nombre or f"JASS {comunidad.nombre}"


def listar_jass(db: Session, ubigeo_id: int | None = None) -> list[JassOut]:
    """Las JASS de un distrito; sin ubigeo, las de todo el ámbito regional."""
    q = db.query(Comunidad)
    if ubigeo_id is not None:
        q = q.filter(Comunidad.ubigeo_id == ubigeo_id)

    salida: list[JassOut] = []
    for c in q.order_by(Comunidad.nombre):
        reservorios = db.query(Reservorio).filter_by(comunidad_id=c.comunidad_id).all()
        nivel, ultima = _peor_estado(db, reservorios)

        dias = (datetime.now(timezone.utc) - ultima).days if ultima else None
        # El umbral de silencio lo fija cada reservorio; basta que uno calle.
        umbral = min((r.umbral_silencio_dias for r in reservorios), default=7)
        en_silencio = dias is None or dias > umbral

        miembros = (
            db.query(Usuario)
            .filter(Usuario.comunidad_id == c.comunidad_id, Usuario.rol.in_(ROLES_JASS))
            .order_by(Usuario.rol, Usuario.nombres).all()
        )

        salida.append(JassOut(
            comunidad_id=c.comunidad_id,
            comunidad=c.nombre,
            jass_nombre=_nombre_por_defecto(c),
            poblacion_servida=c.poblacion_servida,
            reservorios=len(reservorios),
            nivel=nivel,
            ultima_medicion=ultima,
            dias_sin_medir=dias,
            en_silencio=en_silencio,
            miembros=[MiembroJass.model_validate(m) for m in miembros],
        ))
    return salida
