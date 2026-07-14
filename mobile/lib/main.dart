import 'package:flutter/material.dart';

import 'core/api/api_client.dart';
import 'core/sync/sync_service.dart';
import 'core/theme.dart';
import 'features/auth/login_screen.dart';
import 'features/home/home_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SyncService.instance.iniciarAutoSync();
  runApp(const YakuApp());
}

class YakuApp extends StatelessWidget {
  const YakuApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'YakuAlerta',
      debugShowCheckedModeBanner: false,
      theme: yakuTheme(),
      home: const _Arranque(),
    );
  }
}

/// Decide la pantalla inicial según la sesión persistida (acceso offline, HU-01).
class _Arranque extends StatefulWidget {
  const _Arranque();
  @override
  State<_Arranque> createState() => _ArranqueState();
}

class _ArranqueState extends State<_Arranque> {
  Future<bool>? _sesion;

  @override
  void initState() {
    super.initState();
    _sesion = ApiClient.instance.token.then((t) => t != null);
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<bool>(
      future: _sesion,
      builder: (context, snap) {
        if (!snap.hasData) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        return snap.data! ? const HomeScreen() : const LoginScreen();
      },
    );
  }
}
