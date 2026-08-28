"""Restablecimiento de clave con código de un solo uso — HU-01 / RNF-05.

El código se envía por SMS al celular registrado del usuario, que es el canal
que funciona en zona rural (no se depende de correo electrónico).

Decisiones de seguridad:
* El código se guarda **cifrado**, igual que una contraseña.
* Vence en 10 minutos y solo admite 5 intentos.
* Un solo uso: al restablecer, el código y los pendientes quedan anulados.
* La respuesta de la solicitud es idéntica exista o no el DNI, para no permitir
  averiguar qué documentos están registrados.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..enums import CanalNotif
from ..models import RecuperacionClave, Usuario
from ..security import hash_clave, verificar_clave
from ..timeutils import aware_utc
from . import notificaciones as notif

VIGENCIA_MIN = 10
MAX_INTENTOS = 5


def _codigo_nuevo() -> str:
    """Seis dígitos aleatorios, cómodos de dictar y de teclear."""
    return f"{secrets.randbelow(1_000_000):06d}"


def enmascarar(telefono: str) -> str:
    """Muestra solo los últimos dígitos: confirma el destino sin exponerlo."""
    return f"{'*' * max(0, len(telefono) - 4)}{telefono[-4:]}" if telefono else ""


def solicitar(db: Session, dni: str, ip: str | None = None) -> str | None:
    """Genera y envía el código. Devuelve el teléfono enmascarado, o None si el
    DNI no existe (el router responde igual en ambos casos)."""
    usuario = db.query(Usuario).filter(Usuario.dni == dni, Usuario.activo.is_(True)).first()
    if usuario is None:
        return None

    # Anula los códigos anteriores del usuario: solo uno vigente a la vez.
    (db.query(RecuperacionClave)
       .filter(RecuperacionClave.usuario_id == usuario.usuario_id,
               RecuperacionClave.usado.is_(False))
       .update({"usado": True}))

    codigo = _codigo_nuevo()
    db.add(RecuperacionClave(
        usuario_id=usuario.usuario_id,
        codigo_hash=hash_clave(codigo),
        expira_en=datetime.now(timezone.utc) + timedelta(minutes=VIGENCIA_MIN),
        ip_origen=ip,
    ))

    notif.enviar(
        CanalNotif.SMS, usuario.telefono,
        f"Yakuni: su código para restablecer la clave es {codigo}. "
        f"Vence en {VIGENCIA_MIN} minutos. No lo comparta con nadie.",
    )
    return enmascarar(usuario.telefono)


class ErrorRecuperacion(Exception):
    """Motivo por el que no se pudo restablecer la clave."""


def confirmar(db: Session, dni: str, codigo: str, clave_nueva: str) -> Usuario:
    """Valida el código y establece la clave nueva."""
    usuario = db.query(Usuario).filter(Usuario.dni == dni, Usuario.activo.is_(True)).first()
    if usuario is None:
        raise ErrorRecuperacion("Código inválido o vencido")

    registro = (
        db.query(RecuperacionClave)
        .filter(RecuperacionClave.usuario_id == usuario.usuario_id,
                RecuperacionClave.usado.is_(False))
        .order_by(RecuperacionClave.recuperacion_id.desc())
        .first()
    )
    if registro is None:
        raise ErrorRecuperacion("Solicite un código nuevo")
    if aware_utc(registro.expira_en) < datetime.now(timezone.utc):
        registro.usado = True
        raise ErrorRecuperacion("El código venció; solicite uno nuevo")
    if registro.intentos >= MAX_INTENTOS:
        registro.usado = True
        raise ErrorRecuperacion("Demasiados intentos; solicite un código nuevo")

    if not verificar_clave(codigo, registro.codigo_hash):
        registro.intentos += 1
        restantes = MAX_INTENTOS - registro.intentos
        raise ErrorRecuperacion(
            f"Código incorrecto. Le quedan {max(0, restantes)} intento(s)")

    usuario.clave_hash = hash_clave(clave_nueva)
    registro.usado = True
    return usuario
