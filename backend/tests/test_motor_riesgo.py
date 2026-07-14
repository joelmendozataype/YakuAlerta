"""Pruebas del motor de reglas con valores límite (CA-HU03, HU-18).

Frontera acordada en la Sprint Planning: 0.29/0.30/0.49/0.50 mg/L; 5/6 UNT.
"""
import pytest

from app.enums import NivelRiesgo
from app.rules import clasificar


@pytest.mark.parametrize("cloro,turbidez,esperado", [
    (0.72, 2.0, NivelRiesgo.VERDE),     # CA-HU03-01
    (0.50, 5.0, NivelRiesgo.VERDE),     # frontera inferior verde
    (0.41, 3.0, NivelRiesgo.AMARILLO),  # CA-HU03-02
    (0.49, 2.0, NivelRiesgo.AMARILLO),  # frontera superior amarillo
    (0.30, 2.0, NivelRiesgo.AMARILLO),  # frontera inferior amarillo
    (0.29, 2.0, NivelRiesgo.ROJO),      # justo bajo el umbral rojo
    (0.10, 2.0, NivelRiesgo.ROJO),      # CA-HU03-03 (cloro)
    (0.80, 8.0, NivelRiesgo.ROJO),      # CA-HU03-03 (turbidez)
    (0.80, 6.0, NivelRiesgo.ROJO),      # turbidez 6 > 5
    (0.80, 5.0, NivelRiesgo.VERDE),     # turbidez 5 = límite ok
])
def test_clasificacion_limites(cloro, turbidez, esperado):
    assert clasificar(cloro, turbidez).nivel == esperado


def test_regla_peor_caso():
    # Cloro verde pero turbidez roja → rojo (peor caso)
    assert clasificar(1.0, 9.0).nivel == NivelRiesgo.ROJO


def test_observacion_critica_fuerza_rojo():
    r = clasificar(0.9, 1.0, observaciones="El agua salió turbia y con olor")
    assert r.nivel == NivelRiesgo.ROJO


def test_laboratorio_no_conforme_fuerza_rojo():
    r = clasificar(0.9, 1.0, lab_no_conforme=True)
    assert r.nivel == NivelRiesgo.ROJO


def test_verde_no_es_alerta():
    assert not clasificar(0.72, 2.0).es_alerta


def test_amarillo_y_rojo_son_alerta():
    assert clasificar(0.41, 2.0).es_alerta
    assert clasificar(0.10, 2.0).es_alerta
