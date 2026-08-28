import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../core/api/api_client.dart';
import '../../core/theme.dart';

/// Vinculación del tablero web mediante código QR.
///
/// Réplica del patrón de WhatsApp/Discord Web: la app —que ya tiene sesión—
/// escanea el código mostrado en la web y **el usuario confirma de forma
/// explícita** antes de conceder el acceso. La confirmación es la defensa
/// contra códigos QR enviados por terceros.
class EscanerQrScreen extends StatefulWidget {
  const EscanerQrScreen({super.key});

  @override
  State<EscanerQrScreen> createState() => _EscanerQrScreenState();
}

enum _Fase { escaneando, confirmando, enviando, listo, error }

class _EscanerQrScreenState extends State<EscanerQrScreen> {
  static const _prefijo = 'YAKU-QR:';

  final _controller = MobileScannerController(
    detectionSpeed: DetectionSpeed.noDuplicates,
    formats: const [BarcodeFormat.qrCode],
  );
  final _api = ApiClient.instance;

  _Fase _fase = _Fase.escaneando;
  String? _token;
  String? _usuario;
  String _mensaje = '';

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _onDeteccion(BarcodeCapture captura) async {
    if (_fase != _Fase.escaneando) return;
    final valor = captura.barcodes.firstOrNull?.rawValue;
    if (valor == null) return;

    // Solo aceptamos códigos propios: evita procesar QR de cualquier origen.
    if (!valor.startsWith(_prefijo)) {
      setState(() {
        _fase = _Fase.error;
        _mensaje = 'Ese código no pertenece a Yakuni.';
      });
      return;
    }

    final token = valor.substring(_prefijo.length);
    setState(() => _fase = _Fase.confirmando);
    await _controller.stop();

    try {
      final nombres = await _api.qrEscanear(token);
      if (!mounted) return;
      setState(() {
        _token = token;
        _usuario = nombres;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _fase = _Fase.error;
        _mensaje = e.mensaje;
      });
    }
  }

  Future<void> _resolver(bool aprobar) async {
    if (_token == null) return;
    setState(() => _fase = _Fase.enviando);
    try {
      await _api.qrConfirmar(_token!, aprobar: aprobar);
      if (!mounted) return;
      setState(() {
        _fase = _Fase.listo;
        _mensaje = aprobar
            ? 'Tablero web vinculado. Ya puedes usarlo en la computadora.'
            : 'Acceso cancelado. No se abrió ninguna sesión.';
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _fase = _Fase.error;
        _mensaje = e.mensaje;
      });
    }
  }

  Future<void> _reintentar() async {
    setState(() {
      _fase = _Fase.escaneando;
      _token = null;
      _usuario = null;
      _mensaje = '';
    });
    await _controller.start();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        title: const Text('Vincular tablero web'),
      ),
      body: switch (_fase) {
        _Fase.escaneando => _vistaEscaner(),
        _Fase.confirmando || _Fase.enviando => _vistaConfirmacion(),
        _Fase.listo => _vistaFinal(exito: true),
        _Fase.error => _vistaFinal(exito: false),
      },
    );
  }

  Widget _vistaEscaner() {
    return Stack(
      alignment: Alignment.center,
      children: [
        Positioned.fill(
          child: MobileScanner(controller: _controller, onDetect: _onDeteccion),
        ),
        // Marco de puntería
        IgnorePointer(
          child: Container(
            width: 230,
            height: 230,
            decoration: BoxDecoration(
              border: Border.all(color: YakuColors.agua, width: 3),
              borderRadius: BorderRadius.circular(20),
            ),
          ),
        ),
        Positioned(
          bottom: 48,
          left: 24,
          right: 24,
          child: Text(
            'Apunta al código QR que aparece\nen el tablero web de Yakuni',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 15),
          ),
        ),
      ],
    );
  }

  Widget _vistaConfirmacion() {
    final enviando = _fase == _Fase.enviando;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.desktop_windows_outlined,
                color: YakuColors.agua, size: 64),
            const SizedBox(height: 20),
            const Text('¿Iniciar sesión en el tablero web?',
                textAlign: TextAlign.center,
                style: TextStyle(
                    color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            if (_usuario != null)
              Text('Se abrirá con tu cuenta: $_usuario',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white70, fontSize: 15)),
            const SizedBox(height: 24),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.orange.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.warning_amber_rounded, color: Colors.orange, size: 22),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Confirma solo si tú estás frente a esa computadora. '
                      'Nunca escanees un código que te haya enviado otra persona.',
                      style: TextStyle(color: Colors.white70, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 28),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: enviando ? null : () => _resolver(true),
                icon: enviando
                    ? const SizedBox(
                        width: 18, height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.check),
                label: Text(enviando ? 'Confirmando…' : 'Sí, soy yo'),
              ),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: enviando ? null : () => _resolver(false),
              child: const Text('Cancelar', style: TextStyle(color: Colors.white70)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _vistaFinal({required bool exito}) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(exito ? Icons.check_circle : Icons.error_outline,
                color: exito ? YakuColors.verde : Colors.orange, size: 72),
            const SizedBox(height: 20),
            Text(_mensaje,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white, fontSize: 17)),
            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Volver'),
              ),
            ),
            if (!exito)
              TextButton(
                onPressed: _reintentar,
                child: const Text('Escanear otro código',
                    style: TextStyle(color: Colors.white70)),
              ),
          ],
        ),
      ),
    );
  }
}
