import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../../core/db/local_db.dart';
import '../../core/models/medicion.dart';
import '../../core/models/reservorio.dart';
import '../../core/rules/motor_riesgo.dart';
import '../../core/theme.dart';
import 'resultado_screen.dart';

/// HU-02: registro offline de medición (flujo lineal de pocos pasos, RNF-02).
class RegistroScreen extends StatefulWidget {
  final Reservorio reservorio;
  const RegistroScreen({super.key, required this.reservorio});
  @override
  State<RegistroScreen> createState() => _RegistroScreenState();
}

class _RegistroScreenState extends State<RegistroScreen> {
  final _cloro = TextEditingController();
  final _turbidez = TextEditingController();
  final _obs = TextEditingController();
  String _metodo = 'MANUAL';
  bool _guardando = false;

  static const cloroMaxFisico = 20.0;
  static const turbidezMaxFisica = 1000.0;

  double? get _cloroVal => double.tryParse(_cloro.text.replaceAll(',', '.'));
  double? get _turbVal => double.tryParse(_turbidez.text.replaceAll(',', '.'));

  /// Validación de rangos físicos (previene errores de digitación, CA-HU02-02).
  String? _validarRangos() {
    final c = _cloroVal, t = _turbVal;
    if (_cloro.text.isNotEmpty && c == null) return 'El cloro no es un número válido.';
    if (_turbidez.text.isNotEmpty && t == null) return 'La turbidez no es un número válido.';
    if (c != null && (c < 0 || c > cloroMaxFisico)) {
      return 'Cloro $c mg/L fuera de rango físico (0–$cloroMaxFisico). Verifica la lectura.';
    }
    if (t != null && (t < 0 || t > turbidezMaxFisica)) {
      return 'Turbidez $t UNT fuera de rango físico. Verifica la lectura.';
    }
    if (c == null && t == null) return 'Ingresa al menos el cloro o la turbidez.';
    return null;
  }

  Future<void> _confirmar() async {
    final error = _validarRangos();
    if (error != null) {
      _mostrarDialogoVerificacion(error);
      return;
    }
    setState(() => _guardando = true);

    // Clasificación LOCAL con el motor de reglas (sin internet, RNF-04).
    final resultado = clasificar(
      cloroMgL: _cloroVal,
      turbidezUnt: _turbVal,
      observaciones: _obs.text,
    );
    final reco = calcularDosis(
      nivel: resultado.nivel,
      volumenM3: widget.reservorio.volumenM3,
      cloroMedido: _cloroVal,
    );

    final medicion = Medicion(
      uuidRegistro: const Uuid().v4(),
      reservorioId: widget.reservorio.reservorioId,
      fechaHora: DateTime.now(),
      cloroMgL: _cloroVal,
      turbidezUnt: _turbVal,
      metodoCloro: _metodo,
      observaciones: _obs.text.isEmpty ? null : _obs.text,
      nivel: resultado.nivel,
    );
    await LocalDb.instance.guardarMedicion(medicion);

    if (!mounted) return;
    setState(() => _guardando = false);
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => ResultadoScreen(
          medicion: medicion,
          reservorio: widget.reservorio,
          resultado: resultado,
          recomendacion: reco,
        ),
      ),
    );
  }

  void _mostrarDialogoVerificacion(String mensaje) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        icon: const Icon(Icons.warning_amber_rounded, color: Colors.orange, size: 40),
        title: const Text('Verifica la lectura'),
        content: Text(mensaje),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Corregir')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Medir · ${widget.reservorio.codigo}')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _paso(1, 'Cloro residual libre'),
          TextField(
            controller: _cloro,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            style: const TextStyle(fontSize: 22),
            decoration: const InputDecoration(hintText: '0.00', suffixText: 'mg/L'),
          ),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: () {
                // HU-05: lectura por cámara del comparador DPD (estructura lista).
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                  content: Text('Lectura por cámara DPD (HU-05): módulo de visión HSV en integración.')));
                setState(() => _metodo = 'MANUAL');
              },
              icon: const Icon(Icons.camera_alt_outlined),
              label: const Text('Leer con la cámara (DPD)'),
            ),
          ),
          const SizedBox(height: 16),
          _paso(2, 'Turbidez'),
          TextField(
            controller: _turbidez,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            style: const TextStyle(fontSize: 22),
            decoration: const InputDecoration(hintText: '0.0', suffixText: 'UNT'),
          ),
          const SizedBox(height: 16),
          _paso(3, 'Observaciones sanitarias'),
          TextField(
            controller: _obs,
            maxLines: 3,
            decoration: const InputDecoration(
              hintText: 'Color, olor, presencia de turbidez, estado del reservorio…',
            ),
          ),
          const SizedBox(height: 28),
          ElevatedButton.icon(
            onPressed: _guardando ? null : _confirmar,
            icon: _guardando
                ? const SizedBox(height: 22, width: 22,
                    child: CircularProgressIndicator(color: Colors.white, strokeWidth: 3))
                : const Icon(Icons.check),
            label: const Text('Confirmar y ver semáforo'),
          ),
          const SizedBox(height: 8),
          const Text(
            'La medición se guarda en el dispositivo y se clasifica al instante, con o sin internet.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.black54, fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _paso(int n, String titulo) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          children: [
            CircleAvatar(
              radius: 14,
              backgroundColor: YakuColors.agua,
              child: Text('$n', style: const TextStyle(color: Colors.white, fontSize: 13)),
            ),
            const SizedBox(width: 10),
            Text(titulo, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          ],
        ),
      );
}
