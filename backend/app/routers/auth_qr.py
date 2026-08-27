"""Inicio de sesión en el tablero web mediante código QR (patrón WhatsApp/Discord Web).

Flujo de vinculación
--------------------
1. La web (sin autenticar) pide una sesión:  POST /auth/qr/nueva
   Envía el SHA-256 de un secreto que solo ella conserva. Recibe un ``token``
   público y lo dibuja como QR.
2. La web consulta el estado cada pocos segundos: GET /auth/qr/{token}
3. El operador, ya autenticado en la app, escanea el QR:
   POST /auth/qr/{token}/escanear   → el estado pasa a ESCANEADO
   La app muestra en pantalla qué se va a autorizar (anti-phishing).
4. El operador confirma o cancela: POST /auth/qr/{token}/confirmar
5. La web, al detectar APROBADO, reclama la sesión presentando su secreto:
   POST /auth/qr/{token}/reclamar → recibe el JWT. El token queda CONSUMIDA.

Decisiones de seguridad
-----------------------
* Token aleatorio de 256 bits y vigencia breve (120 s).
* Un solo uso: tras reclamarse, la sesión no vuelve a entregar el JWT.
* El JWT solo se entrega a quien demuestre poseer el secreto de cliente, de
  modo que fotografiar el QR no basta para robar la sesión.
* La aprobación exige que el usuario esté autenticado en la app: el acceso que
  se concede es exactamente el suyo, con su mismo rol.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import sesion_actual_id, usuario_actual
from ..enums import EstadoQR, RolUsuario
from ..models import AsignacionOperador, Auditoria, Reservorio, SesionQR, Usuario
from ..schemas import (
    QRConfirmarIn, QREstadoOut, QRNuevaIn, QRNuevaOut, ReservorioOut,
    SesionVinculadaOut, TokenOut, UsuarioOut,
)
from ..services.perfil import perfil_de
from ..security import crear_token
from ..timeutils import aware_utc

router = APIRouter(prefix="/auth/qr", tags=["auth-qr"])

VIGENCIA_SEG = 120          # igual que WhatsApp Web: obliga a refrescar el código
PREFIJO_QR = "YAKU-QR"      # la app rechaza cualquier QR sin este prefijo


def _sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _vencida(sesion: SesionQR, ahora: datetime) -> bool:
    return aware_utc(sesion.expira_en) < ahora


def _obtener(db: Session, token: str) -> SesionQR:
    sesion = db.query(SesionQR).filter(SesionQR.token == token).first()
    if not sesion:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Código QR no válido")
    # La expiración se evalúa siempre al leer: no requiere tarea programada.
    if _vencida(sesion, datetime.now(timezone.utc)) and sesion.estado in (
        EstadoQR.PENDIENTE, EstadoQR.ESCANEADO
    ):
        sesion.estado = EstadoQR.EXPIRADO
        db.commit()
    return sesion


# ── 1. La web solicita un código ────────────────────────────────
@router.post("/nueva", response_model=QRNuevaOut, status_code=status.HTTP_201_CREATED)
def nueva_sesion(datos: QRNuevaIn, request: Request, db: Session = Depends(get_db)):
    token = secrets.token_urlsafe(32)
    sesion = SesionQR(
        token=token,
        client_hash=datos.client_hash,
        estado=EstadoQR.PENDIENTE,
        expira_en=datetime.now(timezone.utc) + timedelta(seconds=VIGENCIA_SEG),
        ip_origen=request.client.host if request.client else None,
        user_agent=(request.headers.get("user-agent") or "")[:255],
    )
    db.add(sesion)
    db.commit()
    return QRNuevaOut(
        token=token,
        contenido_qr=f"{PREFIJO_QR}:{token}",
        expira_en_seg=VIGENCIA_SEG,
    )


# ── 2. La web consulta el estado (sondeo) ───────────────────────
@router.get("/{token}", response_model=QREstadoOut)
def estado_sesion(token: str, db: Session = Depends(get_db)):
    sesion = _obtener(db, token)
    nombres = None
    if sesion.estado in (EstadoQR.ESCANEADO, EstadoQR.APROBADO) and sesion.usuario_id:
        usuario = db.get(Usuario, sesion.usuario_id)
        nombres = usuario.nombres if usuario else None
    # El JWT nunca viaja en el sondeo: se entrega solo en /reclamar.
    return QREstadoOut(estado=sesion.estado, usuario_nombres=nombres)


# ── 3. La app escanea el código (requiere sesión en el móvil) ───
@router.post("/{token}/escanear", response_model=QREstadoOut)
def escanear(token: str, db: Session = Depends(get_db),
             usuario: Usuario = Depends(usuario_actual)):
    sesion = _obtener(db, token)
    if sesion.estado == EstadoQR.EXPIRADO:
        raise HTTPException(status.HTTP_410_GONE, "El código expiró; genere uno nuevo en la web")
    if sesion.estado != EstadoQR.PENDIENTE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este código ya fue utilizado")

    sesion.estado = EstadoQR.ESCANEADO
    sesion.usuario_id = usuario.usuario_id
    sesion.escaneado_en = datetime.now(timezone.utc)
    db.commit()
    return QREstadoOut(estado=sesion.estado, usuario_nombres=usuario.nombres)


# ── 4. La app confirma o cancela ────────────────────────────────
@router.post("/{token}/confirmar", response_model=QREstadoOut)
def confirmar(token: str, datos: QRConfirmarIn = Body(default=QRConfirmarIn()),
              db: Session = Depends(get_db),
              usuario: Usuario = Depends(usuario_actual)):
    sesion = _obtener(db, token)
    if sesion.estado == EstadoQR.EXPIRADO:
        raise HTTPException(status.HTTP_410_GONE, "El código expiró")
    if sesion.estado != EstadoQR.ESCANEADO:
        raise HTTPException(status.HTTP_409_CONFLICT, "El código no está a la espera de confirmación")
    # Solo quien escaneó puede resolver la sesión.
    if sesion.usuario_id != usuario.usuario_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este código fue escaneado por otro usuario")

    sesion.estado = EstadoQR.APROBADO if datos.aprobar else EstadoQR.RECHAZADO
    sesion.resuelto_en = datetime.now(timezone.utc)
    db.add(Auditoria(
        usuario_id=usuario.usuario_id,
        accion="QR_APROBADO" if datos.aprobar else "QR_RECHAZADO",
        entidad_afectada="sesion_qr", registro_id=str(sesion.sesion_qr_id),
        detalle=f"Vinculación web desde {sesion.ip_origen or 'origen desconocido'}",
    ))
    db.commit()
    return QREstadoOut(estado=sesion.estado, usuario_nombres=usuario.nombres)


# ── 5. La web reclama la sesión con su secreto ──────────────────
@router.post("/{token}/reclamar", response_model=TokenOut)
def reclamar(token: str, client_secret: str = Body(..., embed=True),
             db: Session = Depends(get_db)):
    sesion = _obtener(db, token)
    if sesion.estado != EstadoQR.APROBADO:
        raise HTTPException(status.HTTP_409_CONFLICT, "La sesión no está aprobada")
    # El secreto demuestra que quien reclama es el navegador que generó el QR.
    if _sha256(client_secret) != sesion.client_hash:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Secreto de cliente inválido")

    usuario = db.get(Usuario, sesion.usuario_id)
    if not usuario or not usuario.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inactivo")

    sesion.estado = EstadoQR.CONSUMIDA      # un solo uso
    db.add(Auditoria(
        usuario_id=usuario.usuario_id, accion="LOGIN_QR",
        entidad_afectada="usuario", registro_id=str(usuario.usuario_id),
        ip_origen=sesion.ip_origen,
    ))

    reservorios: list[Reservorio] = []
    if usuario.rol == RolUsuario.OPERADOR:
        reservorios = (
            db.query(Reservorio)
            .join(AsignacionOperador, AsignacionOperador.reservorio_id == Reservorio.reservorio_id)
            .filter(AsignacionOperador.usuario_id == usuario.usuario_id,
                    AsignacionOperador.vigente.is_(True))
            .all()
        )
    db.commit()

    return TokenOut(
        # El sid ata el token a esta sesión: podrá revocarse desde la app.
        access_token=crear_token(usuario.usuario_id, usuario.rol.value,
                                 usuario.nombres, sid=sesion.sesion_qr_id),
        usuario=perfil_de(db, usuario),
        reservorios=[ReservorioOut.model_validate(r) for r in reservorios],
    )


# ═══════════════════════════════════════════════════════════════
#  Dispositivos vinculados (gestión desde la app, patrón WhatsApp)
# ═══════════════════════════════════════════════════════════════

def _describir_dispositivo(user_agent: str | None) -> str:
    """Convierte el user-agent en un nombre legible para el usuario."""
    ua = (user_agent or "").lower()
    navegador = next((n for c, n in [
        ("edg/", "Edge"), ("chrome", "Chrome"), ("firefox", "Firefox"),
        ("safari", "Safari"),
    ] if c in ua), "Navegador")
    sistema = next((s for c, s in [
        ("windows", "Windows"), ("android", "Android"), ("iphone", "iPhone"),
        ("ipad", "iPad"), ("mac os", "Mac"), ("linux", "Linux"),
    ] if c in ua), "equipo desconocido")
    return f"{navegador} en {sistema}"


@router.get("/sesiones/activas", response_model=list[SesionVinculadaOut])
def listar_sesiones(db: Session = Depends(get_db),
                    usuario: Usuario = Depends(usuario_actual),
                    sid: int | None = Depends(sesion_actual_id)):
    """Dispositivos web vinculados y activos del usuario."""
    filas = (
        db.query(SesionQR)
        .filter(SesionQR.usuario_id == usuario.usuario_id,
                SesionQR.estado == EstadoQR.CONSUMIDA)
        .order_by(SesionQR.resuelto_en.desc())
        .all()
    )
    return [
        SesionVinculadaOut(
            sesion_id=s.sesion_qr_id,
            dispositivo=_describir_dispositivo(s.user_agent),
            ip_origen=s.ip_origen,
            vinculado_en=s.resuelto_en or s.creado_en,
            es_sesion_actual=(s.sesion_qr_id == sid),
        )
        for s in filas
    ]


@router.delete("/sesiones/activas/{sesion_id}", status_code=status.HTTP_200_OK)
def cerrar_sesion(sesion_id: int, db: Session = Depends(get_db),
                  usuario: Usuario = Depends(usuario_actual)):
    """Cierra un dispositivo vinculado; su token deja de valer de inmediato."""
    sesion = db.get(SesionQR, sesion_id)
    if not sesion or sesion.usuario_id != usuario.usuario_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesión no encontrada")
    if sesion.estado != EstadoQR.CONSUMIDA:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esa sesión ya no está activa")

    sesion.estado = EstadoQR.REVOCADA
    db.add(Auditoria(
        usuario_id=usuario.usuario_id, accion="QR_SESION_CERRADA",
        entidad_afectada="sesion_qr", registro_id=str(sesion.sesion_qr_id),
        detalle=f"Cierre de {_describir_dispositivo(sesion.user_agent)}",
    ))
    db.commit()
    return {"cerradas": 1, "sesion_id": sesion_id}


@router.delete("/sesiones/activas", status_code=status.HTTP_200_OK)
def cerrar_todas(db: Session = Depends(get_db),
                 usuario: Usuario = Depends(usuario_actual),
                 sid: int | None = Depends(sesion_actual_id)):
    """Cierra todos los dispositivos vinculados del usuario."""
    filas = (
        db.query(SesionQR)
        .filter(SesionQR.usuario_id == usuario.usuario_id,
                SesionQR.estado == EstadoQR.CONSUMIDA)
        .all()
    )
    for s in filas:
        s.estado = EstadoQR.REVOCADA
    if filas:
        db.add(Auditoria(
            usuario_id=usuario.usuario_id, accion="QR_SESIONES_CERRADAS",
            entidad_afectada="sesion_qr",
            detalle=f"Cierre masivo de {len(filas)} dispositivo(s)",
        ))
    db.commit()
    return {"cerradas": len(filas)}
