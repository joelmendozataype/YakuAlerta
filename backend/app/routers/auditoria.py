"""Rastro de auditoría — Ley N.° 29733 y trazabilidad del Desafío 2.

El sistema ya venía registrando cada hecho sensible, pero nadie podía leerlo:
la auditoría era de solo escritura. Un rastro que no se puede consultar no
sirve para rendir cuentas, que es justamente para lo que existe.

Quién lo lee
------------
El **ADMIN**, sobre toda la región: la supervisión es su función propia. La
**ATM** solo sobre las cuentas de su distrito, para que el rastro no se
convierta en una ventana a la actividad de otras jurisdicciones.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import requiere_roles
from ..enums import RolUsuario
from ..models import Auditoria, Usuario
from ..schemas import AuditoriaOut

router = APIRouter(prefix="/auditoria", tags=["auditoría"])

_supervisa = requiere_roles(RolUsuario.ATM, RolUsuario.ADMIN)

# Cada acción, dicha en palabras. Un rastro que solo muestra códigos en
# mayúsculas obliga a quien rinde cuentas a traducir mentalmente.
TITULOS: dict[str, str] = {
    "LOGIN": "Inició sesión",
    "LOGIN_QR": "Inició sesión con código QR",
    "QR_APROBADO": "Aprobó vincular un dispositivo",
    "QR_SESION_CERRADA": "Cerró la sesión de un dispositivo",
    "QR_SESIONES_CERRADAS": "Cerró todas sus sesiones vinculadas",
    "RECUPERACION_SOLICITADA": "Solicitó recuperar su clave",
    "CLAVE_RESTABLECIDA": "Restableció su clave con el código recibido",
    "RESET_CLAVE": "Generó una clave provisional para otra cuenta",
    "EDITA_USUARIO": "Corrigió los datos de una cuenta",
    "BAJA_USUARIO": "Dio de baja una cuenta",
    "CAMBIA_UMBRAL": "Modificó un umbral normativo",
    "CIERRE_ALERTA": "Cerró una alerta",
}

# Hechos que conviene poder aislar de un vistazo: son los que cambian el
# comportamiento del sistema o el acceso de alguien.
ACCIONES_SENSIBLES = (
    "CAMBIA_UMBRAL", "CIERRE_ALERTA", "BAJA_USUARIO", "RESET_CLAVE", "EDITA_USUARIO",
)


@router.get("", response_model=list[AuditoriaOut])
def rastro(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(_supervisa),
    accion: str | None = Query(None, description="Filtra por tipo de acción"),
    usuario_id: int | None = Query(None, description="Rastro de una cuenta"),
    entidad: str | None = Query(None, description="alerta, usuario, parametro_normativo…"),
    registro_id: str | None = Query(None, description="Rastro de un registro concreto"),
    solo_sensibles: bool = Query(False, description="Oculta los inicios de sesión"),
    limite: int = Query(100, ge=1, le=500),
):
    """El rastro más reciente primero, acotado al ámbito de quien consulta."""
    q = db.query(Auditoria, Usuario).outerjoin(Usuario, Auditoria.usuario_id == Usuario.usuario_id)

    if usuario.rol != RolUsuario.ADMIN:
        # La ATM ve lo suyo y lo de las cuentas de su distrito, nada más.
        q = q.filter(Usuario.ubigeo_id == usuario.ubigeo_id)
    if accion:
        q = q.filter(Auditoria.accion == accion)
    if solo_sensibles:
        q = q.filter(Auditoria.accion.in_(ACCIONES_SENSIBLES))
    if usuario_id is not None:
        q = q.filter(Auditoria.usuario_id == usuario_id)
    if entidad:
        q = q.filter(Auditoria.entidad_afectada == entidad)
    if registro_id:
        q = q.filter(Auditoria.registro_id == str(registro_id))

    filas = q.order_by(Auditoria.auditoria_id.desc()).limit(limite).all()
    return [
        AuditoriaOut(
            auditoria_id=a.auditoria_id, fecha_hora=a.fecha_hora, accion=a.accion,
            titulo=TITULOS.get(a.accion, a.accion.replace("_", " ").capitalize()),
            usuario_id=a.usuario_id, usuario=u.nombres if u else None,
            rol=u.rol if u else None,
            entidad_afectada=a.entidad_afectada, registro_id=a.registro_id,
            detalle=a.detalle, ip_origen=a.ip_origen,
        )
        for a, u in filas
    ]


@router.get("/acciones", response_model=dict[str, str])
def acciones(usuario: Usuario = Depends(_supervisa)):
    """Catálogo de acciones auditables, para poblar los filtros."""
    return dict(TITULOS)
