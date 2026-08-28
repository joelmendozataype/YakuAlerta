import 'package:flutter_test/flutter_test.dart';
import 'package:yakuni/core/rules/motor_riesgo.dart';
import 'package:yakuni/core/vision/dpd_analyzer.dart';

// Pruebas del análisis de color DPD (HU-05).
// Semántica del dominio: incoloro = SIN cloro = ROJO; magenta intenso = cloro
// alto = VERDE. La estimación crece con la intensidad del rosado.
void main() {
  group('rgbToHsv', () {
    test('blanco tiene saturación 0', () {
      final hsv = rgbToHsv(255, 255, 255);
      expect(hsv.s, 0);
      expect(hsv.v, 1.0);
    });
    test('magenta puro cae en el matiz ~300°', () {
      final hsv = rgbToHsv(255, 0, 255);
      expect(hsv.h, closeTo(300, 1));
      expect(hsv.s, 1.0);
    });
  });

  group('estimarCloro', () {
    test('muestra incolora → cloro ~0 y nivel ROJO (sin desinfección)', () {
      final r = estimarCloro(248, 248, 248);
      expect(r.cloroEstimado, lessThan(0.30));
      expect(r.nivelEstimado, NivelRiesgo.rojo);
    });

    test('magenta intenso → cloro alto y nivel VERDE (agua clorada)', () {
      final r = estimarCloro(200, 20, 120);
      expect(r.cloroEstimado, greaterThan(0.5));
      expect(r.nivelEstimado, NivelRiesgo.verde);
    });

    test('la estimación crece con la intensidad del rosado', () {
      final tenue = estimarCloro(245, 215, 230); // rosa muy tenue
      final intenso = estimarCloro(210, 40, 130); // magenta fuerte
      expect(intenso.cloroEstimado, greaterThan(tenue.cloroEstimado));
    });

    test('nunca excede el rango físico del comparador', () {
      final r = estimarCloro(255, 0, 200);
      expect(r.cloroEstimado, lessThanOrEqualTo(cloroMaxDpd));
      expect(r.cloroEstimado, greaterThanOrEqualTo(0));
    });

    test('la corrección por tarjeta de calibración no rompe el rango', () {
      final r = estimarCloro(180, 20, 110, rBlanco: 230, gBlanco: 235, bBlanco: 240);
      expect(r.cloroEstimado, inInclusiveRange(0, cloroMaxDpd));
      expect(r.confianza, inInclusiveRange(0, 1));
    });
  });
}
