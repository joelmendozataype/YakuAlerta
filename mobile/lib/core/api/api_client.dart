import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Cliente REST del backend YakuAlerta.
///
/// La URL base apunta por defecto al emulador Android (10.0.2.2 = localhost
/// del host). Cámbiala con --dart-define=API_URL=... para dispositivo físico.
class ApiClient {
  ApiClient._();
  static final ApiClient instance = ApiClient._();

  static const String baseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  String? _token;

  Future<String?> get token async {
    if (_token != null) return _token;
    final prefs = await SharedPreferences.getInstance();
    return _token = prefs.getString('token');
  }

  Future<void> _guardarSesion(String token, Map<String, dynamic> usuario) async {
    _token = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('token', token);
    await prefs.setString('usuario', jsonEncode(usuario));
  }

  Future<Map<String, dynamic>?> usuarioCacheado() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('usuario');
    return raw == null ? null : jsonDecode(raw) as Map<String, dynamic>;
  }

  Future<void> cerrarSesion() async {
    _token = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
    await prefs.remove('usuario');
  }

  Future<Map<String, String>> _headers() async => {
        'Content-Type': 'application/json',
        if (await token != null) 'Authorization': 'Bearer ${await token}',
      };

  /// HU-01: login. La sesión persiste en el dispositivo (acceso sin red luego).
  /// El acceso desde la app es por DNI y el grupo de rol elegido: el DNI no
  /// cambia aunque el operador cambie de número de celular.
  Future<Map<String, dynamic>> login(
    String dni,
    String clave, {
    required String grupoRol,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'dni': dni, 'clave': clave, 'grupo_rol': grupoRol}),
    );
    if (res.statusCode != 200) {
      throw ApiException(_detalle(res.body, 'Credenciales incorrectas'));
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    await _guardarSesion(data['access_token'] as String,
        data['usuario'] as Map<String, dynamic>);
    return data;
  }

  /// HU-12: sincroniza un lote de mediciones (deduplicación por UUID).
  Future<Map<String, dynamic>> sync(List<Map<String, dynamic>> mediciones) async {
    final res = await http.post(
      Uri.parse('$baseUrl/sync'),
      headers: await _headers(),
      body: jsonEncode({'mediciones': mediciones}),
    );
    if (res.statusCode != 200) {
      throw ApiException(_detalle(res.body, 'Error de sincronización'));
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Vinculación del tablero web: informa que este dispositivo leyó el código.
  /// Devuelve el nombre del usuario con el que se iniciará la sesión.
  Future<String?> qrEscanear(String token) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/qr/$token/escanear'),
      headers: await _headers(),
    );
    if (res.statusCode != 200) {
      throw ApiException(_detalle(res.body, 'El código no es válido o ya expiró'));
    }
    return (jsonDecode(res.body) as Map<String, dynamic>)['usuario_nombres'] as String?;
  }

  /// Confirma o cancela la vinculación del tablero web.
  Future<String> qrConfirmar(String token, {required bool aprobar}) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/qr/$token/confirmar'),
      headers: await _headers(),
      body: jsonEncode({'aprobar': aprobar}),
    );
    if (res.statusCode != 200) {
      throw ApiException(_detalle(res.body, 'No se pudo confirmar la vinculación'));
    }
    return ((jsonDecode(res.body) as Map<String, dynamic>)['estado'] ?? '') as String;
  }

  /// Resumen del distrito para la vista de la ATM.
  Future<Map<String, dynamic>> tablero(int ubigeoId) async {
    final res = await http.get(Uri.parse('$baseUrl/tablero/$ubigeoId'),
        headers: await _headers());
    if (res.statusCode != 200) {
      throw ApiException(_detalle(res.body, 'No se pudo cargar el distrito'));
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Alertas abiertas de la jurisdicción del usuario (el servidor las filtra).
  Future<List<dynamic>> alertasActivas() async {
    final res = await http.get(Uri.parse('$baseUrl/alertas?estado=ACTIVA'),
        headers: await _headers());
    if (res.statusCode != 200) {
      throw ApiException(_detalle(res.body, 'No se pudieron cargar las alertas'));
    }
    return jsonDecode(res.body) as List<dynamic>;
  }

  /// Estado del agua de una comunidad en lenguaje llano (vista de población).
  Future<Map<String, dynamic>> estadoPublico(int comunidadId) async {
    final res = await http.get(
        Uri.parse('$baseUrl/publico/comunidad/$comunidadId/estado'),
        headers: await _headers());
    if (res.statusCode != 200) {
      throw ApiException(_detalle(res.body, 'No se pudo consultar el estado'));
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Solicita el código de recuperación; el servidor lo envía por SMS.
  Future<Map<String, dynamic>> solicitarRecuperacion(String dni) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/recuperacion/solicitar'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'dni': dni}),
    );
    if (res.statusCode != 200) {
      throw ApiException(_detalle(res.body, 'No se pudo enviar el código'));
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Confirma el código recibido y establece la clave nueva.
  Future<void> confirmarRecuperacion(
      String dni, String codigo, String claveNueva) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/recuperacion/confirmar'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'dni': dni, 'codigo': codigo, 'clave_nueva': claveNueva}),
    );
    if (res.statusCode != 200) {
      throw ApiException(_detalle(res.body, 'No se pudo cambiar la clave'));
    }
  }

  /// Tableros web vinculados y activos de este usuario.
  Future<List<SesionVinculada>> sesionesVinculadas() async {
    final res = await http.get(
      Uri.parse('$baseUrl/auth/qr/sesiones/activas'),
      headers: await _headers(),
    );
    if (res.statusCode != 200) {
      throw ApiException(_detalle(res.body, 'No se pudieron cargar las sesiones'));
    }
    return (jsonDecode(res.body) as List)
        .map((e) => SesionVinculada.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Cierra un tablero web vinculado: su acceso caduca de inmediato.
  Future<void> cerrarSesionVinculada(int sesionId) async {
    final res = await http.delete(
      Uri.parse('$baseUrl/auth/qr/sesiones/activas/$sesionId'),
      headers: await _headers(),
    );
    if (res.statusCode != 200) {
      throw ApiException(_detalle(res.body, 'No se pudo cerrar la sesión'));
    }
  }

  /// Cierra todos los tableros web vinculados. Devuelve cuántos se cerraron.
  Future<int> cerrarTodasLasSesiones() async {
    final res = await http.delete(
      Uri.parse('$baseUrl/auth/qr/sesiones/activas'),
      headers: await _headers(),
    );
    if (res.statusCode != 200) {
      throw ApiException(_detalle(res.body, 'No se pudieron cerrar las sesiones'));
    }
    return ((jsonDecode(res.body) as Map<String, dynamic>)['cerradas'] ?? 0) as int;
  }

  /// HU-08 (2ª fase): sube la foto de evidencia de una medición ya sincronizada.
  Future<void> subirEvidencia(
    String uuidMedicion,
    String rutaFoto, {
    double? latitud,
    double? longitud,
  }) async {
    final req = http.MultipartRequest(
      'POST', Uri.parse('$baseUrl/mediciones/$uuidMedicion/evidencia'),
    );
    final t = await token;
    if (t != null) req.headers['Authorization'] = 'Bearer $t';
    if (latitud != null) req.fields['latitud'] = latitud.toString();
    if (longitud != null) req.fields['longitud'] = longitud.toString();
    req.files.add(await http.MultipartFile.fromPath('archivo', rutaFoto));

    final streamed = await req.send();
    if (streamed.statusCode >= 300) {
      final body = await streamed.stream.bytesToString();
      throw ApiException(_detalle(body, 'Error subiendo la evidencia'));
    }
  }

  /// HU-11: canal SMS estructurado (para pasarela / modo degradado).
  Future<void> enviarSms(String texto) async {
    final res = await http.post(
      Uri.parse('$baseUrl/sync/sms'),
      headers: await _headers(),
      body: jsonEncode({'texto': texto}),
    );
    if (res.statusCode != 200) {
      throw ApiException(_detalle(res.body, 'Error enviando SMS'));
    }
  }

  String _detalle(String body, String fallback) {
    try {
      final d = jsonDecode(body);
      return d is Map && d['detail'] != null ? d['detail'].toString() : fallback;
    } catch (_) {
      return fallback;
    }
  }
}

class ApiException implements Exception {
  final String mensaje;
  ApiException(this.mensaje);
  @override
  String toString() => mensaje;
}

/// Tablero web vinculado a esta cuenta mediante código QR.
class SesionVinculada {
  final int sesionId;
  final String dispositivo;
  final String? ipOrigen;
  final DateTime vinculadoEn;
  final bool esSesionActual;

  const SesionVinculada({
    required this.sesionId,
    required this.dispositivo,
    required this.vinculadoEn,
    this.ipOrigen,
    this.esSesionActual = false,
  });

  factory SesionVinculada.fromJson(Map<String, dynamic> j) => SesionVinculada(
        sesionId: j['sesion_id'] as int,
        dispositivo: (j['dispositivo'] ?? 'Equipo desconocido') as String,
        ipOrigen: j['ip_origen'] as String?,
        vinculadoEn: DateTime.parse(j['vinculado_en'] as String),
        esSesionActual: (j['es_sesion_actual'] ?? false) as bool,
      );
}
