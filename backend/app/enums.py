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


class GrupoRol(str, enum.Enum):
    """Grupo de rol que el usuario elige al ingresar.

    Agrupa los roles internos en las categorías que la gente reconoce. La app
    ofrece las cuatro de campo; el tablero web añade los perfiles regionales,
    que trabajan en oficina.
    """
    JASS = "JASS"                   # Vigilancia del agua
    ATM = "ATM"                     # Autoridad local
    IPRESS_SALUD = "IPRESS_SALUD"   # Establecimiento de salud
    USUARIO = "USUARIO"             # Población usuaria
    # Perfiles regionales: solo ingresan por el tablero web.
    DESA = "DESA"                   # Autoridad sanitaria regional
    DRVCS = "DRVCS"                 # Rectoría regional del saneamiento
    ADMIN = "ADMIN"                 # Administración del sistema


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


# ── Correspondencia grupo (lo que elige el usuario) → roles internos ──
ROLES_POR_GRUPO: dict[GrupoRol, tuple[RolUsuario, ...]] = {
    GrupoRol.JASS: (RolUsuario.OPERADOR, RolUsuario.DIRECTIVO_JASS),
    GrupoRol.ATM: (RolUsuario.ATM, RolUsuario.AUTORIDAD_LOCAL),
    GrupoRol.IPRESS_SALUD: (RolUsuario.SALUD,),
    GrupoRol.USUARIO: (RolUsuario.POBLACION,),
    GrupoRol.DESA: (RolUsuario.DESA,),
    GrupoRol.DRVCS: (RolUsuario.DRVCS,),
    GrupoRol.ADMIN: (RolUsuario.ADMIN,),
}


def grupo_de_rol(rol: RolUsuario) -> GrupoRol | None:
    """Grupo al que pertenece un rol interno (None si no se ofrece en la app)."""
    for grupo, roles in ROLES_POR_GRUPO.items():
        if rol in roles:
            return grupo
    return None


# ── Los siete actores del sistema ────────────────────────────────
# Cada grupo es un actor. Dos superficies, y quien está en las dos lo está
# porque su trabajo ocurre en ambos sitios: la ATM y Salud verifican en campo
# y deciden en oficina.
GRUPOS_DE_LA_APP: frozenset[GrupoRol] = frozenset({
    GrupoRol.JASS, GrupoRol.ATM, GrupoRol.IPRESS_SALUD, GrupoRol.USUARIO,
})

# Nombre con el que cada actor se presenta, el orden en que se listan y el rol
# con el que se da de alta una cuenta suya.
#
# Dos actores admiten un segundo rol —la JASS tiene directivos y la ATM
# autoridades locales— pero registrar una cuenta no obliga a elegir entre
# ellos: se da de alta el rol principal, que es el que trabaja a diario. Los
# otros siguen siendo válidos y reciben la alerta roja; cuando el piloto los
# necesite, se ajustan sobre la cuenta ya creada.
ACTORES: tuple[tuple[GrupoRol, str, RolUsuario], ...] = (
    (GrupoRol.JASS, "JASS", RolUsuario.OPERADOR),
    (GrupoRol.ATM, "ATM", RolUsuario.ATM),
    (GrupoRol.IPRESS_SALUD, "IPRESS / Salud", RolUsuario.SALUD),
    (GrupoRol.USUARIO, "Usuario / vecino", RolUsuario.POBLACION),
    (GrupoRol.DESA, "DESA", RolUsuario.DESA),
    (GrupoRol.DRVCS, "DRVCS", RolUsuario.DRVCS),
    (GrupoRol.ADMIN, "Administrador", RolUsuario.ADMIN),
)


# ── Quién trabaja en el tablero web ──────────────────────────────
# El tablero es de quien decide desde una oficina. Quedan fuera dos grupos, y
# por razones distintas:
#
#   JASS      opera en el cerro, sin señal y sin computadora: todo su trabajo
#             ocurre en la app móvil, offline.
#   USUARIO   el vecino no necesita cuenta para saber si puede beber el agua.
#             Escanea el QR del aviso fijado en el punto de agua y lee la
#             página pública, sin registrarse. Su rol existe para *recibir* la
#             alerta roja en el celular, no para navegar un tablero.
GRUPOS_DEL_TABLERO: frozenset[GrupoRol] = frozenset({
    GrupoRol.ATM, GrupoRol.IPRESS_SALUD,
    GrupoRol.DESA, GrupoRol.DRVCS, GrupoRol.ADMIN,
})


def usa_el_tablero(rol: RolUsuario) -> bool:
    """¿Este rol tiene algo que hacer en el tablero web?"""
    grupo = grupo_de_rol(rol)
    return grupo is not None and grupo in GRUPOS_DEL_TABLERO
