import 'package:flutter/material.dart';

import 'rules/motor_riesgo.dart';

/// Identidad visual YakuAlerta: paleta agua/petróleo + semáforo accesible.
class YakuColors {
  static const agua = Color(0xFF0E7490);
  static const aguaOscuro = Color(0xFF155E75);
  static const aguaClaro = Color(0xFFECFEFF);
  static const verde = Color(0xFF15803D);
  static const amarillo = Color(0xFFB45309);
  static const rojo = Color(0xFFB91C1C);

  static Color deNivel(NivelRiesgo n) => switch (n) {
        NivelRiesgo.verde => verde,
        NivelRiesgo.amarillo => amarillo,
        NivelRiesgo.rojo => rojo,
      };

  static IconData iconoNivel(NivelRiesgo n) => switch (n) {
        NivelRiesgo.verde => Icons.check_circle,
        NivelRiesgo.amarillo => Icons.warning_amber_rounded,
        NivelRiesgo.rojo => Icons.dangerous,
      };
}

ThemeData yakuTheme() {
  final base = ThemeData(
    useMaterial3: true,
    colorSchemeSeed: YakuColors.agua,
    scaffoldBackgroundColor: const Color(0xFFF1F5F9),
  );
  return base.copyWith(
    appBarTheme: const AppBarTheme(
      backgroundColor: YakuColors.aguaOscuro,
      foregroundColor: Colors.white,
      centerTitle: false,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: YakuColors.agua,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(56), // botones grandes (RNF-02)
        textStyle: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
    ),
    cardTheme: CardTheme(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
    ),
  );
}
