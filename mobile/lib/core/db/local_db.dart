import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

import '../models/medicion.dart';
import '../models/reservorio.dart';

/// Base de datos local SQLite (offline-first, RNF-01).
///
/// Guarda las mediciones con su estado de sincronización y cachea los
/// reservorios asignados para operar sin conexión.
class LocalDb {
  LocalDb._();
  static final LocalDb instance = LocalDb._();
  Database? _db;

  Future<Database> get db async => _db ??= await _abrir();

  Future<Database> _abrir() async {
    final ruta = p.join(await getDatabasesPath(), 'yakualerta.db');
    return openDatabase(ruta, version: 2, onCreate: _crear, onUpgrade: _actualizar);
  }

  Future<void> _crear(Database d, int v) async {
    await d.execute('''
      CREATE TABLE medicion (
        id_local       INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid_registro  TEXT UNIQUE NOT NULL,
        reservorio_id  INTEGER NOT NULL,
        fecha_hora     TEXT NOT NULL,
        cloro_mg_l     REAL,
        turbidez_unt   REAL,
        metodo_cloro   TEXT NOT NULL DEFAULT 'MANUAL',
        observaciones  TEXT,
        nivel_riesgo   TEXT NOT NULL,
        estado_sync    TEXT NOT NULL DEFAULT 'PENDIENTE',
        ruta_foto      TEXT,
        latitud        REAL,
        longitud       REAL,
        foto_sync      INTEGER NOT NULL DEFAULT 0
      )
    ''');
    await d.execute('''
      CREATE TABLE reservorio (
        reservorio_id  INTEGER PRIMARY KEY,
        comunidad_id   INTEGER NOT NULL,
        codigo         TEXT NOT NULL,
        volumen_m3     REAL NOT NULL,
        tipo_sistema   TEXT
      )
    ''');
    await d.execute('CREATE INDEX idx_med_sync ON medicion(estado_sync)');
  }

  /// Migraciones de esquema entre versiones.
  Future<void> _actualizar(Database d, int desde, int hasta) async {
    if (desde < 2) {
      // v2: seguimiento de la subida de evidencia fotográfica (HU-08).
      await d.execute(
          'ALTER TABLE medicion ADD COLUMN foto_sync INTEGER NOT NULL DEFAULT 0');
    }
  }

  // ─── Mediciones ───────────────────────────────────────────────
  Future<int> guardarMedicion(Medicion m) async {
    final d = await db;
    return d.insert('medicion', m.toDb(),
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<Medicion>> medicionesRecientes({int limite = 50}) async {
    final d = await db;
    final rows = await d.query('medicion',
        orderBy: 'fecha_hora DESC', limit: limite);
    return rows.map(Medicion.fromDb).toList();
  }

  Future<List<Medicion>> pendientes() async {
    final d = await db;
    final rows = await d.query('medicion',
        where: "estado_sync != 'SINCRONIZADO'", orderBy: 'fecha_hora ASC');
    return rows.map(Medicion.fromDb).toList();
  }

  Future<int> contarPendientes() async {
    final d = await db;
    final r = await d.rawQuery(
        "SELECT COUNT(*) c FROM medicion WHERE estado_sync != 'SINCRONIZADO'");
    return (r.first['c'] as int?) ?? 0;
  }

  Future<void> marcarEstado(String uuid, EstadoSync estado) async {
    final d = await db;
    await d.update('medicion', {'estado_sync': estado.valor},
        where: 'uuid_registro = ?', whereArgs: [uuid]);
  }

  /// Mediciones ya sincronizadas cuya foto aún no se subió (HU-08, 2ª fase).
  Future<List<Medicion>> fotosPendientes() async {
    final d = await db;
    final rows = await d.query('medicion',
        where: "ruta_foto IS NOT NULL AND foto_sync = 0 AND estado_sync = 'SINCRONIZADO'");
    return rows.map(Medicion.fromDb).toList();
  }

  Future<void> marcarFotoSubida(String uuid) async {
    final d = await db;
    await d.update('medicion', {'foto_sync': 1},
        where: 'uuid_registro = ?', whereArgs: [uuid]);
  }

  // ─── Reservorios (caché) ──────────────────────────────────────
  Future<void> guardarReservorios(List<Reservorio> lista) async {
    final d = await db;
    final batch = d.batch();
    for (final r in lista) {
      batch.insert('reservorio', r.toDb(),
          conflictAlgorithm: ConflictAlgorithm.replace);
    }
    await batch.commit(noResult: true);
  }

  Future<List<Reservorio>> reservorios() async {
    final d = await db;
    final rows = await d.query('reservorio', orderBy: 'codigo');
    return rows.map(Reservorio.fromDb).toList();
  }

  Future<Reservorio?> reservorio(int id) async {
    final d = await db;
    final rows = await d.query('reservorio',
        where: 'reservorio_id = ?', whereArgs: [id], limit: 1);
    return rows.isEmpty ? null : Reservorio.fromDb(rows.first);
  }
}
