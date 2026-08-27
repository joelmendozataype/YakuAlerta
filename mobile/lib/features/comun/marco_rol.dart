import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/theme.dart';
import '../auth/login_screen.dart';

/// Estructura común de las pantallas de rol: barra con el nombre del usuario,
/// acción de salir y recarga deslizando hacia abajo.
class MarcoRol extends StatelessWidget {
  final String titulo;
  final String? subtitulo;
  final Widget hijo;
  final Future<void> Function() alRecargar;
  final List<Widget> acciones;

  const MarcoRol({
    super.key,
    required this.titulo,
    required this.hijo,
    required this.alRecargar,
    this.subtitulo,
    this.acciones = const [],
  });

  Future<void> _salir(BuildContext context) async {
    await ApiClient.instance.cerrarSesion();
    if (!context.mounted) return;
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (_) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(titulo, style: const TextStyle(fontSize: 18)),
            if (subtitulo != null)
              Text(subtitulo!,
                  style: const TextStyle(fontSize: 12, color: Color(0xFFCBD5E1))),
          ],
        ),
        actions: [
          ...acciones,
          IconButton(
            tooltip: 'Salir',
            onPressed: () => _salir(context),
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: RefreshIndicator(onRefresh: alRecargar, child: hijo),
    );
  }
}

/// Tarjeta de indicador con un número grande.
class TarjetaDato extends StatelessWidget {
  final String valor;
  final String etiqueta;
  final Color color;
  final IconData icono;

  const TarjetaDato({
    super.key,
    required this.valor,
    required this.etiqueta,
    required this.color,
    required this.icono,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
        child: Column(
          children: [
            Icon(icono, color: color, size: 26),
            const SizedBox(height: 6),
            Text(valor,
                style: TextStyle(
                    fontSize: 26, fontWeight: FontWeight.bold, color: color)),
            const SizedBox(height: 2),
            Text(etiqueta,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 11.5, color: Colors.black54)),
          ],
        ),
      ),
    );
  }
}

/// Mensaje centrado para estados vacíos o de error.
class MensajeVacio extends StatelessWidget {
  final IconData icono;
  final String texto;
  const MensajeVacio({super.key, required this.icono, required this.texto});

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        const SizedBox(height: 100),
        Icon(icono, size: 56, color: Colors.black26),
        const SizedBox(height: 14),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Text(texto,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.black54, fontSize: 15)),
        ),
      ],
    );
  }
}

/// Distintivo de color según el nivel de riesgo.
class EtiquetaNivel extends StatelessWidget {
  final String? nivel;
  const EtiquetaNivel({super.key, this.nivel});

  @override
  Widget build(BuildContext context) {
    final (color, texto) = switch (nivel) {
      'VERDE' => (YakuColors.verde, 'Segura'),
      'AMARILLO' => (YakuColors.amarillo, 'En riesgo'),
      'ROJO' => (YakuColors.rojo, 'No segura'),
      _ => (Colors.grey, 'Sin dato'),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(texto,
          style: TextStyle(
              color: color, fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }
}
