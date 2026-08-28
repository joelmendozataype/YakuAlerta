"""Consulta pública del estado del agua y afiche comunitario — RF-06 / Desafío 2.

La página pública es el destino del código QR del afiche: cualquier vecino la
abre con la cámara de su celular, sin instalar nada ni iniciar sesión. Está
pensada para conexiones lentas y pantallas pequeñas, y solo muestra información
sanitaria de interés público (sin datos personales, Ley N.° 29733).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import requiere_roles
from ..enums import RolUsuario
from ..models import Usuario
from ..services.aviso_comunitario import generar_aviso
from ..services.estado_publico import estado_de_comunidad

router = APIRouter(tags=["publico"])


def _url_publica(comunidad_id: int) -> str:
    return f"{settings.public_base_url.rstrip('/')}/publico/comunidad/{comunidad_id}"


# ── Página que abre el QR (sin autenticación) ───────────────────
@router.get("/publico/comunidad/{comunidad_id}", response_class=HTMLResponse)
def pagina_publica(comunidad_id: int, db: Session = Depends(get_db)):
    estado = estado_de_comunidad(db, comunidad_id)
    if estado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comunidad no encontrada")

    fecha = (estado.ultima_medicion.strftime("%d/%m/%Y")
             if estado.ultima_medicion else "sin registro")
    acciones = "".join(f"<li>{a}</li>" for a in estado.acciones)

    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Estado del agua · {estado.comunidad}</title>
<style>
  *{{box-sizing:border-box}}
  body{{margin:0;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
       background:#f1f5f9;color:#1e293b}}
  .caja{{max-width:520px;margin:0 auto;padding:16px}}
  .marca{{display:flex;align-items:center;gap:8px;padding:14px 4px;color:#0e4a5a;font-weight:700}}
  .tarjeta{{background:#fff;border-radius:16px;overflow:hidden;
           box-shadow:0 1px 3px rgba(0,0,0,.08)}}
  .banda{{background:#{estado.color};color:#fff;padding:26px 20px;text-align:center}}
  .banda .punto{{width:64px;height:64px;border-radius:50%;background:rgba(255,255,255,.25);
                margin:0 auto 12px;display:grid;place-items:center;font-size:32px}}
  .banda h1{{margin:0;font-size:27px;letter-spacing:.5px}}
  .banda p{{margin:6px 0 0;font-size:15px;opacity:.95}}
  .cuerpo{{padding:20px}}
  .instruccion{{font-size:19px;font-weight:700;text-align:center;margin:0 0 18px}}
  h2{{font-size:15px;color:#0e4a5a;margin:0 0 8px}}
  ul{{margin:0;padding-left:20px;line-height:1.65;font-size:15px}}
  .pie{{font-size:12px;color:#64748b;text-align:center;padding:16px 8px 28px;line-height:1.6}}
</style>
</head>
<body>
  <div class="caja">
    <div class="marca">💧 Yakuni</div>
    <div class="tarjeta">
      <div class="banda">
        <div class="punto">💧</div>
        <h1>{estado.etiqueta}</h1>
        <p>{estado.comunidad} · {estado.distrito}</p>
      </div>
      <div class="cuerpo">
        <p class="instruccion">{estado.instruccion}</p>
        <h2>¿Qué debe hacer?</h2>
        <ul>{acciones}</ul>
      </div>
    </div>
    <p class="pie">
      Última medición: {fecha}<br>
      Clasificación conforme al D.S. N.° 031-2010-SA<br>
      Información difundida por la JASS y el Área Técnica Municipal
    </p>
  </div>
</body>
</html>"""
    # Se permite una caché breve: alivia la red rural sin ocultar cambios.
    return HTMLResponse(html, headers={"Cache-Control": "public, max-age=300"})


# ── Mismo estado en JSON (integraciones y pruebas) ──────────────
@router.get("/publico/comunidad/{comunidad_id}/estado")
def estado_json(comunidad_id: int, db: Session = Depends(get_db)):
    estado = estado_de_comunidad(db, comunidad_id)
    if estado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comunidad no encontrada")
    return {
        "comunidad": estado.comunidad,
        "distrito": estado.distrito,
        "nivel": estado.nivel.value if estado.nivel else None,
        "etiqueta": estado.etiqueta,
        "instruccion": estado.instruccion,
        "acciones": estado.acciones,
        "ultima_medicion": estado.ultima_medicion,
    }


# ── Afiche imprimible (requiere sesión institucional) ───────────
@router.get("/avisos/comunidad/{comunidad_id}")
def afiche_comunitario(
    comunidad_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_roles(
        RolUsuario.ATM, RolUsuario.DESA, RolUsuario.ADMIN,
        RolUsuario.OPERADOR, RolUsuario.DIRECTIVO_JASS)),
):
    """PDF A4 para imprimir, plastificar y fijar en el punto de agua."""
    estado = estado_de_comunidad(db, comunidad_id)
    if estado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comunidad no encontrada")

    pdf = generar_aviso(estado, _url_publica(comunidad_id))
    nombre = f"aviso_{estado.comunidad.lower().replace(' ', '_')}.pdf"
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
