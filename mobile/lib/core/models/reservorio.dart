/// Reservorio asignado al operador (se cachea localmente tras el login).
class Reservorio {
  final int reservorioId;
  final int comunidadId;
  final String codigo;
  final double volumenM3;
  final String? tipoSistema;

  const Reservorio({
    required this.reservorioId,
    required this.comunidadId,
    required this.codigo,
    required this.volumenM3,
    this.tipoSistema,
  });

  Map<String, dynamic> toDb() => {
        'reservorio_id': reservorioId,
        'comunidad_id': comunidadId,
        'codigo': codigo,
        'volumen_m3': volumenM3,
        'tipo_sistema': tipoSistema,
      };

  factory Reservorio.fromJson(Map<String, dynamic> j) => Reservorio(
        reservorioId: j['reservorio_id'] as int,
        comunidadId: j['comunidad_id'] as int,
        codigo: j['codigo'] as String,
        volumenM3: (j['volumen_m3'] as num).toDouble(),
        tipoSistema: j['tipo_sistema'] as String?,
      );

  factory Reservorio.fromDb(Map<String, dynamic> m) => Reservorio(
        reservorioId: m['reservorio_id'] as int,
        comunidadId: m['comunidad_id'] as int,
        codigo: m['codigo'] as String,
        volumenM3: (m['volumen_m3'] as num).toDouble(),
        tipoSistema: m['tipo_sistema'] as String?,
      );
}
