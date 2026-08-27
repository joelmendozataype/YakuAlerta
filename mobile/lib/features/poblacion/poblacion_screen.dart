import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/theme.dart';
import '../comun/marco_rol.dart';

/// Vista de la población usuaria.
///
/// Una sola pregunta, respondida en grande: **¿puedo tomar el agua hoy?**
/// Sin cifras técnicas: solo el estado y qué hacer, igual que el aviso
/// comunitario impreso que se fija en el punto de agua.
class PoblacionScreen extends StatefulWidget {
  const PoblacionScreen({super.key});

  @override
  State<PoblacionScreen> createState() => _PoblacionScreenState();
}

class _PoblacionScreenState extends State<PoblacionScreen> {
  final _api = ApiClient.instance;
  Map<String, dynamic>? _estado;
  bool _cargando = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final u = await _api.usuarioCacheado();
      final comunidad = u?['comunidad_id'] as int?;
      if (comunidad == null) {
        if (!mounted) return;
        setState(() {
          _error = 'Su cuenta aún no tiene una comunidad asignada. '
              'Solicite a la ATM que la registre.';
          _cargando = false;
        });
        return;
      }
      final estado = await _api.estadoPublico(comunidad);
      if (!mounted) return;
      setState(() {
        _estado = estado;
        _cargando = false;
      });
    } on ApiException catch (e) {
      if (mounted) {
        setState(() {
          _error = e.mensaje;
          _cargando = false;
        });
      }
    }
  }

  Color get _color => switch (_estado?['nivel']) {
        'VERDE' => YakuColors.verde,
        'AMARILLO' => YakuColors.amarillo,
        'ROJO' => YakuColors.rojo,
        _ => Colors.grey,
      };

  @override
  Widget build(BuildContext context) {
    return MarcoRol(
      titulo: 'El agua de mi comunidad',
      subtitulo: _estado?['comunidad'] as String?,
      alRecargar: _cargar,
      hijo: _cargando
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? MensajeVacio(icono: Icons.info_outline, texto: _error!)
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    _banda(),
                    const SizedBox(height: 22),
                    const Text('¿Qué debe hacer?',
                        style: TextStyle(
                            fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(height: 10),
                    ...((_estado?['acciones'] as List?) ?? []).map(_accion),
                    const SizedBox(height: 22),
                    Center(
                      child: Text(
                        'Información difundida por su JASS\n'
                        'con apoyo del Área Técnica Municipal',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            fontSize: 12,
                            color: Colors.black.withValues(alpha: 0.4)),
                      ),
                    ),
                  ],
                ),
    );
  }

  Widget _banda() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 30, horizontal: 20),
      decoration: BoxDecoration(
        color: _color,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        children: [
          const Icon(Icons.water_drop, color: Colors.white, size: 52),
          const SizedBox(height: 12),
          Text('${_estado?['etiqueta'] ?? 'SIN INFORMACIÓN'}',
              textAlign: TextAlign.center,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 27,
                  fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          Text('${_estado?['instruccion'] ?? ''}',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white, fontSize: 16.5)),
        ],
      ),
    );
  }

  Widget _accion(dynamic texto) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(top: 6, right: 10),
              child: Container(
                width: 8,
                height: 8,
                decoration:
                    BoxDecoration(color: _color, shape: BoxShape.circle),
              ),
            ),
            Expanded(
              child: Text('$texto',
                  style: const TextStyle(fontSize: 15.5, height: 1.4)),
            ),
          ],
        ),
      );
}
