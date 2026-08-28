"""Motor de clasificación de riesgo (semáforo) — HU-03 / RF-04.

Regla de PEOR CASO conforme al D.S. N.° 031-2010-SA (MINSA, 2011):

    🟢 VERDE     cloro ≥ 0.50 mg/L  y  turbidez ≤ 5 UNT
    🟡 AMARILLO  cloro 0.30–0.49 mg/L  (y sin condición roja)
    🔴 ROJO      cloro < 0.30 mg/L  ó  turbidez > 5 UNT  ó
                 observación crítica  ó  laboratorio NO CONFORME

El nivel final es el MÁS SEVERO entre todos los factores evaluados.
Los umbrales NO están fijos en el código (RNF-07): se inyectan desde la
tabla ``parametro_normativo``. Aquí solo viven los valores por defecto.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..enums import NivelRiesgo

# Severidad para aplicar la regla de peor caso.
_SEVERIDAD = {NivelRiesgo.VERDE: 0, NivelRiesgo.AMARILLO: 1, NivelRiesgo.ROJO: 2}

# Palabras clave que, en las observaciones del operador, fuerzan nivel rojo.
PALABRAS_CRITICAS = (
    "turbia", "turbio", "color", "olor", "sabor", "heces", "animal muerto",
    "contamina", "sucia", "lodo", "barro", "espuma", "brote", "diarrea",
)


@dataclass(frozen=True)
class Umbrales:
    """Umbrales de clasificación (inyectables desde parametro_normativo).

    Cada parámetro tiene dos líneas y las dos significan lo mismo en ambos:
    la primera es el límite del D.S. N.° 031-2010-SA —al cruzarlo el agua ya
    incumple y hay que actuar—; la segunda es el criterio preventivo del
    proyecto, más severo, a partir del cual el agua se declara no apta.

    El cloro se lee al revés que la turbidez: menos desinfectante es peor,
    más partículas son peores. Por eso el rojo del cloro queda por debajo de
    su amarillo, y el de la turbidez por encima.
    """
    cloro_verde: float = 0.50       # cloro ≥ este valor → apto (norma)
    cloro_rojo: float = 0.30        # cloro < este valor → rojo (proyecto)
    turbidez_amarillo: float = 5.0  # turbidez > este valor → amarillo (norma)
    turbidez_rojo: float = 10.0     # turbidez > este valor → rojo (proyecto)


UMBRALES_DEFECTO = Umbrales()


@dataclass(frozen=True)
class ResultadoClasificacion:
    nivel: NivelRiesgo
    motivos: list[str]

    @property
    def es_alerta(self) -> bool:
        return self.nivel in (NivelRiesgo.AMARILLO, NivelRiesgo.ROJO)


def _peor(a: NivelRiesgo, b: NivelRiesgo) -> NivelRiesgo:
    return a if _SEVERIDAD[a] >= _SEVERIDAD[b] else b


def clasificar(
    cloro_mg_l: float | None,
    turbidez_unt: float | None,
    observaciones: str | None = None,
    lab_no_conforme: bool = False,
    umbrales: Umbrales = UMBRALES_DEFECTO,
) -> ResultadoClasificacion:
    """Clasifica una medición aplicando la regla de peor caso."""
    nivel = NivelRiesgo.VERDE
    motivos: list[str] = []

    # ── Factor cloro residual libre ──────────────────────────────
    if cloro_mg_l is not None:
        if cloro_mg_l < umbrales.cloro_rojo:
            nivel = _peor(nivel, NivelRiesgo.ROJO)
            motivos.append(f"Cloro {cloro_mg_l:.2f} mg/L < {umbrales.cloro_rojo:.2f} (desinfección crítica).")
        elif cloro_mg_l < umbrales.cloro_verde:
            nivel = _peor(nivel, NivelRiesgo.AMARILLO)
            motivos.append(f"Cloro {cloro_mg_l:.2f} mg/L por debajo de {umbrales.cloro_verde:.2f} mg/L (precaución).")
    else:
        motivos.append("Cloro no medido.")

    # ── Factor turbidez ──────────────────────────────────────────
    # Tres bandas, igual que el cloro: superar el límite de la norma avisa;
    # superar el del proyecto declara el agua no apta. Antes se pasaba de
    # verde a rojo de un salto y la JASS no tenía margen para reaccionar.
    if turbidez_unt is not None:
        if turbidez_unt > umbrales.turbidez_rojo:
            nivel = _peor(nivel, NivelRiesgo.ROJO)
            motivos.append(f"Turbidez {turbidez_unt:.2f} UNT > {umbrales.turbidez_rojo:.0f} UNT (la desinfección deja de ser confiable).")
        elif turbidez_unt > umbrales.turbidez_amarillo:
            nivel = _peor(nivel, NivelRiesgo.AMARILLO)
            motivos.append(f"Turbidez {turbidez_unt:.2f} UNT por encima de {umbrales.turbidez_amarillo:.0f} UNT (excede el límite normativo).")

    # ── Factor observación crítica del operador ─────────────────
    if observaciones:
        obs = observaciones.lower()
        encontrada = next((p for p in PALABRAS_CRITICAS if p in obs), None)
        if encontrada:
            nivel = _peor(nivel, NivelRiesgo.ROJO)
            motivos.append(f"Observación crítica detectada: «{encontrada}».")

    # ── Factor laboratorio (RF-15): fuerza rojo hasta cierre ────
    if lab_no_conforme:
        nivel = _peor(nivel, NivelRiesgo.ROJO)
        motivos.append("Resultado de laboratorio NO CONFORME (rojo forzado hasta cierre sanitario).")

    if nivel == NivelRiesgo.VERDE and not motivos:
        motivos.append("Parámetros dentro de norma.")

    return ResultadoClasificacion(nivel=nivel, motivos=motivos)
