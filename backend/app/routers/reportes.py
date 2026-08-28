"""Reportes de vigilancia y verificación de silencio — HU-17/HU-15 / RF-13, RF-11."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import requiere_roles
from ..enums import RolUsuario
from ..models import Reporte, Usuario
from ..services import reportes as svc
from ..services.silencio import reservorios_en_silencio, verificar_silencio

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.get("/vigilancia")
def reporte_vigilancia(
    ubigeo_id: int,
    periodo: str = Query(..., pattern=r"^\d{4}-\d{2}$", examples=["2026-08"]),
    formato: str = Query("pdf", pattern="^(pdf|xlsx)$"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_roles(
        RolUsuario.ATM, RolUsuario.DESA, RolUsuario.DRVCS, RolUsuario.ADMIN)),
):
    """Genera y descarga el reporte consolidado en PDF o Excel."""
    if formato == "xlsx":
        contenido = svc.generar_excel(db, ubigeo_id, periodo)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    else:
        contenido = svc.generar_pdf(db, ubigeo_id, periodo)
        media = "application/pdf"
        ext = "pdf"

    db.add(Reporte(ubigeo_id=ubigeo_id, usuario_id=usuario.usuario_id,
                   periodo=periodo, formato=ext.upper()))
    db.commit()

    nombre = f"vigilancia_{ubigeo_id}_{periodo}.{ext}"
    return Response(content=contenido, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@router.get("/silencio")
def silencio_actual(db: Session = Depends(get_db),
                    usuario: Usuario = Depends(requiere_roles(
                        RolUsuario.ATM, RolUsuario.DRVCS, RolUsuario.ADMIN))):
    """Lista los reservorios en silencio de datos (sin notificar)."""
    return [
        {"reservorio_id": r.reservorio_id, "codigo": r.codigo,
         "dias_sin_medir": dias, "umbral": r.umbral_silencio_dias}
        for r, dias in reservorios_en_silencio(db)
    ]


@router.post("/silencio/verificar")
def ejecutar_verificacion_silencio(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_roles(RolUsuario.ATM, RolUsuario.ADMIN)),
):
    """Dispara manualmente la verificación diaria de silencio (además del cron)."""
    n = verificar_silencio(db)
    db.commit()
    return {"reservorios_notificados": n}
