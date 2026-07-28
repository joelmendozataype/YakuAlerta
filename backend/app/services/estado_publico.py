"""Estado público del agua de una comunidad, para difusión a la población.

Alimenta tanto el afiche imprimible con QR como la página web que ese QR abre.
Solo expone información sanitaria de interés público: **nunca datos personales**
del operador ni valores técnicos que puedan malinterpretarse (Ley N.° 29733).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from ..enums import NivelRiesgo
from ..models import Comunidad, Medicion, Reservorio
from ..timeutils import aware_utc


@dataclass(frozen=True)
class EstadoPublico:
    comunidad: str
    distrito: str
    nivel: NivelRiesgo | None          # None = sin medición registrada
    titular: str                       # frase corta y contundente
    instruccion: str                   # qué debe hacer la población
    acciones: list[str]                # pasos concretos
    color: str                         # color semafórico (hex, sin '#')
    ultima_medicion: datetime | None
    reservorio: str | None

    @property
    def etiqueta(self) -> str:
        return {
            NivelRiesgo.VERDE: "AGUA SEGURA",
            NivelRiesgo.AMARILLO: "AGUA EN OBSERVACIÓN",
            NivelRiesgo.ROJO: "AGUA NO SEGURA",
        }.get(self.nivel, "SIN INFORMACIÓN")


# Mensajes dirigidos a la población: lenguaje llano, sin cifras técnicas.
_CONTENIDO = {
    NivelRiesgo.VERDE: (
        "El agua es apta para el consumo",
        "Puede beber el agua con normalidad.",
        [
            "Mantenga limpios sus recipientes de almacenamiento.",
            "Tape siempre el balde o bidón donde guarda el agua.",
            "Lávese las manos antes de manipular alimentos.",
        ],
        "15803D",
    ),
    NivelRiesgo.AMARILLO: (
        "El agua está en observación",
        "Por precaución, hierva el agua antes de beberla.",
        [
            "Hierva el agua 1 minuto antes de beber o cocinar.",
            "Dé prioridad al agua hervida para niñas, niños y personas enfermas.",
            "La JASS ya está corrigiendo la cloración del reservorio.",
        ],
        "B45309",
    ),
    NivelRiesgo.ROJO: (
        "El agua NO es segura para beber",
        "HIERVA el agua 1 minuto antes de consumirla.",
        [
            "Hierva toda el agua para beber, cocinar y lavar alimentos.",
            "No consuma el agua directamente del caño.",
            "Si hay personas con diarrea, acuda al establecimiento de salud.",
            "Espere el aviso de su JASS antes de volver a consumirla sin hervir.",
        ],
        "B91C1C",
    ),
}

_SIN_DATOS = (
    "Sin medición reciente",
    "Consulte con su JASS antes de confiar en este aviso.",
    [
        "Solicite a su JASS la medición semanal del reservorio.",
        "Como precaución, hierva el agua antes de beberla.",
    ],
    "64748B",
)


def estado_de_comunidad(db: Session, comunidad_id: int) -> EstadoPublico | None:
    """Resuelve el estado vigente de una comunidad con la regla de peor caso."""
    comunidad = db.get(Comunidad, comunidad_id)
    if comunidad is None:
        return None

    reservorios = db.query(Reservorio).filter_by(comunidad_id=comunidad_id).all()
    severidad = {NivelRiesgo.VERDE: 1, NivelRiesgo.AMARILLO: 2, NivelRiesgo.ROJO: 3}

    peor_nivel: NivelRiesgo | None = None
    peor_fecha: datetime | None = None
    peor_codigo: str | None = None

    for r in reservorios:
        ultima = (
            db.query(Medicion).filter_by(reservorio_id=r.reservorio_id)
            .order_by(Medicion.fecha_hora.desc()).first()
        )
        if ultima is None:
            continue
        if peor_nivel is None or severidad[ultima.nivel_riesgo] > severidad[peor_nivel]:
            peor_nivel = ultima.nivel_riesgo
            peor_fecha = aware_utc(ultima.fecha_hora)
            peor_codigo = r.codigo

    titular, instruccion, acciones, color = _CONTENIDO.get(peor_nivel, _SIN_DATOS)
    return EstadoPublico(
        comunidad=comunidad.nombre,
        distrito=comunidad.ubigeo.distrito if comunidad.ubigeo else "—",
        nivel=peor_nivel,
        titular=titular,
        instruccion=instruccion,
        acciones=list(acciones),
        color=color,
        ultima_medicion=peor_fecha,
        reservorio=peor_codigo,
    )
