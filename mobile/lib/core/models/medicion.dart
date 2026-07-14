import '../rules/motor_riesgo.dart';

/// Estados de la cola de sincronización (offline-first).
enum EstadoSync { pendiente, enviadoSms, sincronizado }

extension EstadoSyncX on EstadoSync {
  String get valor => switch (this) {
        EstadoSync.pendiente => 'PENDIENTE',
        EstadoSync.enviadoSms => 'ENVIADO_SMS',
        EstadoSync.sincronizado => 'SINCRONIZADO',
      };
  static EstadoSync desde(String s) => switch (s) {
        'ENVIADO_SMS' => EstadoSync.enviadoSms,
        'SINCRONIZADO' => EstadoSync.sincronizado,
        _ => EstadoSync.pendiente,
      };
}

/// Medición registrada en campo. Se guarda primero en SQLite (offline) y
/// luego se sincroniza con el backend, deduplicando por [uuidRegistro].
class Medicion {
  final int? idLocal;
  final String uuidRegistro;
  final int reservorioId;
  final DateTime fechaHora;
  final double? cloroMgL;
  final double? turbidezUnt;
  final String metodoCloro; // MANUAL | CAMARA_DPD
  final String? observaciones;
  final NivelRiesgo nivel;
  final EstadoSync estadoSync;
  final String? rutaFoto;
  final double? latitud;
  final double? longitud;

  const Medicion({
    this.idLocal,
    required this.uuidRegistro,
    required this.reservorioId,
    required this.fechaHora,
    this.cloroMgL,
    this.turbidezUnt,
    this.metodoCloro = 'MANUAL',
    this.observaciones,
    required this.nivel,
    this.estadoSync = EstadoSync.pendiente,
    this.rutaFoto,
    this.latitud,
    this.longitud,
  });

  Map<String, dynamic> toDb() => {
        'uuid_registro': uuidRegistro,
        'reservorio_id': reservorioId,
        'fecha_hora': fechaHora.toIso8601String(),
        'cloro_mg_l': cloroMgL,
        'turbidez_unt': turbidezUnt,
        'metodo_cloro': metodoCloro,
        'observaciones': observaciones,
        'nivel_riesgo': nivel.valor,
        'estado_sync': estadoSync.valor,
        'ruta_foto': rutaFoto,
        'latitud': latitud,
        'longitud': longitud,
      };

  factory Medicion.fromDb(Map<String, dynamic> m) => Medicion(
        idLocal: m['id_local'] as int?,
        uuidRegistro: m['uuid_registro'] as String,
        reservorioId: m['reservorio_id'] as int,
        fechaHora: DateTime.parse(m['fecha_hora'] as String),
        cloroMgL: (m['cloro_mg_l'] as num?)?.toDouble(),
        turbidezUnt: (m['turbidez_unt'] as num?)?.toDouble(),
        metodoCloro: m['metodo_cloro'] as String? ?? 'MANUAL',
        observaciones: m['observaciones'] as String?,
        nivel: switch (m['nivel_riesgo']) {
          'ROJO' => NivelRiesgo.rojo,
          'AMARILLO' => NivelRiesgo.amarillo,
          _ => NivelRiesgo.verde,
        },
        estadoSync: EstadoSyncX.desde(m['estado_sync'] as String? ?? 'PENDIENTE'),
        rutaFoto: m['ruta_foto'] as String?,
        latitud: (m['latitud'] as num?)?.toDouble(),
        longitud: (m['longitud'] as num?)?.toDouble(),
      );

  /// Payload para el endpoint /sync del backend.
  Map<String, dynamic> toApi() => {
        'uuid_registro': uuidRegistro,
        'reservorio_id': reservorioId,
        'fecha_hora': fechaHora.toUtc().toIso8601String(),
        'cloro_mg_l': cloroMgL,
        'turbidez_unt': turbidezUnt,
        'metodo_cloro': metodoCloro,
        'observaciones': observaciones,
        'origen': 'SINCRONIZADO',
      };

  /// SMS estructurado de respaldo (HU-11): YA;RES-XXX;CL:..;TB:..;OBS:..;UUID:..
  String toSms(String codigoReservorio) {
    final b = StringBuffer('YA;$codigoReservorio');
    if (cloroMgL != null) b.write(';CL:${cloroMgL!.toStringAsFixed(2)}');
    if (turbidezUnt != null) b.write(';TB:${turbidezUnt!.toStringAsFixed(1)}');
    if (observaciones != null && observaciones!.isNotEmpty) b.write(';OBS:$observaciones');
    b.write(';UUID:$uuidRegistro');
    return b.toString();
  }
}
