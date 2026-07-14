"""Bandeja de alertas y cierre con evidencia — HU-14/HU-16 / RF-12.

Regla de negocio central (CA-HU16-02): una alerta ROJA solo puede cerrarse con
una remedición en nivel VERDE **o** con un dictamen sanitario de la DESA.
No existen alarmas huérfanas.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import requiere_roles, usuario_actual
from ..enums import EstadoAlerta, NivelRiesgo, RolUsuario
from ..models import (
    Alerta, Comunidad, EvidenciaFoto, Medicion, RecomendacionDosis, Reservorio, Usuario,
)
from ..schemas import AlertaOut, CierreAlertaIn, NotificacionOut

router = APIRouter(prefix="/alertas", tags=["alertas"])


def _to_out(db: Session, a: Alerta) -> AlertaOut:
    m = db.get(Medicion, a.medicion_id)
    reservorio = db.get(Reservorio, m.reservorio_id) if m else None
    comunidad = db.get(Comunidad, reservorio.comunidad_id) if reservorio else None
    reco = db.query(RecomendacionDosis).filter_by(medicion_id=a.medicion_id).first()
    evidencia_ids = [
        e.evidencia_id
        for e in db.query(EvidenciaFoto.evidencia_id).filter_by(medicion_id=a.medicion_id)
    ]
    return AlertaOut(
        alerta_id=a.alerta_id, medicion_id=a.medicion_id, nivel=a.nivel,
        estado=a.estado, fecha_generacion=a.fecha_generacion,
        fecha_cierre=a.fecha_cierre, resultado_cierre=a.resultado_cierre,
        comunidad=comunidad.nombre if comunidad else None,
        reservorio_codigo=reservorio.codigo if reservorio else None,
        cloro_mg_l=float(m.cloro_mg_l) if m and m.cloro_mg_l is not None else None,
        turbidez_unt=float(m.turbidez_unt) if m and m.turbidez_unt is not None else None,
        protocolo=reco.protocolo if reco else None,
        evidencia_ids=evidencia_ids,
        notificaciones=[NotificacionOut.model_validate(n) for n in a.notificaciones],
    )


@router.get("", response_model=list[AlertaOut])
def listar_alertas(estado: EstadoAlerta | None = EstadoAlerta.ACTIVA,
                   db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    q = db.query(Alerta).order_by(Alerta.fecha_generacion.desc())
    if estado:
        q = q.filter(Alerta.estado == estado)
    return [_to_out(db, a) for a in q.all()]


@router.get("/{alerta_id}", response_model=AlertaOut)
def obtener_alerta(alerta_id: int, db: Session = Depends(get_db),
                   usuario: Usuario = Depends(usuario_actual)):
    a = db.get(Alerta, alerta_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alerta no encontrada")
    return _to_out(db, a)


@router.post("/{alerta_id}/cerrar", response_model=AlertaOut)
def cerrar_alerta(
    alerta_id: int, datos: CierreAlertaIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_roles(RolUsuario.ATM, RolUsuario.DESA, RolUsuario.ADMIN)),
):
    a = db.get(Alerta, alerta_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alerta no encontrada")
    if a.estado == EstadoAlerta.CERRADA:
        raise HTTPException(status.HTTP_409_CONFLICT, "La alerta ya está cerrada")

    # ── Regla de trazabilidad (CA-HU16-02) ──────────────────────
    if a.nivel == NivelRiesgo.ROJO and not datos.dictamen_desa:
        if datos.medicion_cierre_id is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "No se puede cerrar una alerta ROJA sin una remedición en VERDE "
                "o un dictamen sanitario de la DESA (CA-HU16-02).",
            )
        remedicion = db.get(Medicion, datos.medicion_cierre_id)
        if not remedicion:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Remedición no encontrada")
        if remedicion.nivel_riesgo != NivelRiesgo.VERDE:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"La remedición está en {remedicion.nivel_riesgo.value}; se requiere VERDE para cerrar.",
            )

    a.estado = EstadoAlerta.CERRADA
    a.fecha_cierre = datetime.now(timezone.utc)
    a.medicion_cierre_id = datos.medicion_cierre_id
    a.resultado_cierre = datos.resultado_cierre
    a.usuario_cierre_id = usuario.usuario_id
    db.commit()
    db.refresh(a)
    return _to_out(db, a)
