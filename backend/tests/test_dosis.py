"""Pruebas del cálculo de dosis de recloración (CA-HU06)."""
from app.enums import NivelRiesgo
from app.rules import calcular_dosis


def test_verde_sin_recomendacion():
    assert calcular_dosis(NivelRiesgo.VERDE, 12, 0.72) is None


def test_amarillo_reservorio_12m3_hipoclorito_70():
    # CA-HU06-01: reservorio 12 m³, hipoclorito 70 %, plazo 48 h, dosis en gramos.
    reco = calcular_dosis(NivelRiesgo.AMARILLO, 12, 0.41, concentracion_insumo=70)
    assert reco is not None
    assert reco.plazo_remedicion_hrs == 48
    assert reco.gramos_hipoclorito > 0
    # demanda = max(1.0, 1.5-0.41)=1.09 → 1.09*12*100/70 ≈ 18.69 g
    assert abs(reco.gramos_hipoclorito - 18.69) < 0.5


def test_rojo_plazo_24h_y_protocolo_hervir():
    reco = calcular_dosis(NivelRiesgo.ROJO, 20, 0.10, concentracion_insumo=70)
    assert reco.plazo_remedicion_hrs == 24
    assert "HERVIR" in reco.protocolo


def test_dosis_escala_con_volumen():
    r1 = calcular_dosis(NivelRiesgo.ROJO, 10, 0.0)
    r2 = calcular_dosis(NivelRiesgo.ROJO, 20, 0.0)
    assert r2.gramos_hipoclorito > r1.gramos_hipoclorito
