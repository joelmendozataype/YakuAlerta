"""Subida y consulta de evidencia fotográfica — HU-08 / RF-14.

La foto se sube en una segunda fase, DESPUÉS de que la medición se sincronizó
(se referencia por su UUID) y se guarda **dentro de la base**, en la tabla
``evidencia_foto``.

Antes vivía como archivo en ``uploads/`` con la ruta anotada en la fila, y eso
partía la evidencia en dos: respaldar la base sin la carpeta dejaba filas
apuntando a imágenes inexistentes, y un despliegue con disco efímero las
borraba en cada actualización. Las fotos anteriores siguen leyéndose de disco.

Quién puede qué
---------------
Adjuntar: solo quien firmó la medición. La evidencia respalda lo que esa
persona vio en el reservorio; si otro pudiera adjuntarla, la foto dejaría de
probar nada.

Ver: quien tiene que decidir con ella —la ATM, Salud, la DESA, la DRVCS y la
administración— además del propio autor. Son fotos georreferenciadas de
comunidades y no se exponen más allá de eso (Ley N.° 29733).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException, UploadFile, status,
)
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import usuario_actual
from ..enums import RolUsuario
from ..models import EvidenciaFoto, Medicion, Usuario

router = APIRouter(tags=["evidencias"])

# Solo para leer las fotos guardadas antes de este cambio. Anclada al paquete
# y no al directorio de arranque, porque una ruta relativa las volvía
# inencontrables según desde dónde se levantara el servidor.
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"

# El tipo se valida al recibir; ya no hace falta la extensión del archivo.
TIPOS_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB (las fotos ya vienen comprimidas del móvil)


@router.post("/mediciones/{uuid}/evidencia", status_code=status.HTTP_201_CREATED)
async def subir_evidencia(
    uuid: str,
    archivo: UploadFile = File(...),
    latitud: float | None = Form(None),
    longitud: float | None = Form(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    medicion = db.query(Medicion).filter(Medicion.uuid_registro == uuid).first()
    if not medicion:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Medición no encontrada; sincroniza la medición antes de subir la foto.",
        )
    if medicion.usuario_id != usuario.usuario_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "La evidencia la adjunta quien tomó la medición: es lo que respalda.",
        )

    if (archivo.content_type or "") not in TIPOS_PERMITIDOS:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Tipo no permitido: {archivo.content_type}. Use JPEG/PNG/WebP.",
        )

    contenido = await archivo.read()
    if len(contenido) > MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"La imagen supera {MAX_BYTES // (1024 * 1024)} MB.",
        )

    evidencia = EvidenciaFoto(
        medicion_id=medicion.medicion_id,
        contenido=contenido,
        tipo_mime=archivo.content_type,
        tamano_bytes=len(contenido),
        latitud=latitud,
        longitud=longitud,
    )
    db.add(evidencia)
    db.commit()
    db.refresh(evidencia)
    return {
        "evidencia_id": evidencia.evidencia_id,
        "medicion_id": medicion.medicion_id,
        "url": f"/evidencias/{evidencia.evidencia_id}",
    }


# Roles que deciden a partir de la evidencia. El autor de la medición también
# ve la suya, aunque no esté en esta lista.
ROLES_QUE_REVISAN = (
    RolUsuario.ATM, RolUsuario.SALUD, RolUsuario.DESA,
    RolUsuario.DRVCS, RolUsuario.ADMIN,
)


def _exige_poder_verla(db: Session, usuario: Usuario, medicion_id: int) -> None:
    if usuario.rol in ROLES_QUE_REVISAN:
        return
    medicion = db.get(Medicion, medicion_id)
    if medicion is None or medicion.usuario_id != usuario.usuario_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Esta evidencia no corresponde a su ámbito.",
        )


@router.get("/evidencias/{evidencia_id}")
def ver_evidencia(
    evidencia_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    evidencia = db.get(EvidenciaFoto, evidencia_id)
    if not evidencia:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidencia no encontrada")
    _exige_poder_verla(db, usuario, evidencia.medicion_id)

    if evidencia.contenido is not None:
        return Response(evidencia.contenido,
                        media_type=evidencia.tipo_mime or "image/jpeg")

    # Guardada antes del cambio: sigue en disco.
    if evidencia.ruta_archivo:
        ruta = Path(evidencia.ruta_archivo)
        if ruta.exists():
            return FileResponse(ruta)
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no disponible")


@router.get("/mediciones/{medicion_id}/evidencias")
def listar_evidencias(
    medicion_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    _exige_poder_verla(db, usuario, medicion_id)
    filas = db.query(EvidenciaFoto).filter_by(medicion_id=medicion_id).all()
    return [
        {
            "evidencia_id": e.evidencia_id,
            "url": f"/evidencias/{e.evidencia_id}",
            "tamano_bytes": e.tamano_bytes,
            "latitud": float(e.latitud) if e.latitud is not None else None,
            "longitud": float(e.longitud) if e.longitud is not None else None,
            "fecha_hora": e.fecha_hora,
        }
        for e in filas
    ]
