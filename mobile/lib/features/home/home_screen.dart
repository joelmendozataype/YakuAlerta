import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api/api_client.dart';
import '../../core/db/local_db.dart';
import '../../core/models/medicion.dart';
import '../../core/models/reservorio.dart';
import '../../core/sync/sync_service.dart';
import '../../core/theme.dart';
import '../auth/login_screen.dart';
import '../medicion/registro_screen.dart';
import '../vincular_web/escaner_qr_screen.dart';

/// Pantalla principal del operador: reservorios asignados, estado offline,
/// cola de sincronización y últimas mediciones.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Reservorio> _reservorios = [];
  List<Medicion> _recientes = [];
  int _pendientes = 0;
  bool _online = false;
  Map<String, dynamic>? _usuario;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    final res = await LocalDb.instance.reservorios();
    final rec = await LocalDb.instance.medicionesRecientes(limite: 10);
    final pend = await LocalDb.instance.contarPendientes();
    final online = await SyncService.instance.hayConexion();
    final user = await ApiClient.instance.usuarioCacheado();
    if (!mounted) return;
    setState(() {
      _reservorios = res;
      _recientes = rec;
      _pendientes = pend;
      _online = online;
      _usuario = user;
    });
  }

  Future<void> _sincronizar() async {
    final r = await SyncService.instance.sincronizar();
    if (!mounted) return;
    if (r == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Sin conexión. Se sincronizará automáticamente al recuperar señal.')));
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Sincronizado: ${r.insertadas} nuevas, ${r.duplicadas} duplicadas, ${r.alertas} alertas.')));
    }
    _cargar();
  }

  Future<void> _salir() async {
    await ApiClient.instance.cerrarSesion();
    if (!mounted) return;
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const LoginScreen()));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('YakuAlerta', style: TextStyle(fontSize: 18)),
            Text(_usuario?['nombres'] ?? 'Operador',
                style: const TextStyle(fontSize: 12, color: Colors.white70)),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Vincular tablero web',
            onPressed: () => Navigator.push(context,
                MaterialPageRoute(builder: (_) => const EscanerQrScreen())),
            icon: const Icon(Icons.qr_code_scanner),
          ),
          IconButton(onPressed: _salir, icon: const Icon(Icons.logout)),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _bannerConectividad(),
            const SizedBox(height: 16),
            const Text('Mis reservorios', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            if (_reservorios.isEmpty)
              const Card(child: Padding(padding: EdgeInsets.all(16),
                child: Text('No tienes reservorios asignados. Contacta al administrador.'))),
            ..._reservorios.map(_tarjetaReservorio),
            const SizedBox(height: 20),
            const Text('Últimas mediciones', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            if (_recientes.isEmpty)
              const Text('Aún no hay mediciones registradas.', style: TextStyle(color: Colors.black54)),
            ..._recientes.map(_filaMedicion),
          ],
        ),
      ),
    );
  }

  Widget _bannerConectividad() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _online ? YakuColors.verde.withValues(alpha: 0.1) : Colors.orange.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _online ? YakuColors.verde : Colors.orange),
      ),
      child: Row(
        children: [
          Icon(_online ? Icons.cloud_done : Icons.cloud_off,
              color: _online ? YakuColors.verde : Colors.orange),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              _online ? 'En línea' : 'Modo sin conexión — tus registros se guardan localmente',
              style: TextStyle(
                  color: _online ? YakuColors.verde : Colors.orange.shade900,
                  fontWeight: FontWeight.w600),
            ),
          ),
          if (_pendientes > 0)
            TextButton.icon(
              onPressed: _sincronizar,
              icon: const Icon(Icons.sync),
              label: Text('$_pendientes'),
            ),
        ],
      ),
    );
  }

  Widget _tarjetaReservorio(Reservorio r) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: const CircleAvatar(
          backgroundColor: YakuColors.aguaClaro,
          child: Icon(Icons.water_drop, color: YakuColors.agua),
        ),
        title: Text(r.codigo, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text('${r.volumenM3.toStringAsFixed(0)} m³ · ${r.tipoSistema ?? "—"}'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () async {
          await Navigator.push(context,
              MaterialPageRoute(builder: (_) => RegistroScreen(reservorio: r)));
          _cargar();
        },
      ),
    );
  }

  Widget _filaMedicion(Medicion m) {
    final color = YakuColors.deNivel(m.nivel);
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(YakuColors.iconoNivel(m.nivel), color: color),
        title: Text('Cloro ${m.cloroMgL ?? "—"} mg/L · Turb ${m.turbidezUnt ?? "—"} UNT'),
        subtitle: Text(DateFormat('dd/MM/yyyy HH:mm').format(m.fechaHora)),
        trailing: m.estadoSync == EstadoSync.sincronizado
            ? const Icon(Icons.check_circle, color: YakuColors.verde, size: 20)
            : Icon(m.estadoSync == EstadoSync.enviadoSms ? Icons.sms : Icons.schedule,
                color: Colors.orange, size: 20),
      ),
    );
  }
}
