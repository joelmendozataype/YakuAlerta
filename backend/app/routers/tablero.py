"""Tablero institucional: semáforo distrital, indicadores e historial — HU-13/HU-15 / RF-10."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import usuario_actual
from ..enums import EstadoAlerta, NivelRiesgo
from ..models import Alerta, Comunidad, Medicion, Reservorio, Ubigeo, Usuario
from ..schemas import HistorialPunto, SemaforoComunidad, TableroResumen, UbigeoOut
from ..timeutils import aware_utc

router = APIRouter(prefix="/tablero", tags=["tablero"])


@router.get("/distritos", response_model=list[UbigeoOut])
def distritos(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return [UbigeoOut.model_validate(u) for u in db.query(Ubigeo).order_by(Ubigeo.distrito)]


@router.get("/{ubigeo_id}", response_model=TableroResumen)
def resumen_distrito(ubigeo_id: int, db: Session = Depends(get_db),
                     usuario: Usuario = Depends(usuario_actual)):
    ubigeo = db.get(Ubigeo, ubigeo_id)
    if not ubigeo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Distrito no encontrado")

    ahora = datetime.now(timezone.utc)
    comunidades = db.query(Comunidad).filter(Comunidad.ubigeo_id == ubigeo_id).order_by(Comunidad.nombre).all()

    semaforo: list[SemaforoComunidad] = []
    seguras = total_reservorios = en_silencio = 0

    for c in comunidades:
        reservorios = db.query(Reservorio).filter_by(comunidad_id=c.comunidad_id).all()
        # Se muestra el peor reservorio de la comunidad (regla de peor caso a nivel comunidad)
        peor: SemaforoComunidad | None = None
        peor_sev = -1
        sev = {None: 0, NivelRiesgo.VERDE: 1, NivelRiesgo.AMARILLO: 2, NivelRiesgo.ROJO: 3}
        for r in reservorios:
            total_reservorios += 1
            ultima = (db.query(Medicion).filter_by(reservorio_id=r.reservorio_id)
                      .order_by(Medicion.fecha_hora.desc()).first())
            dias = (ahora - aware_utc(ultima.fecha_hora)).days if ultima else None
            silencio = dias is None or dias > r.umbral_silencio_dias
            if silencio:
                en_silencio += 1
            nivel = ultima.nivel_riesgo if ultima else None
            if nivel == NivelRiesgo.VERDE:
                seguras += 1
            item = SemaforoComunidad(
                comunidad_id=c.comunidad_id, comunidad=c.nombre,
                latitud=float(c.latitud) if c.latitud is not None else None,
                longitud=float(c.longitud) if c.longitud is not None else None,
                reservorio_id=r.reservorio_id, reservorio_codigo=r.codigo,
                nivel=nivel, ultima_medicion=ultima.fecha_hora if ultima else None,
                via_recepcion=ultima.estado_sync if ultima else None,
                silencio=silencio, dias_sin_medir=dias,
            )
            if sev[nivel] > peor_sev:
                peor_sev, peor = sev[nivel], item
        if peor:
            semaforo.append(peor)

    alertas_activas = (
        db.query(func.count(Alerta.alerta_id))
        .join(Medicion, Alerta.medicion_id == Medicion.medicion_id)
        .join(Reservorio, Medicion.reservorio_id == Reservorio.reservorio_id)
        .join(Comunidad, Reservorio.comunidad_id == Comunidad.comunidad_id)
        .filter(Comunidad.ubigeo_id == ubigeo_id, Alerta.estado == EstadoAlerta.ACTIVA)
        .scalar()
    )

    pct = round(100.0 * seguras / total_reservorios, 1) if total_reservorios else 0.0
    return TableroResumen(
        distrito=ubigeo.distrito,
        sistemas_monitoreados=total_reservorios,
        porcentaje_agua_segura=pct,
        alertas_activas=alertas_activas or 0,
        reservorios_en_silencio=en_silencio,
        comunidades=semaforo,
    )


@router.get("/reservorio/{reservorio_id}/historial", response_model=list[HistorialPunto])
def historial_reservorio(reservorio_id: int, limite: int = 30,
                         db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    mediciones = (
        db.query(Medicion).filter_by(reservorio_id=reservorio_id)
        .order_by(Medicion.fecha_hora.desc()).limit(min(limite, 200)).all()
    )
    return [
        HistorialPunto(
            fecha_hora=m.fecha_hora,
            cloro_mg_l=float(m.cloro_mg_l) if m.cloro_mg_l is not None else None,
            turbidez_unt=float(m.turbidez_unt) if m.turbidez_unt is not None else None,
            nivel=m.nivel_riesgo,
        )
        for m in reversed(mediciones)
    ]
