import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest_all.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

/// Recordatorios de la medición semanal — HU-07 / RF-16.
///
/// Notificación local programada en el dispositivo, **sin internet**
/// (flutter_local_notifications). Recuerda al operador su vigilancia semanal.
class RecordatorioService {
  RecordatorioService._();
  static final RecordatorioService instance = RecordatorioService._();

  final _plugin = FlutterLocalNotificationsPlugin();
  bool _inicializado = false;

  static const _canal = AndroidNotificationDetails(
    'recordatorios_medicion',
    'Recordatorios de medición',
    channelDescription: 'Avisos de la vigilancia semanal del agua',
    importance: Importance.high,
    priority: Priority.high,
  );

  Future<void> inicializar() async {
    if (_inicializado) return;
    tz.initializeTimeZones();
    tz.setLocalLocation(tz.getLocation('America/Lima'));

    const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
    await _plugin.initialize(const InitializationSettings(android: androidInit));

    // Android 13+: solicitar permiso de notificaciones (POST_NOTIFICATIONS).
    await _plugin
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();
    _inicializado = true;
  }

  /// Programa el recordatorio semanal (por defecto, próximos 7 días a las 08:00).
  Future<void> programarSemanal(int reservorioId, String codigoReservorio,
      {int diasDesdeHoy = 7, int hora = 8}) async {
    await inicializar();
    final cuando = _proximaFecha(diasDesdeHoy, hora);
    await _plugin.zonedSchedule(
      reservorioId, // id único por reservorio
      'Yakuni — Medición semanal',
      'Te toca medir el cloro y la turbidez del reservorio $codigoReservorio.',
      cuando,
      const NotificationDetails(android: _canal),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
      matchDateTimeComponents: DateTimeComponents.dayOfWeekAndTime,
    );
  }

  /// Notificación inmediata (útil para confirmar al operador que quedó programado).
  Future<void> avisoInmediato(String titulo, String cuerpo) async {
    await inicializar();
    await _plugin.show(0, titulo, cuerpo, const NotificationDetails(android: _canal));
  }

  Future<void> cancelar(int reservorioId) async {
    await _plugin.cancel(reservorioId);
  }

  tz.TZDateTime _proximaFecha(int diasDesdeHoy, int hora) {
    final ahora = tz.TZDateTime.now(tz.local);
    var fecha = tz.TZDateTime(tz.local, ahora.year, ahora.month, ahora.day, hora)
        .add(Duration(days: diasDesdeHoy));
    if (fecha.isBefore(ahora)) fecha = fecha.add(const Duration(days: 7));
    return fecha;
  }
}
