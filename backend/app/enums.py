"""Dominios controlados del negocio (espejo de los ENUM de PostgreSQL)."""
import enum


class RolUsuario(str, enum.Enum):
    OPERADOR = "OPERADOR"
    DIRECTIVO_JASS = "DIRECTIVO_JASS"
    ATM = "ATM"
    DESA = "DESA"
    SALUD = "SALUD"
    ADMIN = "ADMIN"


class NivelRiesgo(str, enum.Enum):
    VERDE = "VERDE"
    AMARILLO = "AMARILLO"
    ROJO = "ROJO"


class MetodoLectura(str, enum.Enum):
    CAMARA_DPD = "CAMARA_DPD"
    MANUAL = "MANUAL"


class EstadoSync(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    ENVIADO_SMS = "ENVIADO_SMS"
    SINCRONIZADO = "SINCRONIZADO"


class EstadoAlerta(str, enum.Enum):
    ACTIVA = "ACTIVA"
    EN_PROCESO = "EN_PROCESO"
    CERRADA = "CERRADA"


class CanalNotif(str, enum.Enum):
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    APP = "APP"


class EstadoNotif(str, enum.Enum):
    ENVIADO = "ENVIADO"
    ENTREGADO = "ENTREGADO"
    FALLIDO = "FALLIDO"


class DictamenLab(str, enum.Enum):
    CONFORME = "CONFORME"
    NO_CONFORME = "NO_CONFORME"
