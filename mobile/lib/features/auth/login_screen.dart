import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api/api_client.dart';
import '../../core/theme.dart';
import '../roles/inicio_por_rol.dart';
import 'recuperar_clave_screen.dart';

/// Grupo de rol que el usuario elige antes de ingresar.
///
/// Son las cuatro categorías que la gente reconoce en campo; internamente el
/// backend las traduce a los roles del sistema. Los perfiles regionales
/// (DESA, DRVCS) y el administrador ingresan por el tablero web.
enum GrupoRol {
  jass('JASS', 'JASS (Vigilancia del Agua)', Icons.water_drop_outlined),
  atm('ATM', 'ATM (Autoridad Local)', Icons.account_balance_outlined),
  ipressSalud('IPRESS_SALUD', 'IPRESS / SALUD', Icons.local_hospital_outlined),
  usuario('USUARIO', 'USUARIO', Icons.person_outline);

  const GrupoRol(this.valor, this.etiqueta, this.icono);

  /// Valor que entiende el backend.
  final String valor;
  final String etiqueta;
  final IconData icono;
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  static const _largoDni = 8;

  GrupoRol? _grupo;
  final _dni = TextEditingController();
  final _clave = TextEditingController();
  bool _cargando = false;
  bool _verClave = false;
  String? _error;

  @override
  void dispose() {
    _dni.dispose();
    _clave.dispose();
    super.dispose();
  }

  /// Validación previa: el rol es obligatorio y el DNI debe tener 8 dígitos.
  String? _validacionLocal() {
    if (_grupo == null) return 'Seleccione su tipo de rol para continuar.';
    if (_dni.text.trim().length != _largoDni) {
      return 'El DNI debe tener $_largoDni dígitos.';
    }
    if (_clave.text.isEmpty) return 'Ingrese su clave.';
    return null;
  }

  Future<void> _entrar() async {
    final problema = _validacionLocal();
    if (problema != null) {
      setState(() => _error = problema);
      return;
    }
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      await ApiClient.instance.login(
        _dni.text.trim(),
        _clave.text,
        grupoRol: _grupo!.valor,
      );
      if (!mounted) return;
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const InicioPorRol()),
      );
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.mensaje);
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  void _recuperarClave() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const RecuperarClaveScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: YakuColors.aguaOscuro,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            children: [
              const SizedBox(height: 40),
              const Icon(Icons.location_on, size: 96, color: Color(0xFF7FA9F5)),
              const Text(
                'YakuAlerta',
                style: TextStyle(
                  fontSize: 34,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 4),
              const Text(
                'Vigilancia del agua · Huancavelica',
                style: TextStyle(fontSize: 14, color: Color(0xFFCBD5E1)),
              ),
              const SizedBox(height: 28),
              _tarjeta(),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _tarjeta() {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // ── 1. Tipo de rol ──────────────────────────────────
          DropdownButtonFormField<GrupoRol>(
            initialValue: _grupo,
            isExpanded: true,
            decoration: const InputDecoration(
              labelText: 'Tipo de Rol (Seleccione uno)',
              border: OutlineInputBorder(),
            ),
            hint: const Text('Tipo de Rol (Seleccione uno)'),
            items: [
              for (final g in GrupoRol.values)
                DropdownMenuItem(
                  value: g,
                  child: Row(
                    children: [
                      Icon(g.icono, size: 20, color: YakuColors.agua),
                      const SizedBox(width: 10),
                      Flexible(
                        child: Text(g.etiqueta,
                            overflow: TextOverflow.ellipsis),
                      ),
                    ],
                  ),
                ),
            ],
            onChanged: _cargando
                ? null
                : (g) => setState(() {
                      _grupo = g;
                      _error = null;
                    }),
          ),
          const SizedBox(height: 16),

          // ── 2. DNI (usuario) ────────────────────────────────
          TextField(
            controller: _dni,
            enabled: !_cargando,
            keyboardType: TextInputType.number,
            maxLength: _largoDni,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            decoration: const InputDecoration(
              labelText: 'DNI',
              hintText: '70100001',
              counterText: '',
              prefixIcon: Icon(Icons.badge_outlined),
              border: OutlineInputBorder(),
            ),
            onChanged: (_) {
              if (_error != null) setState(() => _error = null);
            },
          ),
          const SizedBox(height: 12),

          // ── 3. Clave ────────────────────────────────────────
          TextField(
            controller: _clave,
            enabled: !_cargando,
            obscureText: !_verClave,
            decoration: InputDecoration(
              labelText: 'Clave',
              prefixIcon: const Icon(Icons.lock_outline),
              suffixIcon: IconButton(
                icon: Icon(
                    _verClave ? Icons.visibility_off : Icons.visibility),
                onPressed: () => setState(() => _verClave = !_verClave),
              ),
              border: const OutlineInputBorder(),
            ),
            onSubmitted: (_) => _entrar(),
          ),

          if (_error != null) ...[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: YakuColors.rojo.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline,
                      color: YakuColors.rojo, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(_error!,
                        style: const TextStyle(
                            color: YakuColors.rojo, fontSize: 13)),
                  ),
                ],
              ),
            ),
          ],

          const SizedBox(height: 22),
          SizedBox(
            height: 52,
            child: ElevatedButton(
              onPressed: _cargando ? null : _entrar,
              child: _cargando
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Text('Ingresar',
                      style: TextStyle(
                          fontSize: 17, fontWeight: FontWeight.bold)),
            ),
          ),
          const SizedBox(height: 14),
          Center(
            child: TextButton(
              onPressed: _cargando ? null : _recuperarClave,
              child: const Text(
                '¿Olvidaste tu contraseña? Para recuperar tu clave presiona aquí',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12.5, color: YakuColors.aguaOscuro),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
