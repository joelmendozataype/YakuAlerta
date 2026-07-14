"""Cálculo de la dosis de recloración y protocolos de acción — HU-06 / RF-05, RF-07.

Fórmula de recloración (masa de producto comercial de hipoclorito):

    demanda (mg/L) = cloro_objetivo − cloro_medido        (nunca < mínima)
    gramos_producto = demanda(mg/L) × volumen(m³) × 100 / concentración(%)

Deducción de unidades:
    demanda[mg/L] × volumen[m³]×1000[L] = mg de cloro activo requerido
    mg / 1000 = g de cloro activo
    g_activo / (concentración/100) = g de producto comercial
    ⇒ g_producto = demanda × volumen × 1000 / 1000 / (conc/100)
                  = demanda × volumen × 100 / conc
"""
from __future__ import annotations

from dataclasses import dataclass

from ..enums import NivelRiesgo

# Cloro residual objetivo tras la recloración (mg/L). Deja margen sobre el
# mínimo normativo de 0.5 mg/L para cubrir la demanda del sistema.
CLORO_OBJETIVO = 1.5
DEMANDA_MINIMA = 1.0  # corrección mínima aplicada si el cloro medido es alto

# Plazos de remediación por nivel (RF-07).
PLAZO_HRS = {NivelRiesgo.ROJO: 24, NivelRiesgo.AMARILLO: 48}

PROTOCOLO_ROJO = (
    "AGUA NO SEGURA. Acciones inmediatas:\n"
    "1) Avisar a la población: HERVIR el agua antes de consumir (1 min a ebullición).\n"
    "2) Limpieza y desinfección del reservorio.\n"
    "3) Recloración con la dosis indicada.\n"
    "4) Evaluar suspensión preventiva del servicio.\n"
    "5) Remedir en 24 horas y registrar el resultado."
)
PROTOCOLO_AMARILLO = (
    "AGUA EN RIESGO. Acciones:\n"
    "1) Recloración con la dosis indicada para restablecer el cloro residual.\n"
    "2) Verificar el sistema de dosificación (goteo/pastillas).\n"
    "3) Remedir en 48 horas y registrar el resultado."
)
PROTOCOLO_VERDE = "Agua segura. Continuar la vigilancia semanal habitual."


@dataclass(frozen=True)
class RecomendacionCalculada:
    gramos_hipoclorito: float
    concentracion_insumo: float
    plazo_remedicion_hrs: int
    protocolo: str


def calcular_dosis(
    nivel: NivelRiesgo,
    volumen_m3: float,
    cloro_medido: float | None,
    concentracion_insumo: float = 70.0,
) -> RecomendacionCalculada | None:
    """Devuelve la recomendación de recloración; ``None`` si el nivel es verde."""
    if nivel == NivelRiesgo.VERDE:
        return None

    concentracion_insumo = max(1.0, min(100.0, concentracion_insumo))
    medido = cloro_medido if cloro_medido is not None else 0.0
    demanda = max(DEMANDA_MINIMA, CLORO_OBJETIVO - medido)

    gramos = demanda * volumen_m3 * 100.0 / concentracion_insumo

    protocolo = PROTOCOLO_ROJO if nivel == NivelRiesgo.ROJO else PROTOCOLO_AMARILLO
    return RecomendacionCalculada(
        gramos_hipoclorito=round(gramos, 2),
        concentracion_insumo=round(concentracion_insumo, 2),
        plazo_remedicion_hrs=PLAZO_HRS[nivel],
        protocolo=protocolo,
    )
