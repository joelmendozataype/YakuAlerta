"""A quién representa una cuenta — entidad y ámbito territorial.

La entidad no se teclea. Se deduce del actor y del territorio, igual que el
código de un reservorio: escrita a mano, la misma junta terminaría registrada
como «JASS COM-01», «Jass com 01» y «JASS de la comunidad 01», y el padrón
dejaría de poder agruparse por entidad.

El ámbito manda sobre qué territorio hace falta:

    comunal   → la cuenta pertenece a una comunidad concreta y sin ella no
                significa nada: un operador sin comunidad no tiene reservorio
                que medir, y un promotor sin comunidad no tiene a quién avisar.
    distrital → basta el distrito; una comunidad la dejaría fuera de las demás.
    regional  → sin territorio: alcanza a toda la región.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..enums import RolUsuario
from ..models import Comunidad, Ubigeo
from ..rules.escalamiento import ambito_de

# Entidades de alcance regional: no dependen de ningún territorio.
ENTIDAD_REGIONAL = {
    RolUsuario.DESA: "DIRESA Huancavelica",
    RolUsuario.DRVCS: "Dirección Regional de Vivienda y Saneamiento",
    RolUsuario.ADMIN: "Administración del sistema",
}


def _titulo(texto: str) -> str:
    """LIRCAY → Lircay, para leerse dentro de una frase."""
    return " ".join(p.capitalize() for p in texto.split())


def entidad_de(db: Session, rol: RolUsuario,
               comunidad: Comunidad | None, ubigeo: Ubigeo | None) -> str:
    """Nombre de la entidad a la que representa una cuenta."""
    if rol in ENTIDAD_REGIONAL:
        return ENTIDAD_REGIONAL[rol]

    if rol in (RolUsuario.OPERADOR, RolUsuario.DIRECTIVO_JASS):
        # La junta ya tiene nombre propio: es el de su comunidad.
        return comunidad.jass_nombre or f"JASS {comunidad.nombre}"

    if rol == RolUsuario.AUTORIDAD_LOCAL:
        return f"Autoridad comunal de {comunidad.nombre}"

    if rol == RolUsuario.POBLACION:
        return f"Difusión a la población · {comunidad.nombre}"

    distrito = _titulo(ubigeo.distrito) if ubigeo else "su distrito"
    if rol == RolUsuario.ATM:
        return f"Municipalidad Distrital de {distrito}"
    if rol == RolUsuario.SALUD:
        return f"Establecimiento de salud de {distrito}"
    return distrito


def exigir_territorio(rol: RolUsuario, comunidad_id: int | None) -> None:
    """Comprueba que la cuenta tenga el territorio que su ámbito requiere."""
    ambito = ambito_de(rol)
    if ambito == "comunidad" and comunidad_id is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Esta cuenta trabaja en una comunidad concreta: indique cuál.",
        )
    if ambito != "comunidad" and comunidad_id is not None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Esta cuenta es de alcance distrital o regional: no se asigna a una "
            "sola comunidad, o quedaría fuera de las demás.",
        )
