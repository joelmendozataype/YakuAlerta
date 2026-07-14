import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/db/local_db.dart';
import '../../core/models/medicion.dart';
import '../../core/models/reservorio.dart';
import '../../core/rules/motor_riesgo.dart';
import '../../core/sync/sync_service.dart';
import '../../core/theme.dart';

/// HU-03 + HU-06: semáforo del agua y recomendación de acción con dosis.
class ResultadoScreen extends StatefulWidget {
  final Medicion medicion;
  final Reservorio reservorio;
  final ResultadoClasificacion resultado;
  final Recomendacion? recomendacion;

  const ResultadoScreen({
    super.key,
    required this.medicion,
    required this.reservorio,
    required this.resultado,
    required this.recomendacion,
  });

  @override
  State<ResultadoScreen> createState() => _ResultadoScreenState();
}

class _ResultadoScreenState extends State<ResultadoScreen> {
  bool _procesando = false;

  NivelRiesgo get _nivel => widget.resultado.nivel;
  Color get _color => YakuColors.deNivel(_nivel);

  Future<void> _sincronizarOSms() async {
    setState(() => _procesando = true);
    final r = await SyncService.instance.sincronizar();
    if (!mounted) return;
    setState(() => _procesando = false);
    if (r != null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Enviado. ${r.alertas} alerta(s) generada(s).'),
        backgroundColor: YakuColors.verde));
    } else {
      _enviarSms();
    }
  }

  /// HU-11: canal SMS estructurado de respaldo cuando no hay internet.
  Future<void> _enviarSms() async {
    final texto = widget.medicion.toSms(widget.reservorio.codigo);
    try {
      await ApiClient.instance.enviarSms(texto);
      await LocalDb.instance.marcarEstado(widget.medicion.uuidRegistro, EstadoSync.enviadoSms);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Enviado por SMS estructurado (modo sin datos).')));
    } catch (_) {
      if (!mounted) return;
      showDialog(context: context, builder: (_) => AlertDialog(
        title: const Text('SMS de respaldo'),
        content: SelectableText(
          'Sin conexión de datos. Envía este SMS a la pasarela YakuAlerta:\n\n$texto'),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Entendido'))],
      ));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Resultado'), backgroundColor: _color),
      body: ListView(
        children: [
          // Semáforo grande
          Container(
            width: double.infinity,
            color: _color,
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
            child: Column(
              children: [
                Icon(YakuColors.iconoNivel(_nivel), color: Colors.white, size: 72),
                const SizedBox(height: 12),
                Text(_nivel.etiqueta.toUpperCase(),
                    style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Text('${widget.reservorio.codigo} · '
                    'Cloro ${widget.medicion.cloroMgL ?? "—"} mg/L · '
                    'Turb ${widget.medicion.turbidezUnt ?? "—"} UNT',
                    style: const TextStyle(color: Colors.white70)),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Motivos de la clasificación
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('¿Por qué este resultado?',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                        const SizedBox(height: 8),
                        ...widget.resultado.motivos.map((m) => Padding(
                              padding: const EdgeInsets.only(bottom: 4),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('• '),
                                  Expanded(child: Text(m)),
                                ],
                              ),
                            )),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                // Bloque "Qué hacer ahora" (HU-06)
                if (widget.recomendacion != null) _bloqueRecomendacion(),
                if (widget.recomendacion == null)
                  Card(
                    color: YakuColors.verde.withOpacity(0.08),
                    child: const Padding(
                      padding: EdgeInsets.all(16),
                      child: Text('Agua segura. Continúa tu vigilancia semanal habitual.',
                          style: TextStyle(fontSize: 16)),
                    ),
                  ),

                const SizedBox(height: 24),
                ElevatedButton.icon(
                  onPressed: _procesando ? null : _sincronizarOSms,
                  icon: const Icon(Icons.send),
                  label: Text(_nivel.esAlerta ? 'Enviar alerta' : 'Sincronizar'),
                ),
                const SizedBox(height: 8),
                OutlinedButton(
                  onPressed: () => Navigator.pop(context),
                  style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                  child: const Text('Volver al inicio'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _bloqueRecomendacion() {
    final r = widget.recomendacion!;
    return Card(
      color: _color.withOpacity(0.06),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.medical_services_outlined, color: _color),
                const SizedBox(width: 8),
                const Text('Qué hacer ahora',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
              ],
            ),
            const SizedBox(height: 12),
            // Dosis como dato accionable principal
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: _color,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  const Text('Dosis de recloración',
                      style: TextStyle(color: Colors.white70)),
                  Text('${r.gramosHipoclorito} g',
                      style: const TextStyle(
                          color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold)),
                  Text('Hipoclorito al ${r.concentracion.toStringAsFixed(0)}% · '
                      'Remedir en ${r.plazoHoras} h',
                      style: const TextStyle(color: Colors.white70)),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Text(r.protocolo, style: const TextStyle(fontSize: 15, height: 1.4)),
          ],
        ),
      ),
    );
  }
}
