import 'dart:io';

import 'package:geolocator/geolocator.dart';
import 'package:image/image.dart' as img;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// Captura de evidencia fotográfica georreferenciada — HU-08 / RF-14.
///
/// Comprime la foto antes de guardarla (para cumplir el límite de datos,
/// RNF-03) y obtiene las coordenadas GPS **solo en el momento de la captura**
/// (no mantiene el GPS activo, RNF-08).
class EvidenciaService {
  EvidenciaService._();
  static final EvidenciaService instance = EvidenciaService._();

  /// Comprime la imagen [origen] (JPEG, máx. 1024 px de ancho) y la guarda en
  /// el almacenamiento de la app. Devuelve la ruta del archivo comprimido.
  Future<String> comprimirYGuardar(String origen, {String? nombre}) async {
    final bytes = await File(origen).readAsBytes();
    final imagen = img.decodeImage(bytes);
    if (imagen == null) throw Exception('No se pudo leer la imagen.');

    final redimensionada = imagen.width > 1024
        ? img.copyResize(imagen, width: 1024)
        : imagen;
    final jpg = img.encodeJpg(redimensionada, quality: 70);

    final dir = await getApplicationDocumentsDirectory();
    final destino = p.join(
      dir.path,
      nombre ?? 'evidencia_${DateTime.now().millisecondsSinceEpoch}.jpg',
    );
    await File(destino).writeAsBytes(jpg);
    return destino;
  }

  /// Obtiene las coordenadas actuales (bajo demanda). Devuelve null si no hay
  /// permiso o el GPS está desactivado (la evidencia se guarda igual, sin geo).
  Future<Position?> ubicacionActual() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) return null;
      var permiso = await Geolocator.checkPermission();
      if (permiso == LocationPermission.denied) {
        permiso = await Geolocator.requestPermission();
      }
      if (permiso == LocationPermission.denied ||
          permiso == LocationPermission.deniedForever) {
        return null;
      }
      return await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      );
    } catch (_) {
      return null;
    }
  }
}
