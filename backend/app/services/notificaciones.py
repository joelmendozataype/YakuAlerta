"""Envío de notificaciones por SMS / WhatsApp (Twilio) con modo simulado — RF-06.

En la demo (``SMS_MODO=simulado`` o sin credenciales) los mensajes NO salen
realmente: se registran en la tabla ``notificacion`` y en consola. Basta con
poner credenciales de Twilio en el .env para activar el envío real.
"""
from __future__ import annotations

import logging

from ..config import settings
from ..enums import CanalNotif, EstadoNotif

log = logging.getLogger("yakualerta.notif")


def _modo_real() -> bool:
    return (
        settings.sms_modo.lower() == "real"
        and bool(settings.twilio_account_sid)
        and bool(settings.twilio_auth_token)
    )


def enviar(canal: CanalNotif, destino: str, mensaje: str) -> EstadoNotif:
    """Envía un mensaje por el canal indicado. Devuelve el estado de entrega."""
    if not _modo_real():
        log.info("📤 [SIMULADO %s → %s]\n%s", canal.value, destino, mensaje)
        return EstadoNotif.ENVIADO

    try:  # pragma: no cover - depende de red/credenciales
        from twilio.rest import Client  # import perezoso

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        if canal == CanalNotif.WHATSAPP:
            client.messages.create(
                from_=f"whatsapp:{settings.whatsapp_from}",
                to=f"whatsapp:{destino}", body=mensaje,
            )
        else:
            client.messages.create(from_=settings.twilio_from, to=destino, body=mensaje)
        return EstadoNotif.ENTREGADO
    except Exception as exc:  # pragma: no cover
        log.error("Fallo enviando %s a %s: %s", canal.value, destino, exc)
        return EstadoNotif.FALLIDO


def componer_mensaje_alerta(
    nivel: str, comunidad: str, reservorio: str,
    cloro: float | None, turbidez: float | None,
    protocolo: str | None, medicion_id: int,
) -> str:
    """Texto de la alerta con protocolo incluido (apto para SMS y WhatsApp)."""
    emoji = "🔴" if nivel == "ROJO" else "🟡"
    cl = f"{cloro:.2f} mg/L" if cloro is not None else "s/d"
    tb = f"{turbidez:.1f} UNT" if turbidez is not None else "s/d"
    partes = [
        f"{emoji} YakuAlerta — AGUA {'NO SEGURA' if nivel == 'ROJO' else 'EN RIESGO'}",
        f"Comunidad: {comunidad} · Reservorio: {reservorio}",
        f"Cloro: {cl} · Turbidez: {tb}",
    ]
    if protocolo:
        partes.append("")
        partes.append(protocolo)
    partes.append(f"\nRef. medición #{medicion_id}")
    return "\n".join(partes)
