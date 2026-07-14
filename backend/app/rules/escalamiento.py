"""Matriz de escalamiento de alertas — HU-09/HU-10 / RF-06.

    🟡 AMARILLO → operador + ATM
    🔴 ROJO     → operador + ATM + directivo JASS + salud + autoridad comunal
    🟢 VERDE    → NADIE (regla antifatiga: el verde nunca notifica)

Los destinatarios se resuelven a nivel de comunidad: se notifica a los
usuarios cuyos roles corresponden al nivel y que pertenecen a la entidad
territorial de la medición.
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
    ],
}


def destinatarios_para(nivel: NivelRiesgo) -> list[RolUsuario]:
    """Roles que deben ser notificados para un nivel de riesgo dado."""
    return ROLES_POR_NIVEL.get(nivel, [])
