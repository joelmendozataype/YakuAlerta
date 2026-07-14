import 'dart:math' as math;

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;

import '../../core/theme.dart';
import '../../core/vision/dpd_analyzer.dart';

/// HU-05: lectura del comparador DPD por cámara.
///
/// Muestra la vista de cámara con una guía de encuadre para la muestra y la
/// tarjeta de calibración, captura la foto, estima el cloro por análisis HSV y
/// devuelve el valor para que el operador lo confirme o corrija en el registro.
class CamaraDpdScreen extends StatefulWidget {
  const CamaraDpdScreen({super.key});

  @override
  State<CamaraDpdScreen> createState() => _CamaraDpdScreenState();
}

class _CamaraDpdScreenState extends State<CamaraDpdScreen> {
  CameraController? _controller;
  Future<void>? _initFuture;
  bool _procesando = false;
  String? _error;
  DpdResultado? _resultado;

  @override
  void initState() {
    super.initState();
    _initCamara();
  }

  Future<void> _initCamara() async {
    try {
      final camaras = await availableCameras();
      if (camaras.isEmpty) {
        setState(() => _error = 'No se encontró ninguna cámara en el dispositivo.');
        return;
      }
      final trasera = camaras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => camaras.first,
      );
      final controller = CameraController(
        trasera, ResolutionPreset.high, enableAudio: false,
      );
      _controller = controller;
      setState(() => _initFuture = controller.initialize());
      await _initFuture;
      if (mounted) setState(() {});
    } catch (e) {
      setState(() => _error = 'No se pudo abrir la cámara: $e');
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  Future<void> _capturarYAnalizar() async {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized || _procesando) return;
    setState(() { _procesando = true; _error = null; });
    try {
      final foto = await controller.takePicture();
      final bytes = await foto.readAsBytes();
      final imagen = img.decodeImage(bytes);
      if (imagen == null) throw Exception('No se pudo procesar la imagen.');
      final resultado = _analizarRegionCentral(imagen);
      if (mounted) setState(() => _resultado = resultado);
    } catch (e) {
      if (mounted) setState(() => _error = 'Error al analizar: $e');
    } finally {
      if (mounted) setState(() => _procesando = false);
    }
  }

  /// Promedia el color de la región central (la muestra) y estima el cloro.
  DpdResultado _analizarRegionCentral(img.Image imagen) {
    final w = imagen.width, h = imagen.height;
    final lado = (math.min(w, h) * 0.22).round();
    final x0 = (w - lado) ~/ 2;
    final y0 = (h - lado) ~/ 2;

    int rs = 0, gs = 0, bs = 0, n = 0;
    const paso = 3; // submuestreo para velocidad (gama baja)
    for (int y = y0; y < y0 + lado; y += paso) {
      for (int x = x0; x < x0 + lado; x += paso) {
        final p = imagen.getPixel(x, y);
        rs += p.r.toInt();
        gs += p.g.toInt();
        bs += p.b.toInt();
        n++;
      }
    }
    if (n == 0) n = 1;
    return estimarCloro(rs ~/ n, gs ~/ n, bs ~/ n);
  }

  void _usarValor() => Navigator.pop(context, _resultado?.cloroEstimado);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        title: const Text('Leer DPD con la cámara'),
      ),
      body: _error != null
          ? _vistaError()
          : _resultado != null
              ? _vistaResultado(_resultado!)
              : _vistaCamara(),
    );
  }

  Widget _vistaCamara() {
    final controller = _controller;
    if (controller == null || _initFuture == null) {
      return const Center(child: CircularProgressIndicator(color: Colors.white));
    }
    return FutureBuilder<void>(
      future: _initFuture,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator(color: Colors.white));
        }
        return Stack(
          alignment: Alignment.center,
          children: [
            Positioned.fill(child: CameraPreview(controller)),
            // Guía de encuadre de la muestra + tarjeta de calibración
            _GuiaEncuadre(),
            Positioned(
              bottom: 32,
              child: Column(
                children: [
                  const Text(
                    'Centra la muestra en el recuadro,\njunto a la tarjeta de calibración',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.white, fontSize: 14),
                  ),
                  const SizedBox(height: 16),
                  GestureDetector(
                    onTap: _procesando ? null : _capturarYAnalizar,
                    child: Container(
                      width: 74, height: 74,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.white,
                        border: Border.all(color: YakuColors.agua, width: 4),
                      ),
                      child: _procesando
                          ? const Padding(
                              padding: EdgeInsets.all(18),
                              child: CircularProgressIndicator(strokeWidth: 3))
                          : const Icon(Icons.camera, color: YakuColors.agua, size: 34),
                    ),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _vistaResultado(DpdResultado r) {
    final color = YakuColors.deNivel(r.nivelEstimado);
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(YakuColors.iconoNivel(r.nivelEstimado), color: color, size: 64),
            const SizedBox(height: 16),
            const Text('Cloro estimado',
                style: TextStyle(color: Colors.white70, fontSize: 16)),
            Text('${r.cloroEstimado.toStringAsFixed(2)} mg/L',
                style: TextStyle(
                    color: color, fontSize: 44, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            // Barra de confianza
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(r.confiable ? Icons.verified : Icons.help_outline,
                    color: r.confiable ? YakuColors.verde : Colors.orange, size: 18),
                const SizedBox(width: 6),
                Text('Confianza ${(r.confianza * 100).round()}%',
                    style: const TextStyle(color: Colors.white70)),
              ],
            ),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white10,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Text(
                '⚠️ La cámara solo asiste. Verifica el color contra el comparador '
                'y confirma o corrige el valor antes de guardar.',
                style: TextStyle(color: Colors.white70, fontSize: 13),
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(height: 28),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _usarValor,
                icon: const Icon(Icons.check),
                label: Text('Usar ${r.cloroEstimado.toStringAsFixed(2)} mg/L'),
              ),
            ),
            const SizedBox(height: 10),
            TextButton(
              onPressed: () => setState(() => _resultado = null),
              child: const Text('Reintentar captura',
                  style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _vistaError() {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.no_photography, color: Colors.white54, size: 56),
            const SizedBox(height: 16),
            Text(_error ?? 'Error de cámara',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white70)),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Ingresar el cloro manualmente'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Overlay con el recuadro de encuadre de la muestra.
class _GuiaEncuadre extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 150, height: 150,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.white, width: 3),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Center(
                child: Text('muestra',
                    style: TextStyle(color: Colors.white70, fontSize: 12)),
              ),
            ),
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.black45,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Text('tarjeta de calibración abajo',
                  style: TextStyle(color: Colors.white70, fontSize: 11)),
            ),
          ],
        ),
      ),
    );
  }
}
