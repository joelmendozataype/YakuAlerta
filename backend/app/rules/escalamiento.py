"""Matriz de escalamiento de alertas — HU-09/HU-10 / RF-06.

    🟡 AMARILLO → operador + ATM
    🔴 ROJO     → operador + ATM + directivo JASS + salud + autoridad local
                  + contacto comunitario (difusión a la población usuaria)
    🟢 VERDE    → NADIE (regla antifatiga: el verde nunca notifica)

Los destinatarios se resuelven por jurisdicción territorial: se notifica a los
usuarios cuyo rol corresponde al nivel Y cuyo ámbito (comunidad o distrito)
coincide con el de la medición. Ver ``services/procesamiento.py``.
"""
from __future__ import annotations

from ..enums import NivelRiesgo, RolUsuario

ROLES_POR_NIVEL: dict[NivelRiesgo, list[RolUsuario]] = {
    NivelRiesgo.VERDE: [],
    NivelRiesgo.AMARILLO: [RolUsuario.OPERADOR, RolUsuario.ATM],
    NivelRiesgo.ROJO: [
        RolUsuario.OPERADOR,
        RolUsuario.ATM,
        RolUsuario.DIRECTIVO_JASS,
        RolUsuario.SALUD,
        RolUsuario.AUTORIDAD_LOCAL,
        RolUsuario.POBLACION,
    ],
}

# Ámbito con el que se filtra cada rol al notificar:
#   'comunidad' → solo los de la comunidad de la medición
#   'distrito'  → los del distrito (ubigeo) de la medición
#   'regional'  → sin restricción territorial
AMBITO_POR_ROL: dict[RolUsuario, str] = {
    RolUsuario.OPERADOR: "comunidad",
    RolUsuario.DIRECTIVO_JASS: "comunidad",
    RolUsuario.AUTORIDAD_LOCAL: "comunidad",
    RolUsuario.POBLACION: "comunidad",
    RolUsuario.ATM: "distrito",
    RolUsuario.SALUD: "distrito",
    RolUsuario.DESA: "regional",
    RolUsuario.DRVCS: "regional",
}


def destinatarios_para(nivel: NivelRiesgo) -> list[RolUsuario]:
    """Roles que deben ser notificados para un nivel de riesgo dado."""
    return ROLES_POR_NIVEL.get(nivel, [])


def ambito_de(rol: RolUsuario) -> str:
    """Alcance territorial con el que se filtra un rol al notificar."""
    return AMBITO_POR_ROL.get(rol, "regional")
