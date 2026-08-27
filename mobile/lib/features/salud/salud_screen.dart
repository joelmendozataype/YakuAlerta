import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api/api_client.dart';
import '../../core/theme.dart';
import '../comun/marco_rol.dart';

/// Vista del establecimiento de salud (HU-10).
///
/// Su función es **anticipar la vigilancia epidemiológica**: necesita saber qué
/// comunidades de su jurisdicción tienen agua no segura y con qué protocolo
/// sanitario, para prepararse ante posibles casos de EDA.
class SaludScreen extends StatefulWidget {
  const SaludScreen({super.key});

  @override
  State<SaludScreen> createState() => _SaludScreenState();
}

class _SaludScreenState extends State<SaludScreen> {
  final _api = ApiClient.instance;
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
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final u = await _api.usuarioCacheado();
      final alertas = await _api.alertasActivas();
      if (!mounted) return;
      setState(() {
        _nombre = u?['nombres'] as String?;
        // Al personal de salud le importa primero lo rojo.
        _alertas = [
          ...alertas.where((a) => a['nivel'] == 'ROJO'),
          ...alertas.where((a) => a['nivel'] != 'ROJO'),
        ];
        _cargando = false;
      });
    } on ApiException catch (e) {
      if (mounted) {
        setState(() {
          _error = e.mensaje;
          _cargando = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final rojas = _alertas.where((a) => a['nivel'] == 'ROJO').length;
    return MarcoRol(
      titulo: 'Vigilancia sanitaria',
      subtitulo: _nombre,
      alRecargar: _cargar,
      hijo: _cargando
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? MensajeVacio(icono: Icons.wifi_off, texto: _error!)
              : _alertas.isEmpty
                  ? const MensajeVacio(
                      icono: Icons.health_and_safety_outlined,
                      texto: 'No hay alertas de agua no segura en su '
                          'jurisdicción.\nSe le avisará apenas se detecte una.')
                  : ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        _resumen(rojas),
                        const SizedBox(height: 12),
                        ..._alertas.map(_tarjetaAlerta),
                      ],
                    ),
    );
  }

  Widget _resumen(int rojas) {
    final hayRojas = rojas > 0;
    return Card(
      color: (hayRojas ? YakuColors.rojo : YakuColors.verde)
          .withValues(alpha: 0.08),
      child: ListTile(
        leading: Icon(hayRojas ? Icons.priority_high : Icons.check_circle,
            color: hayRojas ? YakuColors.rojo : YakuColors.verde),
        title: Text(
          hayRojas
              ? '$rojas comunidad(es) con agua NO segura'
              : 'Sin agua no segura en su jurisdicción',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: hayRojas
            ? const Text('Anticipe la vigilancia de casos de EDA.')
            : null,
      ),
    );
  }

  Widget _tarjetaAlerta(dynamic a) {
    final rojo = a['nivel'] == 'ROJO';
    final fecha = a['fecha_generacion'] != null
        ? DateFormat('dd/MM/yyyy HH:mm')
            .format(DateTime.parse(a['fecha_generacion']).toLocal())
        : '';
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ExpansionTile(
        leading: Icon(rojo ? Icons.dangerous : Icons.warning_amber_rounded,
            color: rojo ? YakuColors.rojo : YakuColors.amarillo),
        title: Text(a['comunidad'] ?? '—',
            style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text('${a['reservorio_codigo'] ?? ''} · $fecha'),
        trailing: EtiquetaNivel(nivel: a['nivel'] as String?),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
                'Cloro ${a['cloro_mg_l'] ?? '—'} mg/L · '
                'Turbidez ${a['turbidez_unt'] ?? '—'} UNT',
                style: const TextStyle(color: Colors.black54)),
          ),
          const SizedBox(height: 10),
          if (a['protocolo'] != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(a['protocolo'] as String,
                  style: const TextStyle(fontSize: 13.5, height: 1.4)),
            ),
        ],
      ),
    );
  }
}
