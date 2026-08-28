"""Umbrales normativos configurables — RNF-07.

Los valores que deciden si el agua es segura no están escritos en el código:
viven en ``parametro_normativo`` para que un cambio de norma se aplique sin
recompilar ni redesplegar nada.

Quién los edita
---------------
Solo el **ADMIN**. No es una decisión distrital: si cambia el D.S., cambia
para toda la región, y dejar que cada ATM moviera su propio umbral rompería la
comparabilidad entre distritos —y la defensa legal del dato—.

La ATM, la DESA y la DRVCS los consultan: necesitan saber con qué regla se
clasificó una medición que están por firmar.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import requiere_roles
from ..enums import RolUsuario
from ..models import Auditoria, ParametroNormativo, Usuario
from ..schemas import ParametroOut, ParametroPatch

router = APIRouter(prefix="/parametros", tags=["parámetros normativos"])

_consulta = requiere_roles(RolUsuario.ATM, RolUsuario.DESA,
                           RolUsuario.DRVCS, RolUsuario.ADMIN)
_edita = requiere_roles(RolUsuario.ADMIN)


@router.get("", response_model=list[ParametroOut])
def listar(db: Session = Depends(get_db), usuario: Usuario = Depends(_consulta)):
    """Los umbrales vigentes con los que se clasifica cada medición."""
    return [ParametroOut.model_validate(p)
            for p in db.query(ParametroNormativo).order_by(ParametroNormativo.parametro)]


@router.patch("/{parametro_id}", response_model=ParametroOut)
def corregir(parametro_id: int, datos: ParametroPatch,
             db: Session = Depends(get_db), usuario: Usuario = Depends(_edita)):
    """Ajusta un umbral y deja constancia de quién lo movió.

    Cambiar esto reclasifica todas las mediciones futuras, así que la auditoría
    registra el valor anterior: sin ese rastro no se podría explicar por qué
    una comunidad pasó de verde a amarillo sin que cambiara su agua.
    """
    p = db.get(ParametroNormativo, parametro_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Parámetro no encontrado")

    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No hay nada que corregir.")

    amarillo = cambios.get("umbral_amarillo", p.umbral_amarillo)
    rojo = cambios.get("umbral_rojo", p.umbral_rojo)
    _validar(p.parametro, amarillo, rojo)

    antes = (f"amarillo={p.umbral_amarillo} rojo={p.umbral_rojo} "
             f"vigente={p.vigente}")
    for campo, valor in cambios.items():
        setattr(p, campo, valor)

    db.add(Auditoria(
        usuario_id=usuario.usuario_id, accion="CAMBIA_UMBRAL",
        entidad_afectada="parametro_normativo", registro_id=str(p.parametro_id),
        detalle=f"{p.parametro}: antes {antes}",
    ))
    db.commit()
    db.refresh(p)
    return ParametroOut.model_validate(p)


def _validar(parametro: str, amarillo, rojo) -> None:
    """Un umbral incoherente dejaría de clasificar bien y nadie lo notaría."""
    for nombre, v in (("amarillo", amarillo), ("rojo", rojo)):
        if v is not None and float(v) < 0:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"El umbral {nombre} no puede ser negativo.")
    if amarillo is None or rojo is None:
        return

    a, r = float(amarillo), float(rojo)
    if parametro == "cloro_residual":
        # Cloro: falta de desinfectante. Menos cloro es peor, así que el rojo
        # queda por debajo del amarillo.
        if r > a:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "En el cloro, el umbral rojo debe ser menor que el amarillo: "
                "menos cloro es más riesgo.",
            )
    elif r < a:
        # Turbidez y afines: más valor es peor.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"En «{parametro}», el umbral rojo debe ser mayor o igual que el "
            "amarillo: más valor es más riesgo.",
        )
