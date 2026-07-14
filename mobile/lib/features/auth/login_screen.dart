import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/db/local_db.dart';
import '../../core/models/reservorio.dart';
import '../../core/theme.dart';
import '../home/home_screen.dart';

/// HU-01: inicio de sesión del operador con celular y clave simple.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _telefono = TextEditingController(text: '987000001');
  final _clave = TextEditingController(text: 'yaku2026');
  bool _cargando = false;
  String? _error;

  Future<void> _ingresar() async {
    setState(() { _cargando = true; _error = null; });
    try {
      final data = await ApiClient.instance.login(_telefono.text.trim(), _clave.text);
      // Cachear reservorios asignados para operar offline
      final reservorios = (data['reservorios'] as List)
          .map((j) => Reservorio.fromJson(j as Map<String, dynamic>))
          .toList();
      await LocalDb.instance.guardarReservorios(reservorios);
      if (!mounted) return;
      Navigator.pushReplacement(
        context, MaterialPageRoute(builder: (_) => const HomeScreen()));
    } on ApiException catch (e) {
      setState(() => _error = e.mensaje);
    } catch (_) {
      setState(() => _error = 'Sin conexión y sin sesión previa. Verifica tu red la primera vez.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: YakuColors.aguaOscuro,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 40),
              const Text('💧', style: TextStyle(fontSize: 64), textAlign: TextAlign.center),
              const SizedBox(height: 12),
              const Text('YakuAlerta',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white, fontSize: 34, fontWeight: FontWeight.bold)),
              const Text('Vigilancia del agua · Huancavelica',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white70, fontSize: 14)),
              const SizedBox(height: 40),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const Text('Ingresa con tu celular',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _telefono,
                        keyboardType: TextInputType.phone,
                        decoration: const InputDecoration(
                          labelText: 'Número de celular',
                          prefixIcon: Icon(Icons.phone_android),
                        ),
                      ),
                      const SizedBox(height: 14),
                      TextField(
                        controller: _clave,
                        obscureText: true,
                        decoration: const InputDecoration(
                          labelText: 'Clave',
                          prefixIcon: Icon(Icons.lock_outline),
                        ),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 12),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: YakuColors.rojo.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(_error!, style: const TextStyle(color: YakuColors.rojo)),
                        ),
                      ],
                      const SizedBox(height: 20),
                      ElevatedButton(
                        onPressed: _cargando ? null : _ingresar,
                        child: _cargando
                            ? const SizedBox(height: 24, width: 24,
                                child: CircularProgressIndicator(color: Colors.white, strokeWidth: 3))
                            : const Text('Ingresar'),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              const Text('Demo operador: 987000001 / yaku2026',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white54, fontSize: 12)),
            ],
          ),
        ),
      ),
    );
  }
}
