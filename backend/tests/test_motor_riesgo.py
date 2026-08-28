"""Pruebas del motor de reglas con valores límite (CA-HU03, HU-18).

Fronteras: 0.29/0.30/0.49/0.50 mg/L de cloro; 5/5.1/10/10.1 UNT de turbidez.

Ambos parámetros tienen tres bandas y las dos líneas significan lo mismo en
los dos: la del D.S. N.° 031-2010-SA abre el amarillo y la del proyecto, más
severa, el rojo. Lo que cambia es la dirección —menos cloro es peor, más
turbidez es peor—, no el criterio.
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
    (0.80, 5.0, NivelRiesgo.VERDE),     # turbidez en el límite de la norma
    (0.80, 5.1, NivelRiesgo.AMARILLO),  # excede la norma: avisa, no condena
    (0.80, 8.0, NivelRiesgo.AMARILLO),  # CA-HU03-03 (turbidez)
    (0.80, 10.0, NivelRiesgo.AMARILLO), # frontera superior amarillo
    (0.80, 10.1, NivelRiesgo.ROJO),     # la desinfección deja de ser confiable
    (0.80, 20.0, NivelRiesgo.ROJO),
])
def test_clasificacion_limites(cloro, turbidez, esperado):
    assert clasificar(cloro, turbidez).nivel == esperado


def test_regla_peor_caso():
    # Cloro verde pero turbidez roja → rojo (peor caso)
    assert clasificar(1.0, 12.0).nivel == NivelRiesgo.ROJO
    # Y a la inversa: turbidez limpia no rescata un cloro crítico.
    assert clasificar(0.10, 1.0).nivel == NivelRiesgo.ROJO


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


def test_la_turbidez_avisa_antes_de_condenar():
    """El salto de verde a rojo dejaba a la JASS sin margen de reacción."""
    r = clasificar(0.80, 7.0)
    assert r.nivel == NivelRiesgo.AMARILLO
    assert any("límite normativo" in m for m in r.motivos)


def test_los_umbrales_de_turbidez_son_configurables():
    """Un cambio de norma debe regir sin tocar el código (RNF-07)."""
    from app.rules.motor_riesgo import Umbrales

    estrictos = Umbrales(turbidez_amarillo=1.0, turbidez_rojo=2.0)
    assert clasificar(0.80, 0.9, umbrales=estrictos).nivel == NivelRiesgo.VERDE
    assert clasificar(0.80, 1.5, umbrales=estrictos).nivel == NivelRiesgo.AMARILLO
    assert clasificar(0.80, 2.5, umbrales=estrictos).nivel == NivelRiesgo.ROJO
