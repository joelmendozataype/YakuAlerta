import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api/api_client.dart';
import '../../core/theme.dart';
import 'escaner_qr_screen.dart';

/// Dispositivos vinculados: tableros web autorizados desde este celular.
///
/// Réplica del apartado «Dispositivos vinculados» de WhatsApp: el móvil es la
/// llave maestra y puede cerrar cualquier sesión web que haya autorizado. Al
/// cerrarla, el acceso de esa computadora caduca de inmediato.
class SesionesScreen extends StatefulWidget {
  const SesionesScreen({super.key});

  @override
  State<SesionesScreen> createState() => _SesionesScreenState();
}

class _SesionesScreenState extends State<SesionesScreen> {
  final _api = ApiClient.instance;
  List<SesionVinculada> _sesiones = [];
  bool _cargando = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    setState(() { _cargando = true; _error = null; });
    try {
      final s = await _api.sesionesVinculadas();
      if (!mounted) return;
      setState(() { _sesiones = s; _cargando = false; });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() { _error = e.mensaje; _cargando = false; });
    }
  }

  Future<void> _cerrar(SesionVinculada s) async {
    final ok = await _confirmar(
      titulo: 'Cerrar sesión',
      cuerpo: 'Se cerrará el tablero web en ${s.dispositivo}. '
          'Para volver a usarlo habrá que escanear un nuevo código.',
    );
    if (ok != true) return;
    try {
      await _api.cerrarSesionVinculada(s.sesionId);
      if (!mounted) return;
      _aviso('Sesión cerrada en ${s.dispositivo}');
      _cargar();
    } on ApiException catch (e) {
      if (mounted) _aviso(e.mensaje);
    }
  }

  Future<void> _cerrarTodas() async {
    final ok = await _confirmar(
      titulo: 'Cerrar todas las sesiones',
      cuerpo: 'Se cerrarán los ${_sesiones.length} tableros web vinculados.',
    );
    if (ok != true) return;
    try {
      final n = await _api.cerrarTodasLasSesiones();
      if (!mounted) return;
      _aviso('$n sesión(es) cerrada(s)');
      _cargar();
    } on ApiException catch (e) {
      if (mounted) _aviso(e.mensaje);
    }
  }

  Future<bool?> _confirmar({required String titulo, required String cuerpo}) {
    return showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(titulo),
        content: Text(cuerpo),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: YakuColors.rojo),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Cerrar'),
          ),
        ],
      ),
    );
  }

  void _aviso(String texto) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(texto)));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Dispositivos vinculados'),
        actions: [
          if (_sesiones.isNotEmpty)
            IconButton(
              tooltip: 'Cerrar todas',
              onPressed: _cerrarTodas,
              icon: const Icon(Icons.logout),
            ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          await Navigator.push(context,
              MaterialPageRoute(builder: (_) => const EscanerQrScreen()));
          _cargar();
        },
        icon: const Icon(Icons.qr_code_scanner),
        label: const Text('Vincular'),
      ),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: _cargando
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? _mensajeCentral(Icons.wifi_off, _error!)
                : _sesiones.isEmpty
                    ? _mensajeCentral(Icons.devices_other,
                        'No hay ningún tablero web vinculado.\n'
                        'Pulsa «Vincular» y escanea el código que aparece en la computadora.')
                    : ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          const Text(
                            'Estos tableros web tienen tu sesión abierta. '
                            'Puedes cerrar el acceso en cualquier momento.',
                            style: TextStyle(color: Colors.black54),
                          ),
                          const SizedBox(height: 12),
                          ..._sesiones.map(_tarjeta),
                        ],
                      ),
      ),
    );
  }

  Widget _tarjeta(SesionVinculada s) {
    final fecha = DateFormat('dd/MM/yyyy HH:mm').format(s.vinculadoEn.toLocal());
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: YakuColors.agua.withValues(alpha: 0.12),
          child: const Icon(Icons.desktop_windows_outlined, color: YakuColors.agua),
        ),
        title: Row(
          children: [
            Flexible(child: Text(s.dispositivo,
                style: const TextStyle(fontWeight: FontWeight.bold))),
            if (s.esSesionActual)
              Container(
                margin: const EdgeInsets.only(left: 8),
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: YakuColors.verde.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Text('este equipo',
                    style: TextStyle(fontSize: 11, color: YakuColors.verde)),
              ),
          ],
        ),
        subtitle: Text('Vinculado el $fecha'
            '${s.ipOrigen != null ? "\n${s.ipOrigen}" : ""}'),
        isThreeLine: s.ipOrigen != null,
        trailing: IconButton(
          icon: const Icon(Icons.close, color: YakuColors.rojo),
          tooltip: 'Cerrar sesión',
          onPressed: () => _cerrar(s),
        ),
      ),
    );
  }

  Widget _mensajeCentral(IconData icono, String texto) => ListView(
        children: [
          const SizedBox(height: 120),
          Icon(icono, size: 56, color: Colors.black26),
          const SizedBox(height: 16),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Text(texto,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.black54)),
          ),
        ],
      );
}
