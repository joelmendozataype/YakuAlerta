import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../atm/atm_screen.dart';
import '../home/home_screen.dart';
import '../poblacion/poblacion_screen.dart';
import '../salud/salud_screen.dart';

/// Decide la pantalla de inicio según el rol de la sesión.
///
/// Cada perfil ve **solo lo suyo**: el operador de la JASS conserva el flujo
/// completo de vigilancia; los demás reciben la vista mínima que corresponde a
/// su función, sin opciones que no les competen.
class InicioPorRol extends StatelessWidget {
  const InicioPorRol({super.key});

  static Widget paraRol(String? rol) => switch (rol) {
        'OPERADOR' || 'DIRECTIVO_JASS' => const HomeScreen(),
        'ATM' || 'AUTORIDAD_LOCAL' => const AtmScreen(),
        'SALUD' => const SaludScreen(),
        'POBLACION' => const PoblacionScreen(),
        // DESA, DRVCS y administrador operan desde el tablero web.
        _ => const PoblacionScreen(),
      };

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>?>(
      future: ApiClient.instance.usuarioCacheado(),
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        return paraRol(snap.data?['rol'] as String?);
      },
    );
  }
}
