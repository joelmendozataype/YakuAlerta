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
  Future<Map<String, dynamic>> login(String telefono, String clave) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'telefono': telefono, 'clave': clave}),
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
