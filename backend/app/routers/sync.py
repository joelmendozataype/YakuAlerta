"""Sincronización por lotes y canal SMS estructurado — HU-11/HU-12 / RF-08, RF-09."""
from __future__ import annotations

import uuid as uuidlib
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import usuario_actual
from ..enums import EstadoSync, MetodoLectura, NivelRiesgo
from ..models import Alerta, Medicion, Reservorio, Usuario
from ..schemas import MedicionIn, MedicionOut, SyncLoteIn, SyncResultado
from ..services.registro import registrar_medicion
from .mediciones import _to_out, validar_rangos

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("", response_model=SyncResultado)
def sincronizar(lote: SyncLoteIn, db: Session = Depends(get_db),
                usuario: Usuario = Depends(usuario_actual)):
    """Recibe un lote de mediciones creadas offline; deduplica y clasifica."""
    insertadas = duplicadas = alertas = 0
    salida: list[MedicionOut] = []

    for datos in lote.mediciones:
        validar_rangos(datos)
        medicion, dup = registrar_medicion(db, datos, usuario.usuario_id)
        if dup:
            duplicadas += 1
        else:
            insertadas += 1
            if medicion.nivel_riesgo in (NivelRiesgo.AMARILLO, NivelRiesgo.ROJO):
                alertas += 1
        db.flush()
        salida.append(_to_out(medicion))

    db.commit()
    return SyncResultado(
        recibidas=len(lote.mediciones), insertadas=insertadas,
        duplicadas=duplicadas, alertas_generadas=alertas, resultados=salida,
    )


# ─── Canal SMS estructurado (HU-11) ──────────────────────────────
#  Formato compacto interpretable por la pasarela, p. ej.:
#     YA;RES-001;CL:0.10;TB:8;OBS:agua turbia;UUID:xxxx
#  Campos: RES-<codigo reservorio>, CL cloro mg/L, TB turbidez UNT, OBS, UUID.

def parse_sms(texto: str) -> dict:
    """Interpreta un SMS estructurado y devuelve un dict de campos."""
    texto = texto.strip()
    partes = [p.strip() for p in texto.split(";") if p.strip()]
    if not partes or partes[0].upper() != "YA":
        raise ValueError("SMS no válido: debe iniciar con 'YA;'")
    datos: dict = {}
    datos["reservorio_codigo"] = partes[1] if len(partes) > 1 else None
    for campo in partes[2:]:
        if ":" not in campo:
            continue
        clave, valor = campo.split(":", 1)
        clave = clave.strip().upper()
        valor = valor.strip()
        if clave == "CL":
            datos["cloro_mg_l"] = float(valor)
        elif clave == "TB":
            datos["turbidez_unt"] = float(valor)
        elif clave == "OBS":
            datos["observaciones"] = valor
        elif clave == "UUID":
            datos["uuid_registro"] = valor
    return datos


@router.post("/sms", response_model=MedicionOut)
def recibir_sms(
    texto: str = Body(..., embed=True, examples=["YA;RES-001;CL:0.10;TB:8;OBS:agua turbia"]),
    db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual),
):
    """Endpoint que emula la recepción de la pasarela SMS (webhook de Twilio)."""
    try:
        campos = parse_sms(texto)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    codigo = campos.get("reservorio_codigo")
    reservorio = db.query(Reservorio).filter(Reservorio.codigo == codigo).first()
    if not reservorio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Reservorio '{codigo}' no encontrado")

    datos = MedicionIn(
        uuid_registro=campos.get("uuid_registro") or str(uuidlib.uuid4()),
        reservorio_id=reservorio.reservorio_id,
        fecha_hora=datetime.now(timezone.utc),
        cloro_mg_l=campos.get("cloro_mg_l"),
        turbidez_unt=campos.get("turbidez_unt"),
        metodo_cloro=MetodoLectura.MANUAL,
        observaciones=campos.get("observaciones"),
        origen=EstadoSync.ENVIADO_SMS,  # llegó por SMS: modo degradado
    )
    validar_rangos(datos)
    medicion, _ = registrar_medicion(db, datos, usuario.usuario_id)
    db.commit()
    db.refresh(medicion)
    return _to_out(medicion)
