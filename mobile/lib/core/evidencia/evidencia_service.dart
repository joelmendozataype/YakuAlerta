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

  /// Borra del dispositivo una foto que el servidor ya recibió.
  ///
  /// Las fotos se acumulaban sin límite en el almacenamiento de la app: cada
  /// medición con evidencia dejaba su copia para siempre, y el celular de un
  /// operador rural no sobra en espacio. Una vez que el servidor la guardó y
  /// la registró, la copia local no aporta nada.
  ///
  /// No falla si el archivo ya no está: lo que importa es que deje de ocupar.
  Future<void> descartarLocal(String ruta) async {
    try {
      final archivo = File(ruta);
      if (await archivo.exists()) await archivo.delete();
    } catch (_) {
      // Si el sistema no deja borrarla, la medición ya está a salvo igual.
    }
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
