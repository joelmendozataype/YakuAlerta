import 'package:connectivity_plus/connectivity_plus.dart';

import '../api/api_client.dart';
import '../db/local_db.dart';
import '../models/medicion.dart';

/// Servicio de sincronización automática (HU-12 / RF-08).
///
/// Al recuperar conectividad, envía en lote las mediciones pendientes.
/// La deduplicación por UUID la resuelve el backend: si un registro ya viajó
/// por SMS, no se duplica al sincronizar por datos.
class SyncService {
  SyncService._();
  static final SyncService instance = SyncService._();

  final _api = ApiClient.instance;
  final _db = LocalDb.instance;
  bool _sincronizando = false;

  Future<bool> hayConexion() async {
    final estados = await Connectivity().checkConnectivity();
    return !estados.contains(ConnectivityResult.none);
  }

  /// Escucha cambios de conectividad y sincroniza automáticamente.
  void iniciarAutoSync() {
    Connectivity().onConnectivityChanged.listen((estados) {
      if (!estados.contains(ConnectivityResult.none)) {
        sincronizar();
      }
    });
  }

  /// Devuelve el resumen de la sincronización o null si no había red/datos.
  Future<ResultadoSync?> sincronizar() async {
    if (_sincronizando) return null;
    if (!await hayConexion()) return null;

    final pendientes = await _db.pendientes();
    if (pendientes.isEmpty) return const ResultadoSync(0, 0, 0);

    _sincronizando = true;
    try {
      final resp = await _api.sync(pendientes.map((m) => m.toApi()).toList());
      for (final m in pendientes) {
        await _db.marcarEstado(m.uuidRegistro, EstadoSync.sincronizado);
      }
      // 2ª fase: subir las fotos de evidencia ya que las mediciones existen.
      await _subirFotosPendientes();
      return ResultadoSync(
        (resp['insertadas'] as int?) ?? 0,
        (resp['duplicadas'] as int?) ?? 0,
        (resp['alertas_generadas'] as int?) ?? 0,
      );
    } on ApiException {
      return null; // se reintenta en el próximo evento de conectividad
    } finally {
      _sincronizando = false;
    }
  }

  /// HU-08 (2ª fase): sube las fotos de evidencia de mediciones ya sincronizadas.
  /// Cada foto se marca como subida para no repetir; los fallos se reintentan
  /// en la próxima sincronización.
  Future<void> _subirFotosPendientes() async {
    for (final m in await _db.fotosPendientes()) {
      try {
        await _api.subirEvidencia(
          m.uuidRegistro, m.rutaFoto!,
          latitud: m.latitud, longitud: m.longitud,
        );
        await _db.marcarFotoSubida(m.uuidRegistro);
      } on ApiException {
        // se reintenta luego; no interrumpe la subida del resto
      }
    }
  }
}

class ResultadoSync {
  final int insertadas;
  final int duplicadas;
  final int alertas;
  const ResultadoSync(this.insertadas, this.duplicadas, this.alertas);
}
