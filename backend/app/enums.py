"""Dominios controlados del negocio (espejo de los ENUM de PostgreSQL)."""
import enum


class RolUsuario(str, enum.Enum):
    OPERADOR = "OPERADOR"
    DIRECTIVO_JASS = "DIRECTIVO_JASS"
    ATM = "ATM"
    DESA = "DESA"
    SALUD = "SALUD"
    ADMIN = "ADMIN"
    # Usuarios principales exigidos por las bases del Desafío 2
    AUTORIDAD_LOCAL = "AUTORIDAD_LOCAL"   # autoridad comunal / municipal
    DRVCS = "DRVCS"                       # Dir. Reg. Vivienda, Construcción y Saneamiento
    POBLACION = "POBLACION"               # contacto comunitario (difusión a la población)


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


class EstadoQR(str, enum.Enum):
    """Ciclo de vida de una sesión de vinculación por código QR."""
    PENDIENTE = "PENDIENTE"    # QR mostrado en la web, aún sin escanear
    ESCANEADO = "ESCANEADO"    # la app lo leyó; espera confirmación del usuario
    APROBADO = "APROBADO"      # el usuario confirmó; la web puede reclamar el token
    RECHAZADO = "RECHAZADO"    # el usuario canceló desde la app
    CONSUMIDA = "CONSUMIDA"    # la web ya reclamó la sesión: dispositivo vinculado y activo
    REVOCADA = "REVOCADA"      # el usuario cerró la sesión de ese dispositivo desde la app
    EXPIRADO = "EXPIRADO"      # venció el plazo sin completarse
