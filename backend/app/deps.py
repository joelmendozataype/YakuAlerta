"""Dependencias de autenticación y autorización por rol (mínimo privilegio, RNF-05)."""
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .enums import EstadoQR, RolUsuario
from .models import SesionQR, Usuario
from .security import decodificar_token

_bearer = HTTPBearer(auto_error=False)


def usuario_actual(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")
    payload = decodificar_token(cred.credentials)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido o expirado")
    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None or not usuario.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inactivo")

    # Sesión de un dispositivo vinculado por QR: se revoca desde la app y el
    # token deja de valer al instante, sin esperar a su expiración.
    sid = payload.get("sid")
    if sid is not None:
        sesion = db.get(SesionQR, int(sid))
        if sesion is None or sesion.estado != EstadoQR.CONSUMIDA:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "La sesión de este dispositivo fue cerrada desde la aplicación",
            )
    return usuario


def sesion_actual_id(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int | None:
    """Identificador de la sesión vinculada que emitió el token, si lo hay.

    Permite señalar «este dispositivo» en el listado de sesiones activas.
    """
    if cred is None:
        return None
    payload = decodificar_token(cred.credentials)
    sid = payload.get("sid") if payload else None
    return int(sid) if sid is not None else None


def requiere_roles(*roles: RolUsuario) -> Callable[..., Usuario]:
    """Fábrica de dependencia que exige uno de los roles indicados."""
    permitidos = {r.value for r in roles}

    def _dep(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol.value not in permitidos:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Requiere rol {sorted(permitidos)}; su rol es {usuario.rol.value}",
            )
        return usuario

    return _dep
