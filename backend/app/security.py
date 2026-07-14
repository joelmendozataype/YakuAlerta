"""Autenticación por rol, hashing bcrypt y emisión/validación de JWT (RNF-05)."""
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from .config import settings


def hash_clave(clave: str) -> str:
    # bcrypt trunca a 72 bytes; las claves del sistema son cortas.
    return bcrypt.hashpw(clave.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verificar_clave(clave: str, clave_hash: str) -> bool:
    try:
        return bcrypt.checkpw(clave.encode("utf-8")[:72], clave_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def crear_token(usuario_id: int, rol: str, nombres: str) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "rol": rol,
        "nombres": nombres,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=settings.jwt_exp_min),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def decodificar_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    except JWTError:
        return None
