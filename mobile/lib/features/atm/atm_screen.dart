import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api/api_client.dart';
import '../../core/theme.dart';
import '../comun/marco_rol.dart';

/// Vista del responsable de la ATM (y de la autoridad local).
///
/// Su función es **supervisar**, no medir: ve el estado de las comunidades de
/// su distrito, las alertas abiertas y dónde falta información. El cierre de
/// alertas y los reportes siguen en el tablero web, que es donde se hace.
class AtmScreen extends StatefulWidget {
  const AtmScreen({super.key});

  @override
  State<AtmScreen> createState() => _AtmScreenState();
}

class _AtmScreenState extends State<AtmScreen> {
  final _api = ApiClient.instance;
  Map<String, dynamic>? _resumen;
  List<dynamic> _alertas = [];
  String? _nombre;
  bool _cargando = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    setState(() { _cargando = true; _error = null; });
    try {
      final u = await _api.usuarioCacheado();
      final ubigeo = u?['ubigeo_id'] as int?;
      final resumen = ubigeo != null ? await _api.tablero(ubigeo) : null;
      final alertas = await _api.alertasActivas();
      if (!mounted) return;
      setState(() {
        _nombre = u?['nombres'] as String?;
        _resumen = resumen;
        _alertas = alertas;
        _cargando = false;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() { _error = e.mensaje; _cargando = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return MarcoRol(
      titulo: 'Supervisión ATM',
      subtitulo: _nombre,
      alRecargar: _cargar,
      hijo: _cargando
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? MensajeVacio(icono: Icons.wifi_off, texto: _error!)
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    if (_resumen != null) ...[
                      Text('Distrito de ${_resumen!['distrito']}',
                          style: const TextStyle(
                              fontSize: 18, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 12),
                      _indicadores(),
                      const SizedBox(height: 22),
                      const Text('Comunidades',
                          style: TextStyle(fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      ...(_resumen!['comunidades'] as List).map(_filaComunidad),
                    ],
                    const SizedBox(height: 22),
                    Text('Alertas abiertas (${_alertas.length})',
                        style: const TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    if (_alertas.isEmpty)
                      const Card(
                        child: ListTile(
                          leading: Icon(Icons.check_circle, color: YakuColors.verde),
                          title: Text('Ninguna alerta abierta'),
                          subtitle: Text('Todas las comunidades están atendidas.'),
                        ),
                      )
                    else
                      ..._alertas.map(_filaAlerta),
                    const SizedBox(height: 24),
                    const Text(
                      'El cierre de alertas y los reportes de vigilancia se '
                      'realizan en el tablero web.',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 12, color: Colors.black45),
                    ),
                  ],
                ),
    );
  }

  Widget _indicadores() {
    final r = _resumen!;
    return Row(
      children: [
        Expanded(child: TarjetaDato(
            valor: '${r['sistemas_monitoreados']}',
            etiqueta: 'Sistemas', color: YakuColors.agua,
            icono: Icons.water_drop_outlined)),
        const SizedBox(width: 8),
        Expanded(child: TarjetaDato(
            valor: '${r['porcentaje_agua_segura']}%',
            etiqueta: 'Agua segura', color: YakuColors.verde,
            icono: Icons.verified_outlined)),
        const SizedBox(width: 8),
        Expanded(child: TarjetaDato(
            valor: '${r['alertas_activas']}',
            etiqueta: 'Alertas', color: YakuColors.rojo,
            icono: Icons.notifications_active_outlined)),
        const SizedBox(width: 8),
        Expanded(child: TarjetaDato(
            valor: '${r['reservorios_en_silencio']}',
            etiqueta: 'Sin medir', color: YakuColors.amarillo,
            icono: Icons.schedule)),
      ],
    );
  }

  Widget _filaComunidad(dynamic c) {
    final fecha = c['ultima_medicion'] != null
        ? DateFormat('dd/MM/yyyy').format(DateTime.parse(c['ultima_medicion']).toLocal())
        : 'sin registro';
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        title: Text(c['comunidad'] ?? '—',
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text('${c['reservorio_codigo'] ?? ''} · última: $fecha'),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            EtiquetaNivel(nivel: c['nivel'] as String?),
            if (c['silencio'] == true)
              const Padding(
                padding: EdgeInsets.only(top: 4),
                child: Text('⏰ sin medir',
                    style: TextStyle(fontSize: 11, color: YakuColors.amarillo)),
              ),
          ],
        ),
      ),
    );
  }

  Widget _filaAlerta(dynamic a) {
    final rojo = a['nivel'] == 'ROJO';
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(rojo ? Icons.dangerous : Icons.warning_amber_rounded,
            color: rojo ? YakuColors.rojo : YakuColors.amarillo),
        title: Text('${a['comunidad'] ?? '—'} · ${a['reservorio_codigo'] ?? ''}',
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text('Cloro ${a['cloro_mg_l'] ?? '—'} mg/L · '
            'Turbidez ${a['turbidez_unt'] ?? '—'} UNT'),
        trailing: EtiquetaNivel(nivel: a['nivel'] as String?),
      ),
    );
  }
}
