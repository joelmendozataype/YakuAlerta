"""Autenticación por roles — HU-01 / RF-01."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import usuario_actual
from ..enums import RolUsuario
from ..models import Auditoria, AsignacionOperador, Reservorio, Usuario
from ..schemas import LoginIn, ReservorioOut, TokenOut, UsuarioOut
from ..security import crear_token, verificar_clave

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, request: Request, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.telefono == datos.telefono).first()
    if not usuario or not verificar_clave(datos.clave, usuario.clave_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Celular o clave incorrectos")
    if not usuario.activo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuario inactivo")

    db.add(Auditoria(
        usuario_id=usuario.usuario_id, accion="LOGIN", entidad_afectada="usuario",
        registro_id=str(usuario.usuario_id), ip_origen=request.client.host if request.client else None,
    ))

    # Reservorios asignados (para el operador; la sesión persiste en el dispositivo)
    reservorios: list[Reservorio] = []
    if usuario.rol == RolUsuario.OPERADOR:
        reservorios = (
            db.query(Reservorio)
            .join(AsignacionOperador, AsignacionOperador.reservorio_id == Reservorio.reservorio_id)
            .filter(AsignacionOperador.usuario_id == usuario.usuario_id,
                    AsignacionOperador.vigente.is_(True))
            .all()
        )
    db.commit()

    return TokenOut(
        access_token=crear_token(usuario.usuario_id, usuario.rol.value, usuario.nombres),
        usuario=UsuarioOut.model_validate(usuario),
        reservorios=[ReservorioOut.model_validate(r) for r in reservorios],
    )


@router.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(usuario_actual)):
    return UsuarioOut.model_validate(usuario)
