"""Autenticación por roles — HU-01 / RF-01."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import usuario_actual
from ..enums import ROLES_POR_GRUPO, RolUsuario, grupo_de_rol
from ..models import Auditoria, AsignacionOperador, Reservorio, Usuario
from ..schemas import (
    LoginIn, RecuperacionConfirmarIn, RecuperacionSolicitarIn,
    RecuperacionSolicitarOut, ReservorioOut, TokenOut, UsuarioOut,
)
from ..services import recuperacion
from ..security import crear_token, verificar_clave

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, request: Request, db: Session = Depends(get_db)):
    # El acceso desde la app es por DNI; el tablero web mantiene el celular.
    if datos.dni:
        usuario = db.query(Usuario).filter(Usuario.dni == datos.dni).first()
        etiqueta = "DNI"
    else:
        usuario = db.query(Usuario).filter(Usuario.telefono == datos.telefono).first()
        etiqueta = "Celular"

    if not usuario or not verificar_clave(datos.clave, usuario.clave_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"{etiqueta} o clave incorrectos")
    if not usuario.activo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuario inactivo")

    # El rol elegido en la app debe corresponder al de la cuenta: evita que
    # alguien ingrese por una puerta que no le toca y ve funciones ajenas.
    if datos.grupo_rol is not None:
        if usuario.rol not in ROLES_POR_GRUPO.get(datos.grupo_rol, ()):
            propio = grupo_de_rol(usuario.rol)
            sugerencia = f" Seleccione «{propio.value}»." if propio else ""
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Su cuenta no corresponde al rol seleccionado.{sugerencia}",
            )

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


# ═══════════════════════════════════════════════════════════════
#  Recuperación de clave por código SMS
# ═══════════════════════════════════════════════════════════════

@router.post("/recuperacion/solicitar", response_model=RecuperacionSolicitarOut)
def solicitar_recuperacion(datos: RecuperacionSolicitarIn, request: Request,
                           db: Session = Depends(get_db)):
    """Envía un código de un solo uso al celular registrado del usuario.

    La respuesta es la misma exista o no el DNI: así nadie puede averiguar qué
    documentos están registrados en el sistema.
    """
    ip = request.client.host if request.client else None
    enmascarado = recuperacion.solicitar(db, datos.dni, ip)
    db.add(Auditoria(accion="RECUPERACION_SOLICITADA", entidad_afectada="usuario",
                     registro_id=datos.dni, ip_origen=ip))
    db.commit()
    return RecuperacionSolicitarOut(
        mensaje=("Si el DNI está registrado, enviamos un código por mensaje de "
                 "texto al celular asociado."),
        telefono_enmascarado=enmascarado,
        vigencia_min=recuperacion.VIGENCIA_MIN,
    )


@router.post("/recuperacion/confirmar")
def confirmar_recuperacion(datos: RecuperacionConfirmarIn, request: Request,
                           db: Session = Depends(get_db)):
    """Valida el código recibido y establece la clave nueva."""
    try:
        usuario = recuperacion.confirmar(db, datos.dni, datos.codigo, datos.clave_nueva)
    except recuperacion.ErrorRecuperacion as e:
        db.commit()   # conserva el conteo de intentos fallidos
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    db.add(Auditoria(usuario_id=usuario.usuario_id, accion="CLAVE_RESTABLECIDA",
                     entidad_afectada="usuario", registro_id=str(usuario.usuario_id),
                     ip_origen=request.client.host if request.client else None))
    db.commit()
    return {"mensaje": "Su clave fue actualizada. Ya puede ingresar."}
