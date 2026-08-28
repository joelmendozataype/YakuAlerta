import 'package:flutter_test/flutter_test.dart';
import 'package:yakuni/core/rules/motor_riesgo.dart';

// Espejo de las pruebas del backend: mismos valores límite (CA-HU03/HU-06).
void main() {
  group('Clasificación (regla de peor caso)', () {
    test('verde: cloro alto y turbidez baja', () {
      expect(clasificar(cloroMgL: 0.72, turbidezUnt: 2.0).nivel, NivelRiesgo.verde);
    });
    test('frontera verde 0.50 / 5 UNT', () {
      expect(clasificar(cloroMgL: 0.50, turbidezUnt: 5.0).nivel, NivelRiesgo.verde);
    });
    test('amarillo 0.49 y 0.30', () {
      expect(clasificar(cloroMgL: 0.49, turbidezUnt: 2.0).nivel, NivelRiesgo.amarillo);
      expect(clasificar(cloroMgL: 0.30, turbidezUnt: 2.0).nivel, NivelRiesgo.amarillo);
    });
    test('rojo por cloro bajo 0.29', () {
      expect(clasificar(cloroMgL: 0.29, turbidezUnt: 2.0).nivel, NivelRiesgo.rojo);
    });
    test('rojo por turbidez 6 UNT (peor caso)', () {
      expect(clasificar(cloroMgL: 1.0, turbidezUnt: 6.0).nivel, NivelRiesgo.rojo);
    });
    test('rojo por observación crítica', () {
      expect(clasificar(cloroMgL: 0.9, turbidezUnt: 1.0, observaciones: 'agua turbia').nivel,
          NivelRiesgo.rojo);
    });
  });

  group('Dosis de recloración', () {
    test('verde no genera recomendación', () {
      expect(calcularDosis(nivel: NivelRiesgo.verde, volumenM3: 12), isNull);
    });
    test('amarillo 12 m³ / 70% → plazo 48 h y dosis > 0', () {
      final r = calcularDosis(nivel: NivelRiesgo.amarillo, volumenM3: 12, cloroMedido: 0.41);
      expect(r, isNotNull);
      expect(r!.plazoHoras, 48);
      expect(r.gramosHipoclorito, greaterThan(0));
    });
    test('rojo → plazo 24 h y protocolo con HERVIR', () {
      final r = calcularDosis(nivel: NivelRiesgo.rojo, volumenM3: 20, cloroMedido: 0.1);
      expect(r!.plazoHoras, 24);
      expect(r.protocolo.contains('HERVIR'), isTrue);
    });
  });
}
