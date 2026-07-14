import 'dart:io';

import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../../core/db/local_db.dart';
import '../../core/evidencia/evidencia_service.dart';
import '../../core/models/medicion.dart';
import '../../core/models/reservorio.dart';
import '../../core/notificaciones/recordatorio_service.dart';
import '../../core/rules/motor_riesgo.dart';
import '../../core/theme.dart';
import '../camara_dpd/camara_dpd_screen.dart';
import '../evidencia/captura_foto_screen.dart';
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

  // Evidencia fotográfica georreferenciada (HU-08)
  String? _rutaFoto;
  double? _lat, _lon;
  bool _adjuntando = false;

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

  /// HU-05: abre la cámara, estima el cloro del comparador DPD y lo trae al
  /// formulario para confirmación/corrección (marca el método CAMARA_DPD).
  Future<void> _leerConCamara() async {
    final estimado = await Navigator.push<double?>(
      context,
      MaterialPageRoute(builder: (_) => const CamaraDpdScreen()),
    );
    if (estimado != null) {
      setState(() {
        _cloro.text = estimado.toStringAsFixed(2);
        _metodo = 'CAMARA_DPD';
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Valor estimado por cámara. Verifícalo o corrígelo antes de guardar.'),
        ));
      }
    }
  }

  /// HU-08: captura una foto de evidencia, la comprime (RNF-03) y toma la
  /// ubicación GPS solo en ese momento (RNF-08).
  Future<void> _adjuntarEvidencia() async {
    final ruta = await Navigator.push<String?>(
      context,
      MaterialPageRoute(builder: (_) => const CapturaFotoScreen()),
    );
    if (ruta == null) return;
    setState(() => _adjuntando = true);
    try {
      final comprimida = await EvidenciaService.instance.comprimirYGuardar(ruta);
      final pos = await EvidenciaService.instance.ubicacionActual();
      setState(() {
        _rutaFoto = comprimida;
        _lat = pos?.latitude;
        _lon = pos?.longitude;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No se pudo adjuntar la evidencia: $e')));
      }
    } finally {
      if (mounted) setState(() => _adjuntando = false);
    }
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
      rutaFoto: _rutaFoto,
      latitud: _lat,
      longitud: _lon,
    );
    await LocalDb.instance.guardarMedicion(medicion);

    // HU-07: reprograma el recordatorio de la próxima medición semanal.
    RecordatorioService.instance.programarSemanal(
      widget.reservorio.reservorioId, widget.reservorio.codigo);

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
              onPressed: _leerConCamara,
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
          const SizedBox(height: 20),
          _paso(4, 'Evidencia (opcional)'),
          _seccionEvidencia(),
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

  Widget _seccionEvidencia() {
    if (_adjuntando) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 12),
        child: Row(children: [
          SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
          SizedBox(width: 12), Text('Comprimiendo y ubicando…'),
        ]),
      );
    }
    if (_rutaFoto != null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Row(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.file(File(_rutaFoto!), width: 64, height: 64, fit: BoxFit.cover),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Foto adjunta', style: TextStyle(fontWeight: FontWeight.w600)),
                    Text(
                      _lat != null
                          ? '📍 ${_lat!.toStringAsFixed(5)}, ${_lon!.toStringAsFixed(5)}'
                          : 'Sin ubicación GPS',
                      style: const TextStyle(fontSize: 12, color: Colors.black54),
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.delete_outline, color: YakuColors.rojo),
                onPressed: () => setState(() { _rutaFoto = null; _lat = null; _lon = null; }),
              ),
            ],
          ),
        ),
      );
    }
    return Align(
      alignment: Alignment.centerLeft,
      child: OutlinedButton.icon(
        onPressed: _adjuntarEvidencia,
        icon: const Icon(Icons.add_a_photo_outlined),
        label: const Text('Adjuntar foto georreferenciada'),
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
