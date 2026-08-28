"""Esquemas Pydantic (contratos de la API REST)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import (
    CanalNotif, DictamenLab, EstadoAlerta, EstadoNotif, EstadoQR, EstadoSync,
    GrupoRol, MetodoLectura, NivelRiesgo, RolUsuario,
)


# ─── Auth ────────────────────────────────────────────────────────
class LoginIn(BaseModel):
    """Credenciales de acceso.

    Desde la app se ingresa con **DNI** y el grupo de rol elegido; el tablero
    web mantiene el acceso por celular. Debe venir uno de los dos identificadores.
    """
    clave: str = Field(examples=["yaku2026"])
    dni: str | None = Field(default=None, examples=["70123456"])
    telefono: str | None = Field(default=None, examples=["987654321"])
    grupo_rol: GrupoRol | None = Field(
        default=None,
        description="Grupo elegido en la app; debe coincidir con el rol de la cuenta",
    )

    @model_validator(mode="after")
    def _exige_identificador(self):
        if not self.dni and not self.telefono:
            raise ValueError("Indique su DNI o su número de celular")
        if self.dni and not (self.dni.isdigit() and len(self.dni) == 8):
            raise ValueError("El DNI debe tener 8 dígitos")
        return self


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    usuario_id: int
    nombres: str
    dni: str | None = None
    telefono: str
    rol: RolUsuario
    entidad: str | None = None
    ubigeo_id: int | None = None
    comunidad_id: int | None = None
    # Territorio al que pertenece, para encabezar las pantallas de la app.
    departamento: str | None = None
    provincia: str | None = None
    distrito: str | None = None
    comunidad: str | None = None
    activo: bool = True


# ─── Recuperación de clave ──────────────────────────────────────
class RecuperacionSolicitarIn(BaseModel):
    dni: str = Field(examples=["70100001"], min_length=8, max_length=8)


class RecuperacionSolicitarOut(BaseModel):
    """Respuesta deliberadamente uniforme: no revela si el DNI existe."""
    mensaje: str
    telefono_enmascarado: str | None = None
    vigencia_min: int = 10


class RecuperacionConfirmarIn(BaseModel):
    dni: str = Field(min_length=8, max_length=8)
    codigo: str = Field(min_length=6, max_length=6, examples=["482913"])
    clave_nueva: str = Field(min_length=6, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
    reservorios: list[ReservorioOut] = []


# ─── Login por QR (vinculación web ↔ móvil) ─────────────────────
class QRNuevaIn(BaseModel):
    client_hash: str = Field(
        min_length=16, max_length=64,
        description="SHA-256 del secreto que el navegador guarda en memoria",
    )


class QRNuevaOut(BaseModel):
    token: str
    contenido_qr: str = Field(description="Cadena a codificar en el código QR")
    expira_en_seg: int


class QREstadoOut(BaseModel):
    estado: EstadoQR
    # Solo viaja cuando el estado es APROBADO y el cliente presenta su secreto.
    sesion: TokenOut | None = None
    # Datos mostrados en la web mientras se espera la confirmación.
    usuario_nombres: str | None = None


class QRConfirmarIn(BaseModel):
    aprobar: bool = True


class SesionVinculadaOut(BaseModel):
    """Dispositivo web vinculado y activo (listado de sesiones del usuario)."""
    sesion_id: int
    dispositivo: str
    ip_origen: str | None = None
    vinculado_en: datetime
    es_sesion_actual: bool = False


# ─── Territorio / entidades ──────────────────────────────────────
class UbigeoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ubigeo_id: int
    codigo_ubigeo: str
    departamento: str
    provincia: str
    distrito: str


class ComunidadIn(BaseModel):
    ubigeo_id: int
    nombre: str
    jass_nombre: str | None = None
    latitud: float | None = None
    longitud: float | None = None
    poblacion_servida: int | None = None


class ComunidadOut(ComunidadIn):
    model_config = ConfigDict(from_attributes=True)
    comunidad_id: int


class MiembroJass(BaseModel):
    """Persona de la JASS: quien mide y quien preside."""
    model_config = ConfigDict(from_attributes=True)
    usuario_id: int
    nombres: str
    rol: RolUsuario
    telefono: str
    activo: bool


class JassOut(BaseModel):
    """Una JASS con lo que la ATM necesita para acompanarla."""
    comunidad_id: int
    comunidad: str
    jass_nombre: str
    poblacion_servida: int | None = None
    reservorios: int
    nivel: NivelRiesgo | None = None
    ultima_medicion: datetime | None = None
    dias_sin_medir: int | None = None
    en_silencio: bool
    miembros: list[MiembroJass]


class ReservorioIn(BaseModel):
    comunidad_id: int
    codigo: str
    volumen_m3: float
    tipo_sistema: str | None = None
    estado_infra: str | None = None
    umbral_silencio_dias: int = 7


class ReservorioOut(ReservorioIn):
    model_config = ConfigDict(from_attributes=True)
    reservorio_id: int


class UsuarioIn(BaseModel):
    nombres: str
    dni: str | None = None
    telefono: str
    clave: str
    rol: RolUsuario
    entidad: str | None = None
    # Ámbito territorial (RF-06). Vacíos = alcance regional.
    ubigeo_id: int | None = None
    comunidad_id: int | None = None


class UsuarioPatch(BaseModel):
    """Lo que se puede corregir de una cuenta ya creada.

    La clave no está aquí: se restablece por su propio endpoint, que deja
    rastro en auditoría.
    """
    nombres: str | None = None
    telefono: str | None = None
    entidad: str | None = None
    comunidad_id: int | None = None
    activo: bool | None = None


class ClaveTemporalOut(BaseModel):
    """Clave provisional entregada una sola vez a quien administra."""
    usuario_id: int
    nombres: str
    clave_temporal: str


# ─── Parámetros normativos (RNF-07) ──────────────────────────────
class ParametroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    parametro_id: int
    parametro: str
    unidad: str
    umbral_amarillo: float | None = None
    umbral_rojo: float | None = None
    norma_referencia: str
    vigente: bool


class ParametroPatch(BaseModel):
    umbral_amarillo: float | None = None
    umbral_rojo: float | None = None
    norma_referencia: str | None = None
    vigente: bool | None = None


# ─── Mediciones / sync ───────────────────────────────────────────
class MedicionIn(BaseModel):
    """Payload de una medición creada en el dispositivo (offline-first)."""
    uuid_registro: str = Field(description="UUID generado en el dispositivo (deduplicación)")
    reservorio_id: int
    fecha_hora: datetime
    cloro_mg_l: float | None = None
    turbidez_unt: float | None = None
    metodo_cloro: MetodoLectura = MetodoLectura.MANUAL
    observaciones: str | None = None
    origen: EstadoSync = EstadoSync.SINCRONIZADO  # SINCRONIZADO (datos) o ENVIADO_SMS


class RecomendacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    gramos_hipoclorito: float | None = None
    concentracion_insumo: float | None = None
    plazo_remedicion_hrs: int | None = None
    protocolo: str | None = None


class MedicionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    medicion_id: int
    uuid_registro: str
    reservorio_id: int
    usuario_id: int
    fecha_hora: datetime
    cloro_mg_l: float | None = None
    turbidez_unt: float | None = None
    metodo_cloro: MetodoLectura
    observaciones: str | None = None
    nivel_riesgo: NivelRiesgo
    estado_sync: EstadoSync
    recomendacion: RecomendacionOut | None = None


class SyncLoteIn(BaseModel):
    mediciones: list[MedicionIn]


class SyncResultado(BaseModel):
    recibidas: int
    insertadas: int
    duplicadas: int
    alertas_generadas: int
    resultados: list[MedicionOut]


# ─── Alertas ─────────────────────────────────────────────────────
class NotificacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    notificacion_id: int
    usuario_id: int
    canal: CanalNotif
    mensaje: str
    estado_entrega: EstadoNotif
    fecha_hora: datetime


class AlertaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    alerta_id: int
    medicion_id: int
    nivel: NivelRiesgo
    estado: EstadoAlerta
    fecha_generacion: datetime
    fecha_cierre: datetime | None = None
    resultado_cierre: str | None = None
    comunidad: str | None = None
    reservorio_codigo: str | None = None
    cloro_mg_l: float | None = None
    turbidez_unt: float | None = None
    protocolo: str | None = None
    evidencia_ids: list[int] = []
    notificaciones: list[NotificacionOut] = []


class CierreAlertaIn(BaseModel):
    medicion_cierre_id: int | None = Field(
        default=None, description="Remedición en verde que cierra el caso (obligatoria en rojo salvo dictamen DESA)")
    resultado_cierre: str
    dictamen_desa: bool = False


# ─── Tablero ─────────────────────────────────────────────────────
class SemaforoComunidad(BaseModel):
    comunidad_id: int
    comunidad: str
    latitud: float | None = None
    longitud: float | None = None
    reservorio_id: int | None = None
    reservorio_codigo: str | None = None
    nivel: NivelRiesgo | None = None
    ultima_medicion: datetime | None = None
    via_recepcion: EstadoSync | None = None
    silencio: bool = False
    dias_sin_medir: int | None = None
    poblacion_servida: int | None = None


class TableroResumen(BaseModel):
    distrito: str
    sistemas_monitoreados: int
    porcentaje_agua_segura: float
    alertas_activas: int
    reservorios_en_silencio: int
    # Personas que hoy reciben agua clasificada como no segura: convierte el
    # semáforo en una magnitud sanitaria comprensible.
    poblacion_expuesta: int = 0
    comunidades: list[SemaforoComunidad]


class HistorialPunto(BaseModel):
    fecha_hora: datetime
    cloro_mg_l: float | None = None
    turbidez_unt: float | None = None
    nivel: NivelRiesgo


# ─── Laboratorio ─────────────────────────────────────────────────
class ResultadoLabIn(BaseModel):
    reservorio_id: int
    parametro: str
    valor: float | None = None
    unidad: str | None = None
    dictamen: DictamenLab
    fecha_muestreo: date
    laboratorio: str | None = None


class ResultadoLabOut(ResultadoLabIn):
    model_config = ConfigDict(from_attributes=True)
    resultado_id: int
    usuario_id: int


TokenOut.model_rebuild()
