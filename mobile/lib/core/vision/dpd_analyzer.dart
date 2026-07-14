/// Análisis de color del comparador DPD por cámara — HU-05 / RF-03.
///
/// El reactivo DPD-1 tiñe la muestra de **rosado→magenta** en proporción al
/// cloro residual libre: incoloro ≈ 0 mg/L, rosado tenue ≈ 0.3–0.5 mg/L,
/// magenta intenso ≈ 1.5–3 mg/L. Este módulo estima el cloro a partir del
/// color promedio de la muestra, en espacio HSV, con corrección opcional por
/// una tarjeta de calibración blanca.
///
/// Principio de transparencia (documento de diseño): el valor estimado SIEMPRE
/// se muestra al operador para su confirmación o corrección manual.
library;

import 'dart:math' as math;

import '../rules/motor_riesgo.dart';

/// Resultado de la estimación por cámara.
class DpdResultado {
  /// Cloro estimado en mg/L (rango físico del comparador: 0–3.5).
  final double cloroEstimado;

  /// Confianza 0..1 de la estimación (según saturación y luminosidad).
  final double confianza;

  /// Nivel de riesgo estimado (mismo motor de reglas que el registro manual).
  final NivelRiesgo nivelEstimado;

  /// Componentes HSV medidos (diagnóstico/depuración).
  final double hue, saturation, value;

  const DpdResultado({
    required this.cloroEstimado,
    required this.confianza,
    required this.nivelEstimado,
    required this.hue,
    required this.saturation,
    required this.value,
  });

  bool get confiable => confianza >= 0.5;
}

/// Cloro máximo legible por el comparador DPD colorimétrico (mg/L).
const double cloroMaxDpd = 3.5;

/// Conversión RGB (0–255) → HSV. H en grados [0,360), S y V en [0,1].
({double h, double s, double v}) rgbToHsv(int r, int g, int b) {
  final rf = r / 255.0, gf = g / 255.0, bf = b / 255.0;
  final maxC = math.max(rf, math.max(gf, bf));
  final minC = math.min(rf, math.min(gf, bf));
  final delta = maxC - minC;

  double h;
  if (delta == 0) {
    h = 0;
  } else if (maxC == rf) {
    h = 60 * (((gf - bf) / delta) % 6);
  } else if (maxC == gf) {
    h = 60 * (((bf - rf) / delta) + 2);
  } else {
    h = 60 * (((rf - gf) / delta) + 4);
  }
  if (h < 0) h += 360;

  final s = maxC == 0 ? 0.0 : delta / maxC;
  return (h: h, s: s, v: maxC);
}

/// Estima el cloro a partir del color promedio (RGB 0–255) de la muestra.
///
/// [rBlanco],[gBlanco],[bBlanco] son el color del parche BLANCO de la tarjeta
/// de calibración (opcional): si se proveen, se corrige la iluminación
/// normalizando la muestra respecto al blanco de referencia.
DpdResultado estimarCloro(
  int r,
  int g,
  int b, {
  int? rBlanco,
  int? gBlanco,
  int? bBlanco,
}) {
  // ── Corrección de iluminación por tarjeta de calibración ─────
  if (rBlanco != null && gBlanco != null && bBlanco != null &&
      rBlanco > 0 && gBlanco > 0 && bBlanco > 0) {
    // Balance de blancos simple: escala cada canal para que el blanco → 255.
    r = (r * 255 / rBlanco).clamp(0, 255).round();
    g = (g * 255 / gBlanco).clamp(0, 255).round();
    b = (b * 255 / bBlanco).clamp(0, 255).round();
  }

  final hsv = rgbToHsv(r, g, b);

  // ── Índice de "rosado/magenta" del DPD ───────────────────────
  // El rosa-magenta tiene el matiz en ~300–360° ó 0–30°. La intensidad del
  // color (saturación) crece con la concentración de cloro.
  final enRangoMagenta = hsv.h >= 285 || hsv.h <= 25;

  // Si el color no es rosado (p. ej. verdoso/azulado), la muestra no es DPD
  // válida o el cloro es ~0: saturación efectiva baja.
  final satEfectiva = enRangoMagenta ? hsv.s : hsv.s * 0.25;

  // Mapeo de calibración MVP (lineal sobre la saturación efectiva).
  // Calibrable en campo con fotografías reales del piloto (Fase 2, TFLite).
  //   sat 0.00 → 0.0 mg/L   ·   sat 0.75 → ~2.6 mg/L   ·   sat 1.0 → 3.5 mg/L
  double cloro = satEfectiva * cloroMaxDpd;
  cloro = double.parse(cloro.clamp(0, cloroMaxDpd).toStringAsFixed(2));

  // ── Confianza: alta si hay buena luz (V) y color definido ────
  // Luz muy baja o muy quemada, o color ambiguo → menor confianza.
  final luzOk = (hsv.v >= 0.25 && hsv.v <= 0.98) ? 1.0 : 0.5;
  final colorDefinido = enRangoMagenta ? 1.0 : 0.6;
  final confianza = (0.4 + 0.6 * satEfectiva) * luzOk * colorDefinido;

  final nivel = clasificar(cloroMgL: cloro).nivel;

  return DpdResultado(
    cloroEstimado: cloro,
    confianza: confianza.clamp(0.0, 1.0),
    nivelEstimado: nivel,
    hue: hsv.h,
    saturation: hsv.s,
    value: hsv.v,
  );
}
