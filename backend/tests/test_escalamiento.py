"""Pruebas de la matriz de escalamiento y sus ámbitos territoriales — RF-06.

Verifican los requisitos que las bases del Desafío 2 formulan como obligatorios:
diferenciar niveles de riesgo, evitar alarmas injustificadas y alcanzar a los
usuarios principales, incluida la población usuaria.
"""
from app.enums import NivelRiesgo, RolUsuario
from app.rules.escalamiento import ambito_de, destinatarios_para


def test_verde_no_notifica_a_nadie():
    # Regla antifatiga: el nivel verde nunca genera notificaciones.
    assert destinatarios_para(NivelRiesgo.VERDE) == []


def test_amarillo_solo_operador_y_atm():
    destinos = destinatarios_para(NivelRiesgo.AMARILLO)
    assert set(destinos) == {RolUsuario.OPERADOR, RolUsuario.ATM}


def test_rojo_incluye_a_la_poblacion_y_a_la_autoridad_local():
    destinos = destinatarios_para(NivelRiesgo.ROJO)
    assert RolUsuario.POBLACION in destinos       # usuario principal de las bases
    assert RolUsuario.AUTORIDAD_LOCAL in destinos
    assert RolUsuario.SALUD in destinos
    assert RolUsuario.DIRECTIVO_JASS in destinos


def test_el_rojo_escala_sobre_el_amarillo():
    amarillo = set(destinatarios_para(NivelRiesgo.AMARILLO))
    rojo = set(destinatarios_para(NivelRiesgo.ROJO))
    assert amarillo < rojo   # el rojo es un superconjunto estricto


def test_ambitos_territoriales():
    assert ambito_de(RolUsuario.OPERADOR) == "comunidad"
    assert ambito_de(RolUsuario.POBLACION) == "comunidad"
    assert ambito_de(RolUsuario.ATM) == "distrito"
    assert ambito_de(RolUsuario.DESA) == "regional"
