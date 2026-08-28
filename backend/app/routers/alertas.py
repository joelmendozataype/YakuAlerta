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
from ..enums import DictamenLab, EstadoAlerta, NivelRiesgo, RolUsuario
from ..models import (
    Alerta, Auditoria, Comunidad, EvidenciaFoto, Medicion, RecomendacionDosis,
    Reservorio, ResultadoLaboratorio, Usuario,
)
from ..schemas import AlertaOut, CierreAlertaIn, NotificacionOut, SustentoCierre
from ..timeutils import aware_utc

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

    # Cada quien ve las alertas de su jurisdicción: la comunidad para los
    # perfiles comunales, el distrito para la ATM y salud. Sin ámbito
    # declarado (DESA, DRVCS, administrador) el alcance es regional.
    if usuario.comunidad_id is not None:
        q = (q.join(Medicion, Alerta.medicion_id == Medicion.medicion_id)
              .join(Reservorio, Medicion.reservorio_id == Reservorio.reservorio_id)
              .filter(Reservorio.comunidad_id == usuario.comunidad_id))
    elif usuario.ubigeo_id is not None:
        q = (q.join(Medicion, Alerta.medicion_id == Medicion.medicion_id)
              .join(Reservorio, Medicion.reservorio_id == Reservorio.reservorio_id)
              .join(Comunidad, Reservorio.comunidad_id == Comunidad.comunidad_id)
              .filter(Comunidad.ubigeo_id == usuario.ubigeo_id))

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
    # Una alerta roja se cierra con un hecho, no con una declaración: o una
    # remedición en verde del mismo reservorio, o un dictamen CONFORME de
    # laboratorio posterior a la alerta. El servidor los busca; quien cierra
    # no puede afirmar que existen.
    sustento = _sustento_del_cierre(db, a, datos)

    a.estado = EstadoAlerta.CERRADA
    a.fecha_cierre = datetime.now(timezone.utc)
    a.medicion_cierre_id = datos.medicion_cierre_id
    a.resultado_cierre = datos.resultado_cierre
    a.usuario_cierre_id = usuario.usuario_id
    db.add(Auditoria(
        usuario_id=usuario.usuario_id, accion="CIERRE_ALERTA",
        entidad_afectada="alerta", registro_id=str(a.alerta_id),
        detalle=f"{sustento.tipo}: {sustento.detalle}",
    ))
    db.commit()
    db.refresh(a)
    return _to_out(db, a)


def _sustento_del_cierre(db: Session, a: Alerta, datos: CierreAlertaIn) -> SustentoCierre:
    """Verifica que exista un hecho que justifique cerrar, y devuelve cuál.

    Una alerta amarilla se cierra con la gestión de quien la atiende. Una roja
    exige evidencia registrada (CA-HU16-02), porque cerrarla significa decirle
    a la comunidad que puede volver a beber el agua.
    """
    if a.nivel != NivelRiesgo.ROJO:
        return SustentoCierre(tipo="DIRECTO", detalle="Alerta no roja: basta la gestión registrada.")

    abierta = aware_utc(a.fecha_generacion)
    reservorio_id = a.medicion.reservorio_id

    # ── Camino 1: remedición en verde ───────────────────────────
    if datos.medicion_cierre_id is not None:
        rem = db.get(Medicion, datos.medicion_cierre_id)
        if not rem:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Remedición no encontrada")
        # Debe ser del mismo reservorio: una medición verde de otra comunidad
        # no dice nada sobre esta agua.
        if rem.reservorio_id != reservorio_id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "La remedición pertenece a otro reservorio; debe ser del mismo que originó la alerta.",
            )
        if rem.nivel_riesgo != NivelRiesgo.VERDE:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"La remedición está en {rem.nivel_riesgo.value}; se requiere VERDE para cerrar.",
            )
        # Y posterior a la alerta: una medición vieja no prueba que se resolvió.
        if aware_utc(rem.fecha_hora) < abierta:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "La remedición es anterior a la alerta; no acredita que el problema se haya resuelto.",
            )
        return SustentoCierre(
            tipo="REMEDICION",
            detalle=f"Medición #{rem.medicion_id} en VERDE del {aware_utc(rem.fecha_hora):%d/%m/%Y}.",
        )

    # ── Camino 2: dictamen de laboratorio CONFORME ──────────────
    # La comparación de fechas se hace en Python, no en SQL. SQLite guarda
    # CURRENT_TIMESTAMP sin microsegundos pero enlaza el parámetro con ellos, y
    # al compararse como texto «…58» queda por debajo de «…58.000000»: un
    # dictamen emitido en el mismo segundo que la alerta se volvía invisible y
    # el caso no se podía cerrar.
    candidatos = (
        db.query(ResultadoLaboratorio)
        .filter(ResultadoLaboratorio.reservorio_id == reservorio_id,
                ResultadoLaboratorio.dictamen == DictamenLab.CONFORME)
        .order_by(ResultadoLaboratorio.resultado_id.desc()).all()
    )
    dictamen = next(
        (d for d in candidatos if aware_utc(d.created_at) >= abierta), None
    )
    if dictamen:
        return SustentoCierre(
            tipo="DICTAMEN_LAB",
            detalle=(f"Resultado #{dictamen.resultado_id} CONFORME de "
                     f"{dictamen.laboratorio or 'laboratorio'}, muestreo del "
                     f"{dictamen.fecha_muestreo:%d/%m/%Y}."),
        )

    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "No se puede cerrar una alerta ROJA sin evidencia: registre una remedición "
        "en VERDE del mismo reservorio, o un resultado de laboratorio CONFORME "
        "posterior a la alerta (CA-HU16-02).",
    )
