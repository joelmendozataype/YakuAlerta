"""Resultados de laboratorio de la DESA — HU-18 / RF-15.

Un resultado NO CONFORME fuerza el nivel ROJO del reservorio hasta el cierre
sanitario: se genera/escala una alerta roja sobre su última medición.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import requiere_roles
from ..enums import DictamenLab, EstadoAlerta, NivelRiesgo, RolUsuario
from ..models import Alerta, Medicion, Reservorio, ResultadoLaboratorio, Usuario
from ..schemas import ResultadoLabIn, ResultadoLabOut
from ..services.procesamiento import _notificar

router = APIRouter(prefix="/laboratorio", tags=["laboratorio"])


@router.post("", response_model=ResultadoLabOut, status_code=status.HTTP_201_CREATED)
def registrar_resultado(
    datos: ResultadoLabIn, db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_roles(RolUsuario.DESA, RolUsuario.ADMIN)),
):
    reservorio = db.get(Reservorio, datos.reservorio_id)
    if not reservorio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservorio no encontrado")

    resultado = ResultadoLaboratorio(
        reservorio_id=datos.reservorio_id, usuario_id=usuario.usuario_id,
        parametro=datos.parametro, valor=datos.valor, unidad=datos.unidad,
        dictamen=datos.dictamen, fecha_muestreo=datos.fecha_muestreo,
        laboratorio=datos.laboratorio,
    )
    db.add(resultado)

    # NO CONFORME → forzar rojo sobre la última medición del reservorio
    if datos.dictamen == DictamenLab.NO_CONFORME:
        ultima = (db.query(Medicion).filter_by(reservorio_id=datos.reservorio_id)
                  .order_by(Medicion.fecha_hora.desc()).first())
        if ultima:
            ultima.nivel_riesgo = NivelRiesgo.ROJO
            alerta = db.query(Alerta).filter_by(medicion_id=ultima.medicion_id).first()
            if alerta:
                alerta.nivel = NivelRiesgo.ROJO
                if alerta.estado == EstadoAlerta.CERRADA:
                    alerta.estado = EstadoAlerta.ACTIVA
                    alerta.fecha_cierre = None
            else:
                alerta = Alerta(medicion_id=ultima.medicion_id, nivel=NivelRiesgo.ROJO,
                                estado=EstadoAlerta.ACTIVA)
                db.add(alerta)
                db.flush()
            _notificar(db, alerta, ultima, reservorio,
                       protocolo="Resultado de laboratorio NO CONFORME. "
                                 "Mantener el reservorio en ROJO hasta el cierre sanitario de la DESA.")

    db.commit()
    db.refresh(resultado)
    return ResultadoLabOut.model_validate(resultado)


@router.get("/reservorio/{reservorio_id}", response_model=list[ResultadoLabOut])
def listar_resultados(reservorio_id: int, db: Session = Depends(get_db),
                      usuario: Usuario = Depends(requiere_roles(
                          RolUsuario.DESA, RolUsuario.ATM, RolUsuario.ADMIN))):
    filas = (db.query(ResultadoLaboratorio).filter_by(reservorio_id=reservorio_id)
             .order_by(ResultadoLaboratorio.fecha_muestreo.desc()).all())
    return [ResultadoLabOut.model_validate(f) for f in filas]
