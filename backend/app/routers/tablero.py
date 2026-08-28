"""Tablero institucional: semáforo distrital, indicadores e historial — HU-13/HU-15 / RF-10.

Cada quien ve su jurisdicción. La ATM y Salud administran un distrito y solo
ese: ofrecerles los doce de la provincia era una ventana a datos ajenos, y
además abría el tablero en el primero por orden alfabético —vacío— en vez de
en el suyo. La DESA, la DRVCS y la administración sí alcanzan toda la región.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import usuario_actual
from ..enums import EstadoAlerta, NivelRiesgo
from ..models import Alerta, Comunidad, Medicion, Reservorio, Ubigeo, Usuario
from ..rules.escalamiento import ambito_de
from ..schemas import (
    ComunidadPriorizada, DistritoTablero, HistorialPunto, PriorizacionRegional,
    SemaforoComunidad, TableroResumen, UbigeoOut,
)
from ..timeutils import aware_utc

router = APIRouter(prefix="/tablero", tags=["tablero"])


def _es_regional(usuario: Usuario) -> bool:
    """Quien no está atado a un distrito alcanza toda la región."""
    return ambito_de(usuario.rol) == "regional" or usuario.ubigeo_id is None


def _exige_jurisdiccion(usuario: Usuario, ubigeo_id: int) -> None:
    if _es_regional(usuario):
        return
    if usuario.ubigeo_id != ubigeo_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Ese distrito no corresponde a su jurisdicción.",
        )


@router.get("/distritos", response_model=list[DistritoTablero])
def distritos(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Los distritos que quien consulta puede abrir.

    Ordenados por comunidades registradas: el tablero debe abrir donde hay algo
    que ver, no en el primero del abecedario.
    """
    conteo = (
        db.query(Comunidad.ubigeo_id, func.count().label("n"))
        .group_by(Comunidad.ubigeo_id).subquery()
    )
    q = (db.query(Ubigeo, func.coalesce(conteo.c.n, 0).label("comunidades"))
           .outerjoin(conteo, conteo.c.ubigeo_id == Ubigeo.ubigeo_id))
    if not _es_regional(usuario):
        q = q.filter(Ubigeo.ubigeo_id == usuario.ubigeo_id)

    return [
        DistritoTablero(**UbigeoOut.model_validate(u).model_dump(), comunidades=n)
        for u, n in q.order_by(func.coalesce(conteo.c.n, 0).desc(), Ubigeo.distrito)
    ]


# ─── Priorización regional ──────────────────────────────────────
# Cuánto pesa cada factor al ordenar la cola de atención. El agua no segura
# manda; el silencio pesa casi igual porque un reservorio que dejó de reportar
# suele ser uno sin operador o con la infraestructura fuera de servicio, y eso
# no aparece en ningún semáforo.
PESO_NIVEL = {NivelRiesgo.ROJO: 60, NivelRiesgo.AMARILLO: 30, NivelRiesgo.VERDE: 0}
PESO_SILENCIO = 40
PESO_SIN_MEDIR = 25          # nunca midió: ni siquiera se sabe qué agua entrega


def _criticidad(c: SemaforoComunidad) -> int:
    """Cuánto reclama atención una comunidad, de 0 a 100 y algo más.

    Se suma la población servida en escala reducida para que, entre dos casos
    igual de graves, primero vaya el que afecta a más gente.
    """
    puntos = PESO_NIVEL.get(c.nivel, PESO_SIN_MEDIR)
    if c.silencio:
        puntos += PESO_SILENCIO
    puntos += min(20, (c.poblacion_servida or 0) // 50)
    return puntos


@router.get("/priorizacion", response_model=PriorizacionRegional)
def priorizacion(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Todas las comunidades de la jurisdicción, ordenadas por atención.

    Es la vista de quien decide entre distritos, no dentro de uno: compara la
    región completa de una sola vez.
    """
    q = db.query(Ubigeo)
    if not _es_regional(usuario):
        q = q.filter(Ubigeo.ubigeo_id == usuario.ubigeo_id)

    filas: list[ComunidadPriorizada] = []
    sistemas = seguras = en_silencio = expuesta = 0
    con_datos = 0

    for ubigeo in q.order_by(Ubigeo.distrito):
        resumen = resumen_distrito(ubigeo.ubigeo_id, db, usuario)
        if resumen.comunidades:
            con_datos += 1
        sistemas += resumen.sistemas_monitoreados
        seguras += round(resumen.sistemas_monitoreados * resumen.porcentaje_agua_segura / 100)
        en_silencio += resumen.reservorios_en_silencio
        expuesta += resumen.poblacion_expuesta
        for c in resumen.comunidades:
            filas.append(ComunidadPriorizada(
                **c.model_dump(), distrito=ubigeo.distrito, criticidad=_criticidad(c)))

    filas.sort(key=lambda c: (-c.criticidad, -(c.poblacion_servida or 0), c.comunidad))
    return PriorizacionRegional(
        distritos=con_datos,
        sistemas_monitoreados=sistemas,
        porcentaje_agua_segura=round(100.0 * seguras / sistemas, 1) if sistemas else 0.0,
        poblacion_expuesta=expuesta,
        reservorios_en_silencio=en_silencio,
        comunidades=filas,
    )


@router.get("/{ubigeo_id}", response_model=TableroResumen)
def resumen_distrito(ubigeo_id: int, db: Session = Depends(get_db),
                     usuario: Usuario = Depends(usuario_actual)):
    ubigeo = db.get(Ubigeo, ubigeo_id)
    if not ubigeo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Distrito no encontrado")
    _exige_jurisdiccion(usuario, ubigeo_id)

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
                poblacion_servida=c.poblacion_servida,
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

    # Personas expuestas: las de las comunidades cuyo peor reservorio está en rojo.
    expuesta = sum(x.poblacion_servida or 0
                   for x in semaforo if x.nivel == NivelRiesgo.ROJO)

    pct = round(100.0 * seguras / total_reservorios, 1) if total_reservorios else 0.0
    return TableroResumen(
        distrito=ubigeo.distrito,
        sistemas_monitoreados=total_reservorios,
        porcentaje_agua_segura=pct,
        alertas_activas=alertas_activas or 0,
        reservorios_en_silencio=en_silencio,
        poblacion_expuesta=expuesta,
        comunidades=semaforo,
    )


@router.get("/reservorio/{reservorio_id}/historial", response_model=list[HistorialPunto])
def historial_reservorio(reservorio_id: int, limite: int = 30,
                         db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    # El historial es de un reservorio, y un reservorio pertenece a un distrito.
    reservorio = db.get(Reservorio, reservorio_id)
    if not reservorio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservorio no encontrado")
    comunidad = db.get(Comunidad, reservorio.comunidad_id)
    if comunidad:
        _exige_jurisdiccion(usuario, comunidad.ubigeo_id)

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
