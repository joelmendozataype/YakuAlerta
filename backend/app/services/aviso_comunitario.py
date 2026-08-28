"""Afiche comunitario imprimible con código QR — difusión a la población.

Pieza A4 pensada para plastificarse y fijarse en el punto de agua: semáforo
grande, instrucción en lenguaje llano y un código QR que cualquier vecino puede
escanear para consultar el estado vigente sin instalar nada ni iniciar sesión.
"""
from __future__ import annotations

import io

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas

from .estado_publico import EstadoPublico

ANCHO, ALTO = A4
MARGEN = 18 * mm


def _qr_imagen(url: str) -> ImageReader:
    qr = qrcode.QRCode(box_size=10, border=1,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def _texto_centrado(c, y, texto, fuente, tamano, color):
    c.setFont(fuente, tamano)
    c.setFillColorRGB(*_rgb(color))
    c.drawCentredString(ANCHO / 2, y, texto)


def _rgb(hexa: str) -> tuple[float, float, float]:
    return tuple(int(hexa[i:i + 2], 16) / 255 for i in (0, 2, 4))


def generar_aviso(estado: EstadoPublico, url_publica: str) -> bytes:
    """Devuelve el PDF del afiche listo para imprimir."""
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Aviso comunitario — {estado.comunidad}")

    # ── Encabezado ───────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 13)
    c.setFillColorRGB(*_rgb("0E4A5A"))
    c.drawString(MARGEN, ALTO - MARGEN - 4 * mm, "Yakuni")
    c.setFont("Helvetica", 9.5)
    c.setFillColorRGB(*_rgb("64748B"))
    c.drawRightString(ANCHO - MARGEN, ALTO - MARGEN - 4 * mm,
                      "Vigilancia del agua para consumo humano")
    c.setStrokeColorRGB(*_rgb("CBD5E1"))
    c.setLineWidth(0.8)
    c.line(MARGEN, ALTO - MARGEN - 9 * mm, ANCHO - MARGEN, ALTO - MARGEN - 9 * mm)

    # ── Comunidad ────────────────────────────────────────────────
    _texto_centrado(c, ALTO - MARGEN - 26 * mm, estado.comunidad.upper(),
                    "Helvetica-Bold", 27, "0E4A5A")
    _texto_centrado(c, ALTO - MARGEN - 34 * mm,
                    f"Distrito de {estado.distrito}", "Helvetica", 12, "64748B")

    # ── Banda semafórica: el mensaje principal ───────────────────
    banda_alto = 46 * mm
    banda_y = ALTO - MARGEN - 88 * mm
    c.setFillColorRGB(*_rgb(estado.color))
    c.roundRect(MARGEN, banda_y, ANCHO - 2 * MARGEN, banda_alto, 6 * mm,
                stroke=0, fill=1)

    # Punto del semáforo, para lectura no dependiente del color
    radio = 11 * mm
    cx = MARGEN + 26 * mm
    cy = banda_y + banda_alto / 2
    c.setFillColorRGB(1, 1, 1)
    c.circle(cx, cy, radio, stroke=0, fill=1)
    c.setFillColorRGB(*_rgb(estado.color))
    c.circle(cx, cy, radio - 3.2 * mm, stroke=0, fill=1)

    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(cx + radio + 10 * mm, cy + 3 * mm, estado.etiqueta)
    c.setFont("Helvetica", 13.5)
    c.drawString(cx + radio + 10 * mm, cy - 9 * mm, estado.titular)

    # ── Instrucción principal ────────────────────────────────────
    y = banda_y - 16 * mm
    _texto_centrado(c, y, estado.instruccion, "Helvetica-Bold", 19, "1E293B")

    # ── Qué debe hacer la población ──────────────────────────────
    y -= 16 * mm
    c.setFont("Helvetica-Bold", 12.5)
    c.setFillColorRGB(*_rgb("0E4A5A"))
    c.drawString(MARGEN + 2 * mm, y, "¿Qué debe hacer?")
    y -= 10 * mm
    for accion in estado.acciones:
        c.setFillColorRGB(*_rgb(estado.color))
        c.circle(MARGEN + 5 * mm, y + 1.6 * mm, 1.8 * mm, stroke=0, fill=1)
        c.setFont("Helvetica", 13.5)
        c.setFillColorRGB(*_rgb("1E293B"))
        # Ajuste sencillo de línea para no desbordar el ancho útil
        for linea in _dividir(accion, 64):
            c.drawString(MARGEN + 11 * mm, y, linea)
            y -= 7 * mm
        y -= 2.5 * mm

    # ── Bloque del QR ────────────────────────────────────────────
    # Fluye tras las acciones, sin dejar un vacío en el centro del afiche,
    # pero nunca invade el pie de página.
    qr_lado = 46 * mm
    bloque_alto = qr_lado + 18 * mm
    bloque_y = min(y - 14 * mm - bloque_alto, ALTO - MARGEN - 200 * mm)
    bloque_y = max(bloque_y, MARGEN + 16 * mm)

    c.setFillColorRGB(*_rgb("F1F5F9"))
    c.roundRect(MARGEN, bloque_y, ANCHO - 2 * MARGEN, bloque_alto, 4 * mm,
                stroke=0, fill=1)

    qr_x = ANCHO - MARGEN - qr_lado - 9 * mm
    qr_y = bloque_y + (bloque_alto - qr_lado) / 2
    c.drawImage(_qr_imagen(url_publica), qr_x, qr_y, qr_lado, qr_lado)

    texto_y = bloque_y + bloque_alto - 14 * mm
    c.setFont("Helvetica-Bold", 15)
    c.setFillColorRGB(*_rgb("0E4A5A"))
    c.drawString(MARGEN + 9 * mm, texto_y, "¿El agua está segura hoy?")
    c.setFont("Helvetica", 11.5)
    c.setFillColorRGB(*_rgb("334155"))
    for i, linea in enumerate([
        "Apunte la cámara de su celular al código",
        "y verá el estado actualizado del agua de",
        "su comunidad. No necesita instalar nada.",
    ]):
        c.drawString(MARGEN + 9 * mm, texto_y - 10 * mm - i * 6.2 * mm, linea)

    # ── Pie con la trazabilidad del dato ─────────────────────────
    fecha = (estado.ultima_medicion.strftime("%d/%m/%Y")
             if estado.ultima_medicion else "sin registro")
    c.setFont("Helvetica", 8.5)
    c.setFillColorRGB(*_rgb("64748B"))
    c.drawString(MARGEN, MARGEN + 8 * mm,
                 f"Última medición: {fecha}"
                 f"{f'  ·  Reservorio {estado.reservorio}' if estado.reservorio else ''}")
    c.drawString(MARGEN, MARGEN + 3.5 * mm,
                 "Clasificación conforme al D.S. N.° 031-2010-SA  ·  "
                 "Emitido por la JASS con apoyo del Área Técnica Municipal")

    c.showPage()
    c.save()
    return buf.getvalue()


def _dividir(texto: str, ancho: int) -> list[str]:
    """Divide un texto en líneas de a lo más ``ancho`` caracteres."""
    palabras, lineas, actual = texto.split(), [], ""
    for palabra in palabras:
        if len(actual) + len(palabra) + 1 <= ancho:
            actual = f"{actual} {palabra}".strip()
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas
