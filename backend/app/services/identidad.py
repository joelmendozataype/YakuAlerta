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


def resolver_comunidad(db: Session, ubigeo_id: int | None, nombre: str,
                       rol: RolUsuario):
    """Busca la comunidad por su nombre dentro del distrito, o la crea.

    Devuelve ``(comunidad, creada, reservorio)``. Al crearla nace también su
    JASS —la relación es 1:1— y su primer reservorio, cuyo código arma el
    sistema con la estructura acordada.

    La búsqueda ignora mayúsculas y espacios sobrantes: «com-01», «COM-01» y
    «COM 01 » son la misma comunidad, y admitir las tres crearía duplicados
    que después nadie sabría cuál es cuál.
    """
    from ..models import Reservorio
    from .codigo_reservorio import _normalizar, siguiente_codigo

    if ubigeo_id is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Indique el distrito al que pertenece la comunidad.",
        )
    limpio = " ".join(nombre.split())
    if not limpio:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Escriba el nombre de la comunidad.")

    clave = _normalizar(limpio)
    for c in db.query(Comunidad).filter(Comunidad.ubigeo_id == ubigeo_id):
        if _normalizar(c.nombre) == clave:
            return c, False, None

    # Una comunidad nace con su JASS, no con otro rol: es la junta la que
    # administra el sistema de agua, y sin ella la comunidad no tendría quién
    # mida su reservorio.
    if rol not in (RolUsuario.OPERADOR, RolUsuario.DIRECTIVO_JASS):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"La comunidad «{limpio}» aún no está registrada. Se registra al dar "
            f"de alta su JASS, que es quien administra su sistema de agua.",
        )

    comunidad = Comunidad(ubigeo_id=ubigeo_id, nombre=limpio,
                          jass_nombre=f"JASS {limpio}")
    db.add(comunidad)
    db.flush()

    reservorio = Reservorio(
        comunidad_id=comunidad.comunidad_id,
        codigo=siguiente_codigo(db, comunidad),
        volumen_m3=0, tipo_sistema="Gravedad",
        estado_infra="Por registrar", umbral_silencio_dias=7,
    )
    db.add(reservorio)
    db.flush()
    return comunidad, True, reservorio
