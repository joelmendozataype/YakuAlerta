"""Esquemas Pydantic (contratos de la API REST)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from .enums import (
    CanalNotif, DictamenLab, EstadoAlerta, EstadoNotif, EstadoSync,
    MetodoLectura, NivelRiesgo, RolUsuario,
)


# ─── Auth ────────────────────────────────────────────────────────
class LoginIn(BaseModel):
    telefono: str = Field(examples=["987654321"])
    clave: str = Field(examples=["yaku2026"])


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    usuario_id: int
    nombres: str
    telefono: str
    rol: RolUsuario
    entidad: str | None = None
    ubigeo_id: int | None = None
    comunidad_id: int | None = None
    activo: bool = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
    reservorios: list[ReservorioOut] = []


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
    latitud: float | None = None
    longitud: float | None = None
    poblacion_servida: int | None = None


class ComunidadOut(ComunidadIn):
    model_config = ConfigDict(from_attributes=True)
    comunidad_id: int


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
    telefono: str
    clave: str
    rol: RolUsuario
    entidad: str | None = None
    # Ámbito territorial (RF-06). Vacíos = alcance regional.
    ubigeo_id: int | None = None
    comunidad_id: int | None = None


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


class TableroResumen(BaseModel):
    distrito: str
    sistemas_monitoreados: int
    porcentaje_agua_segura: float
    alertas_activas: int
    reservorios_en_silencio: int
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
