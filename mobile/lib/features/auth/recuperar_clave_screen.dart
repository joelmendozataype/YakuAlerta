import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api/api_client.dart';
import '../../core/theme.dart';

/// Recuperación de clave en dos pasos.
///
/// 1. El usuario escribe su DNI y el sistema envía un código por **mensaje de
///    texto** al celular registrado (el canal que funciona sin internet).
/// 2. Con ese código define su clave nueva.
class RecuperarClaveScreen extends StatefulWidget {
  const RecuperarClaveScreen({super.key});

  @override
  State<RecuperarClaveScreen> createState() => _RecuperarClaveScreenState();
}

enum _Paso { pedirDni, ingresarCodigo, listo }

class _RecuperarClaveScreenState extends State<RecuperarClaveScreen> {
  final _dni = TextEditingController();
  final _codigo = TextEditingController();
  final _clave = TextEditingController();
  final _claveRepetida = TextEditingController();

  _Paso _paso = _Paso.pedirDni;
  bool _cargando = false;
  bool _verClave = false;
  String? _error;
  String? _telefono;
  int _vigenciaMin = 10;

  @override
  void dispose() {
    _dni.dispose();
    _codigo.dispose();
    _clave.dispose();
    _claveRepetida.dispose();
    super.dispose();
  }

  Future<void> _solicitar() async {
    if (_dni.text.trim().length != 8) {
      setState(() => _error = 'El DNI debe tener 8 dígitos.');
      return;
    }
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final r = await ApiClient.instance.solicitarRecuperacion(_dni.text.trim());
      if (!mounted) return;
      setState(() {
        _telefono = r['telefono_enmascarado'] as String?;
        _vigenciaMin = (r['vigencia_min'] ?? 10) as int;
        _paso = _Paso.ingresarCodigo;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.mensaje);
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  Future<void> _confirmar() async {
    if (_codigo.text.trim().length != 6) {
      setState(() => _error = 'El código tiene 6 dígitos.');
      return;
    }
    if (_clave.text.length < 6) {
      setState(() => _error = 'La clave nueva debe tener al menos 6 caracteres.');
      return;
    }
    if (_clave.text != _claveRepetida.text) {
      setState(() => _error = 'Las claves no coinciden.');
      return;
    }
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      await ApiClient.instance.confirmarRecuperacion(
          _dni.text.trim(), _codigo.text.trim(), _clave.text);
      if (!mounted) return;
      setState(() => _paso = _Paso.listo);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.mensaje);
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: YakuColors.aguaOscuro,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text('Recuperar mi clave'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Container(
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
            ),
            child: switch (_paso) {
              _Paso.pedirDni => _vistaDni(),
              _Paso.ingresarCodigo => _vistaCodigo(),
              _Paso.listo => _vistaListo(),
            },
          ),
        ),
      ),
    );
  }

  // ── Paso 1 ────────────────────────────────────────────────────
  Widget _vistaDni() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Icon(Icons.lock_reset, size: 48, color: YakuColors.agua),
        const SizedBox(height: 12),
        const Text('Ingresa tu DNI',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 19, fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        const Text(
          'Te enviaremos un código por mensaje de texto al celular '
          'registrado en tu cuenta.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.black54, fontSize: 14),
        ),
        const SizedBox(height: 20),
        TextField(
          controller: _dni,
          enabled: !_cargando,
          keyboardType: TextInputType.number,
          maxLength: 8,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: const InputDecoration(
            labelText: 'DNI',
            counterText: '',
            prefixIcon: Icon(Icons.badge_outlined),
            border: OutlineInputBorder(),
          ),
        ),
        _errorWidget(),
        const SizedBox(height: 18),
        SizedBox(
          height: 50,
          child: ElevatedButton(
            onPressed: _cargando ? null : _solicitar,
            child: _cargando
                ? const _Cargando()
                : const Text('Enviarme el código'),
          ),
        ),
      ],
    );
  }

  // ── Paso 2 ────────────────────────────────────────────────────
  Widget _vistaCodigo() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Icon(Icons.sms_outlined, size: 48, color: YakuColors.agua),
        const SizedBox(height: 12),
        const Text('Revisa tus mensajes',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 19, fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        Text(
          _telefono != null && _telefono!.isNotEmpty
              ? 'Enviamos un código al celular $_telefono. '
                  'Vence en $_vigenciaMin minutos.'
              : 'Si el DNI está registrado, enviamos un código al celular '
                  'asociado. Vence en $_vigenciaMin minutos.',
          textAlign: TextAlign.center,
          style: const TextStyle(color: Colors.black54, fontSize: 14),
        ),
        const SizedBox(height: 20),
        TextField(
          controller: _codigo,
          enabled: !_cargando,
          keyboardType: TextInputType.number,
          maxLength: 6,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 26, letterSpacing: 10),
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: const InputDecoration(
            labelText: 'Código de 6 dígitos',
            counterText: '',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _clave,
          enabled: !_cargando,
          obscureText: !_verClave,
          decoration: InputDecoration(
            labelText: 'Clave nueva',
            prefixIcon: const Icon(Icons.lock_outline),
            suffixIcon: IconButton(
              icon: Icon(_verClave ? Icons.visibility_off : Icons.visibility),
              onPressed: () => setState(() => _verClave = !_verClave),
            ),
            border: const OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _claveRepetida,
          enabled: !_cargando,
          obscureText: !_verClave,
          decoration: const InputDecoration(
            labelText: 'Repite la clave nueva',
            prefixIcon: Icon(Icons.lock_outline),
            border: OutlineInputBorder(),
          ),
          onSubmitted: (_) => _confirmar(),
        ),
        _errorWidget(),
        const SizedBox(height: 18),
        SizedBox(
          height: 50,
          child: ElevatedButton(
            onPressed: _cargando ? null : _confirmar,
            child: _cargando ? const _Cargando() : const Text('Cambiar mi clave'),
          ),
        ),
        TextButton(
          onPressed: _cargando ? null : _solicitar,
          child: const Text('No me llegó, enviar otro código'),
        ),
      ],
    );
  }

  // ── Final ─────────────────────────────────────────────────────
  Widget _vistaListo() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Icon(Icons.check_circle, size: 64, color: YakuColors.verde),
        const SizedBox(height: 14),
        const Text('Tu clave fue actualizada',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 19, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        const Text('Ya puedes ingresar con tu DNI y tu clave nueva.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.black54, fontSize: 14)),
        const SizedBox(height: 24),
        SizedBox(
          height: 50,
          child: ElevatedButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Volver al ingreso'),
          ),
        ),
      ],
    );
  }

  Widget _errorWidget() {
    if (_error == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: YakuColors.rojo.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            const Icon(Icons.error_outline, color: YakuColors.rojo, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: Text(_error!,
                  style: const TextStyle(color: YakuColors.rojo, fontSize: 13)),
            ),
          ],
        ),
      ),
    );
  }
}

class _Cargando extends StatelessWidget {
  const _Cargando();

  @override
  Widget build(BuildContext context) => const SizedBox(
        width: 22,
        height: 22,
        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
      );
}
