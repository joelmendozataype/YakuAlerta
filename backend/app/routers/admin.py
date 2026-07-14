"""Gestión de entidades del sistema — HU-04 / RF-01, RF-04.

Alta de comunidades, reservorios, usuarios y asignaciones operador↔reservorio.
Restringido al rol ADMIN (mínimo privilegio, RNF-05).
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
    ComunidadIn, ComunidadOut, ReservorioIn, ReservorioOut, UbigeoOut,
    UsuarioIn, UsuarioOut,
)
from ..security import hash_clave

router = APIRouter(prefix="/admin", tags=["admin"],
                   dependencies=[Depends(requiere_roles(RolUsuario.ADMIN))])


# ─── Ubigeo ──────────────────────────────────────────────────────
@router.get("/ubigeos", response_model=list[UbigeoOut])
def listar_ubigeos(db: Session = Depends(get_db)):
    return [UbigeoOut.model_validate(u) for u in db.query(Ubigeo).order_by(Ubigeo.distrito)]


# ─── Comunidades ─────────────────────────────────────────────────
@router.get("/comunidades", response_model=list[ComunidadOut])
def listar_comunidades(db: Session = Depends(get_db)):
    return [ComunidadOut.model_validate(c) for c in db.query(Comunidad).order_by(Comunidad.nombre)]


@router.post("/comunidades", response_model=ComunidadOut, status_code=201)
def crear_comunidad(datos: ComunidadIn, db: Session = Depends(get_db)):
    c = Comunidad(**datos.model_dump())
    db.add(c)
    _commit(db)
    db.refresh(c)
    return ComunidadOut.model_validate(c)


# ─── Reservorios ─────────────────────────────────────────────────
@router.get("/reservorios", response_model=list[ReservorioOut])
def listar_reservorios(db: Session = Depends(get_db)):
    return [ReservorioOut.model_validate(r) for r in db.query(Reservorio).order_by(Reservorio.codigo)]


@router.post("/reservorios", response_model=ReservorioOut, status_code=201)
def crear_reservorio(datos: ReservorioIn, db: Session = Depends(get_db)):
    r = Reservorio(**datos.model_dump())
    db.add(r)
    _commit(db)
    db.refresh(r)
    return ReservorioOut.model_validate(r)


# ─── Usuarios ────────────────────────────────────────────────────
@router.get("/usuarios", response_model=list[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db)):
    return [UsuarioOut.model_validate(u) for u in db.query(Usuario).order_by(Usuario.nombres)]


@router.post("/usuarios", response_model=UsuarioOut, status_code=201)
def crear_usuario(datos: UsuarioIn, db: Session = Depends(get_db)):
    u = Usuario(
        nombres=datos.nombres, telefono=datos.telefono,
        clave_hash=hash_clave(datos.clave), rol=datos.rol, entidad=datos.entidad,
    )
    db.add(u)
    _commit(db)
    db.refresh(u)
    return UsuarioOut.model_validate(u)


# ─── Asignaciones operador ↔ reservorio ─────────────────────────
@router.post("/asignaciones", status_code=201)
def asignar_operador(usuario_id: int, reservorio_id: int, db: Session = Depends(get_db)):
    usuario = db.get(Usuario, usuario_id)
    if not usuario or usuario.rol != RolUsuario.OPERADOR:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El usuario debe existir y ser OPERADOR")
    if not db.get(Reservorio, reservorio_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservorio no encontrado")
    a = AsignacionOperador(usuario_id=usuario_id, reservorio_id=reservorio_id)
    db.add(a)
    _commit(db)
    return {"asignacion_id": a.asignacion_id, "usuario_id": usuario_id, "reservorio_id": reservorio_id}


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, f"Violación de integridad: {e.orig}")
