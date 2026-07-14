/// Motor de reglas LOCAL — idéntico al del backend (HU-03 / RF-04).
///
/// Permite clasificar la medición SIN conexión, en el propio dispositivo,
/// aplicando la regla de peor caso del D.S. N.° 031-2010-SA:
///
///   🟢 VERDE     cloro ≥ 0.50 mg/L  y  turbidez ≤ 5 UNT
///   🟡 AMARILLO  cloro 0.30–0.49 mg/L
///   🔴 ROJO      cloro < 0.30 mg/L  ó  turbidez > 5 UNT  ó  observación crítica
library;

enum NivelRiesgo { verde, amarillo, rojo }

extension NivelRiesgoX on NivelRiesgo {
  String get valor => switch (this) {
        NivelRiesgo.verde => 'VERDE',
        NivelRiesgo.amarillo => 'AMARILLO',
        NivelRiesgo.rojo => 'ROJO',
      };

  String get etiqueta => switch (this) {
        NivelRiesgo.verde => 'Agua segura',
        NivelRiesgo.amarillo => 'Agua en riesgo',
        NivelRiesgo.rojo => 'Agua NO segura',
      };

  bool get esAlerta => this != NivelRiesgo.verde;
}

/// Umbrales configurables (RNF-07). Por defecto, los del reglamento.
class Umbrales {
  final double cloroVerde; // cloro ≥ este valor → apto
  final double cloroRojo; // cloro < este valor → rojo
  final double turbidezRojo; // turbidez > este valor → rojo

  const Umbrales({
    this.cloroVerde = 0.50,
    this.cloroRojo = 0.30,
    this.turbidezRojo = 5.0,
  });
}

const List<String> palabrasCriticas = [
  'turbia', 'turbio', 'color', 'olor', 'sabor', 'heces', 'animal muerto',
  'contamina', 'sucia', 'lodo', 'barro', 'espuma', 'brote', 'diarrea',
];

class ResultadoClasificacion {
  final NivelRiesgo nivel;
  final List<String> motivos;
  const ResultadoClasificacion(this.nivel, this.motivos);
}

int _sev(NivelRiesgo n) => switch (n) {
      NivelRiesgo.verde => 0,
      NivelRiesgo.amarillo => 1,
      NivelRiesgo.rojo => 2,
    };

NivelRiesgo _peor(NivelRiesgo a, NivelRiesgo b) => _sev(a) >= _sev(b) ? a : b;

/// Clasifica una medición aplicando la regla de peor caso.
ResultadoClasificacion clasificar({
  double? cloroMgL,
  double? turbidezUnt,
  String? observaciones,
  bool labNoConforme = false,
  Umbrales umbrales = const Umbrales(),
}) {
  var nivel = NivelRiesgo.verde;
  final motivos = <String>[];

  if (cloroMgL != null) {
    if (cloroMgL < umbrales.cloroRojo) {
      nivel = _peor(nivel, NivelRiesgo.rojo);
      motivos.add('Cloro ${cloroMgL.toStringAsFixed(2)} mg/L: desinfección crítica.');
    } else if (cloroMgL < umbrales.cloroVerde) {
      nivel = _peor(nivel, NivelRiesgo.amarillo);
      motivos.add('Cloro ${cloroMgL.toStringAsFixed(2)} mg/L por debajo del mínimo.');
    }
  } else {
    motivos.add('Cloro no medido.');
  }

  if (turbidezUnt != null && turbidezUnt > umbrales.turbidezRojo) {
    nivel = _peor(nivel, NivelRiesgo.rojo);
    motivos.add('Turbidez ${turbidezUnt.toStringAsFixed(1)} UNT: riesgo microbiológico.');
  }

  if (observaciones != null && observaciones.isNotEmpty) {
    final obs = observaciones.toLowerCase();
    final coincidencias = palabrasCriticas.where(obs.contains);
    if (coincidencias.isNotEmpty) {
      nivel = _peor(nivel, NivelRiesgo.rojo);
      motivos.add('Observación crítica: «${coincidencias.first}».');
    }
  }

  if (labNoConforme) {
    nivel = _peor(nivel, NivelRiesgo.rojo);
    motivos.add('Laboratorio NO CONFORME (rojo forzado).');
  }

  if (nivel == NivelRiesgo.verde && motivos.isEmpty) {
    motivos.add('Parámetros dentro de norma.');
  }
  return ResultadoClasificacion(nivel, motivos);
}

/// Cálculo de dosis de recloración (HU-06). `null` si el nivel es verde.
class Recomendacion {
  final double gramosHipoclorito;
  final double concentracion;
  final int plazoHoras;
  final String protocolo;
  const Recomendacion(this.gramosHipoclorito, this.concentracion, this.plazoHoras, this.protocolo);
}

const _protocoloRojo =
    'AGUA NO SEGURA. Acciones inmediatas:\n1) Avisar: HERVIR el agua (1 min).\n'
    '2) Limpieza y desinfección del reservorio.\n3) Recloración con la dosis indicada.\n'
    '4) Evaluar suspensión preventiva.\n5) Remedir en 24 horas.';
const _protocoloAmarillo =
    'AGUA EN RIESGO. Acciones:\n1) Recloración con la dosis indicada.\n'
    '2) Verificar el sistema de dosificación.\n3) Remedir en 48 horas.';

Recomendacion? calcularDosis({
  required NivelRiesgo nivel,
  required double volumenM3,
  double? cloroMedido,
  double concentracion = 70.0,
}) {
  if (nivel == NivelRiesgo.verde) return null;
  final conc = concentracion.clamp(1.0, 100.0);
  final medido = cloroMedido ?? 0.0;
  final demanda = (1.5 - medido) < 1.0 ? 1.0 : (1.5 - medido);
  final gramos = demanda * volumenM3 * 100.0 / conc;
  return Recomendacion(
    double.parse(gramos.toStringAsFixed(2)),
    conc.toDouble(),
    nivel == NivelRiesgo.rojo ? 24 : 48,
    nivel == NivelRiesgo.rojo ? _protocoloRojo : _protocoloAmarillo,
  );
}
