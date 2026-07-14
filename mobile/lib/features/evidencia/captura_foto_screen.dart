import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../../core/theme.dart';

/// Captura simple de una foto; devuelve la ruta del archivo (o null).
/// Se usa para la evidencia fotográfica del reservorio/muestra (HU-08).
class CapturaFotoScreen extends StatefulWidget {
  final String titulo;
  const CapturaFotoScreen({super.key, this.titulo = 'Foto de evidencia'});

  @override
  State<CapturaFotoScreen> createState() => _CapturaFotoScreenState();
}

class _CapturaFotoScreenState extends State<CapturaFotoScreen> {
  CameraController? _controller;
  Future<void>? _initFuture;
  bool _capturando = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    try {
      final camaras = await availableCameras();
      if (camaras.isEmpty) {
        setState(() => _error = 'No hay cámara disponible.');
        return;
      }
      final trasera = camaras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => camaras.first,
      );
      final c = CameraController(trasera, ResolutionPreset.high, enableAudio: false);
      _controller = c;
      setState(() => _initFuture = c.initialize());
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

  Future<void> _capturar() async {
    final c = _controller;
    if (c == null || !c.value.isInitialized || _capturando) return;
    setState(() => _capturando = true);
    try {
      final foto = await c.takePicture();
      if (mounted) Navigator.pop(context, foto.path);
    } catch (e) {
      if (mounted) setState(() { _error = 'Error al capturar: $e'; _capturando = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(backgroundColor: Colors.black, title: Text(widget.titulo)),
      body: _error != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(_error!,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.white70)),
              ),
            )
          : (_controller == null || _initFuture == null)
              ? const Center(child: CircularProgressIndicator(color: Colors.white))
              : FutureBuilder<void>(
                  future: _initFuture,
                  builder: (context, snap) {
                    if (snap.connectionState != ConnectionState.done) {
                      return const Center(
                          child: CircularProgressIndicator(color: Colors.white));
                    }
                    return Stack(
                      alignment: Alignment.bottomCenter,
                      children: [
                        Positioned.fill(child: CameraPreview(_controller!)),
                        Padding(
                          padding: const EdgeInsets.only(bottom: 32),
                          child: GestureDetector(
                            onTap: _capturando ? null : _capturar,
                            child: Container(
                              width: 74, height: 74,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: Colors.white,
                                border: Border.all(color: YakuColors.agua, width: 4),
                              ),
                              child: _capturando
                                  ? const Padding(
                                      padding: EdgeInsets.all(18),
                                      child: CircularProgressIndicator(strokeWidth: 3))
                                  : const Icon(Icons.camera, color: YakuColors.agua, size: 34),
                            ),
                          ),
                        ),
                      ],
                    );
                  },
                ),
    );
  }
}
