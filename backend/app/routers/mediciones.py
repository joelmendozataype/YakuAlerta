"""Registro y consulta de mediciones — HU-02 / RF-02.

Valida rangos físicos (previene errores de digitación, CA-HU02-02) y delega
la clasificación + recomendación + alerta al pipeline central.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import usuario_actual
from ..models import Medicion, Usuario
from ..schemas import MedicionIn, MedicionOut
from ..services.registro import registrar_medicion

router = APIRouter(prefix="/mediciones", tags=["mediciones"])

CLORO_MAX_FISICO = 20.0   # mg/L — por encima es error de digitación
TURBIDEZ_MAX_FISICA = 1000.0


def validar_rangos(datos: MedicionIn) -> None:
    if datos.cloro_mg_l is not None and not (0 <= datos.cloro_mg_l <= CLORO_MAX_FISICO):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Cloro {datos.cloro_mg_l} fuera de rango físico (0–{CLORO_MAX_FISICO} mg/L). Verifique la lectura.",
        )
    if datos.turbidez_unt is not None and not (0 <= datos.turbidez_unt <= TURBIDEZ_MAX_FISICA):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Turbidez {datos.turbidez_unt} fuera de rango físico. Verifique la lectura.",
        )


@router.post("", response_model=MedicionOut, status_code=status.HTTP_201_CREATED)
def crear_medicion(datos: MedicionIn, db: Session = Depends(get_db),
                   usuario: Usuario = Depends(usuario_actual)):
    validar_rangos(datos)
    medicion, duplicada = registrar_medicion(db, datos, usuario.usuario_id)
    db.commit()
    db.refresh(medicion)
    return _to_out(medicion)


@router.get("", response_model=list[MedicionOut])
def listar_mediciones(reservorio_id: int | None = None, limite: int = 100,
                      db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    q = db.query(Medicion).order_by(Medicion.fecha_hora.desc())
    if reservorio_id:
        q = q.filter(Medicion.reservorio_id == reservorio_id)
    return [_to_out(m) for m in q.limit(min(limite, 500)).all()]


@router.get("/{medicion_id}", response_model=MedicionOut)
def obtener_medicion(medicion_id: int, db: Session = Depends(get_db),
                     usuario: Usuario = Depends(usuario_actual)):
    m = db.get(Medicion, medicion_id)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Medición no encontrada")
    return _to_out(m)


def _to_out(m: Medicion) -> MedicionOut:
    out = MedicionOut.model_validate(m)
    if m.recomendacion:
        from ..schemas import RecomendacionOut
        out.recomendacion = RecomendacionOut.model_validate(m.recomendacion)
    return out
