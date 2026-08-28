"""Gestión de entidades del sistema — HU-04 / RF-01, RF-04.

Alta de comunidades, reservorios, usuarios y asignaciones operador↔reservorio.

Quién administra
----------------
El **Área Técnica Municipal (ATM)** administra su distrito: es quien conoce a
las JASS, visita los reservorios y mantiene el directorio al día. El rol ADMIN
conserva el alcance regional para la configuración transversal.

Dos salvaguardas sostienen esa delegación (RNF-05, mínimo privilegio):

1. **Ámbito territorial**: la ATM solo ve y crea entidades de su propio
   distrito; no puede tocar las de otro.
2. **Sin escalamiento de privilegios**: la ATM da de alta perfiles de campo
   (operador, directivo JASS, autoridad local y contacto comunitario), pero no
   cuentas regionales (DESA, DRVCS) ni administradores.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import requiere_roles
from ..enums import RolUsuario
from ..models import (
    AsignacionOperador, Comunidad, Reservorio, Ubigeo, Usuario,
)
from ..schemas import (
    ComunidadIn, ComunidadOut, JassOut, ReservorioIn, ReservorioOut, UbigeoOut,
    UsuarioIn, UsuarioOut,
)
from ..services.directorio_jass import listar_jass
from ..security import hash_clave

router = APIRouter(prefix="/admin", tags=["admin"])

# La ATM administra su distrito; el ADMIN, todo el ámbito regional.
_administra = requiere_roles(RolUsuario.ATM, RolUsuario.ADMIN)

# Perfiles de campo que la ATM puede dar de alta.
ROLES_QUE_CREA_LA_ATM = {
    RolUsuario.OPERADOR,
    RolUsuario.DIRECTIVO_JASS,
    RolUsuario.AUTORIDAD_LOCAL,
    RolUsuario.POBLACION,
}


def _es_regional(usuario: Usuario) -> bool:
    """El ADMIN (y cualquier cuenta sin distrito) trabaja sin restricción."""
    return usuario.rol == RolUsuario.ADMIN or usuario.ubigeo_id is None


def _exige_su_distrito(usuario: Usuario, ubigeo_id: int | None) -> None:
    """Impide que una ATM administre entidades de otro distrito."""
    if _es_regional(usuario):
        return
    if ubigeo_id != usuario.ubigeo_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo puede administrar entidades de su propio distrito.",
        )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, f"Violación de integridad: {e.orig}")


# ─── Directorio de JASS ─────────────────────────────────────────
@router.get("/jass", response_model=list[JassOut])
def directorio_jass(db: Session = Depends(get_db),
                    usuario: Usuario = Depends(_administra)):
    """Las JASS del distrito de la ATM.

    Una JASS por comunidad; la ATM acompaña a todas las de su distrito y ve de
    un vistazo cuál dejó de reportar y cuál tiene el agua en rojo.
    """
    return listar_jass(db, None if _es_regional(usuario) else usuario.ubigeo_id)


# ─── Ubigeo ──────────────────────────────────────────────────────
@router.get("/ubigeos", response_model=list[UbigeoOut])
def listar_ubigeos(db: Session = Depends(get_db),
                   usuario: Usuario = Depends(_administra)):
    q = db.query(Ubigeo).order_by(Ubigeo.distrito)
    if not _es_regional(usuario):
        q = q.filter(Ubigeo.ubigeo_id == usuario.ubigeo_id)
    return [UbigeoOut.model_validate(u) for u in q]


# ─── Comunidades ─────────────────────────────────────────────────
@router.get("/comunidades", response_model=list[ComunidadOut])
def listar_comunidades(db: Session = Depends(get_db),
                       usuario: Usuario = Depends(_administra)):
    q = db.query(Comunidad).order_by(Comunidad.nombre)
    if not _es_regional(usuario):
        q = q.filter(Comunidad.ubigeo_id == usuario.ubigeo_id)
    return [ComunidadOut.model_validate(c) for c in q]


@router.post("/comunidades", response_model=ComunidadOut, status_code=201)
def crear_comunidad(datos: ComunidadIn, db: Session = Depends(get_db),
                    usuario: Usuario = Depends(_administra)):
    _exige_su_distrito(usuario, datos.ubigeo_id)
    c = Comunidad(**datos.model_dump())
    db.add(c)
    _commit(db)
    db.refresh(c)
    return ComunidadOut.model_validate(c)


# ─── Reservorios ─────────────────────────────────────────────────
@router.get("/reservorios", response_model=list[ReservorioOut])
def listar_reservorios(db: Session = Depends(get_db),
                       usuario: Usuario = Depends(_administra)):
    q = db.query(Reservorio).order_by(Reservorio.codigo)
    if not _es_regional(usuario):
        q = (q.join(Comunidad, Reservorio.comunidad_id == Comunidad.comunidad_id)
              .filter(Comunidad.ubigeo_id == usuario.ubigeo_id))
    return [ReservorioOut.model_validate(r) for r in q]


@router.post("/reservorios", response_model=ReservorioOut, status_code=201)
def crear_reservorio(datos: ReservorioIn, db: Session = Depends(get_db),
                     usuario: Usuario = Depends(_administra)):
    comunidad = db.get(Comunidad, datos.comunidad_id)
    if not comunidad:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comunidad no encontrada")
    _exige_su_distrito(usuario, comunidad.ubigeo_id)

    r = Reservorio(**datos.model_dump())
    db.add(r)
    _commit(db)
    db.refresh(r)
    return ReservorioOut.model_validate(r)


# ─── Usuarios ────────────────────────────────────────────────────
@router.get("/usuarios", response_model=list[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db),
                    usuario: Usuario = Depends(_administra)):
    q = db.query(Usuario).order_by(Usuario.nombres)
    if not _es_regional(usuario):
        q = q.filter(Usuario.ubigeo_id == usuario.ubigeo_id)
    return [UsuarioOut.model_validate(u) for u in q]


@router.post("/usuarios", response_model=UsuarioOut, status_code=201)
def crear_usuario(datos: UsuarioIn, db: Session = Depends(get_db),
                  usuario: Usuario = Depends(_administra)):
    if not _es_regional(usuario):
        # La ATM no puede crear cuentas de rango igual o superior al suyo.
        if datos.rol not in ROLES_QUE_CREA_LA_ATM:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"La ATM puede registrar perfiles de campo "
                f"({', '.join(sorted(r.value for r in ROLES_QUE_CREA_LA_ATM))}). "
                f"Las cuentas regionales las crea la DIRESA/DESA.",
            )
        # La cuenta nace en el distrito de quien la registra.
        datos.ubigeo_id = usuario.ubigeo_id

    u = Usuario(
        nombres=datos.nombres, dni=datos.dni, telefono=datos.telefono,
        clave_hash=hash_clave(datos.clave), rol=datos.rol, entidad=datos.entidad,
        ubigeo_id=datos.ubigeo_id, comunidad_id=datos.comunidad_id,
    )
    db.add(u)
    _commit(db)
    db.refresh(u)
    return UsuarioOut.model_validate(u)


# ─── Asignaciones operador ↔ reservorio ─────────────────────────
@router.post("/asignaciones", status_code=201)
def asignar_operador(usuario_id: int, reservorio_id: int,
                     db: Session = Depends(get_db),
                     usuario: Usuario = Depends(_administra)):
    operador = db.get(Usuario, usuario_id)
    if not operador or operador.rol != RolUsuario.OPERADOR:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El usuario debe existir y ser OPERADOR")

    reservorio = db.get(Reservorio, reservorio_id)
    if not reservorio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservorio no encontrado")
    comunidad = db.get(Comunidad, reservorio.comunidad_id)
    _exige_su_distrito(usuario, comunidad.ubigeo_id if comunidad else None)

    a = AsignacionOperador(usuario_id=usuario_id, reservorio_id=reservorio_id)
    db.add(a)
    _commit(db)
    return {"asignacion_id": a.asignacion_id, "usuario_id": usuario_id,
            "reservorio_id": reservorio_id}
