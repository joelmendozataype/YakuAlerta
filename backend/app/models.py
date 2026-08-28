"""Modelo ORM (SQLAlchemy 2.0) — las 14 tablas del modelo físico 3NF.

Los tipos ENUM ya existen en la BD (creados por db/init.sql); por eso se usa
``create_type=False`` para que SQLAlchemy no intente recrearlos.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, CHAR, Date, DateTime, ForeignKey, Integer, Numeric,
    SmallInteger, String, Text, Uuid, Enum as SAEnum, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from . import enums

# Clave primaria de 64 bits portátil: BIGINT en PostgreSQL, INTEGER en SQLite
# (SQLite solo autoincrementa columnas INTEGER PRIMARY KEY).
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


def pg_enum(py_enum, name):
    """Tipo enum portátil.

    - PostgreSQL: usa el ENUM nativo creado por db/init.sql (create_type=False).
    - SQLite: usa VARCHAR + CHECK (generado por create_all).
    """
    native = SAEnum(py_enum, name=name, create_type=False, native_enum=True,
                    values_callable=lambda e: [m.value for m in e])
    portable = SAEnum(py_enum, name=name, native_enum=False,
                      values_callable=lambda e: [m.value for m in e])
    return native.with_variant(portable, "sqlite")


class Ubigeo(Base):
    __tablename__ = "ubigeo"
    ubigeo_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_ubigeo: Mapped[str] = mapped_column(CHAR(6), unique=True)
    departamento: Mapped[str] = mapped_column(String(60), default="HUANCAVELICA")
    provincia: Mapped[str] = mapped_column(String(60))
    distrito: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    comunidades: Mapped[list["Comunidad"]] = relationship(back_populates="ubigeo")


class Comunidad(Base):
    __tablename__ = "comunidad"
    comunidad_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ubigeo_id: Mapped[int] = mapped_column(ForeignKey("ubigeo.ubigeo_id"))
    nombre: Mapped[str] = mapped_column(String(120))
    # La JASS es única por comunidad (1:1): administra el sistema de agua de
    # esa comunidad y de ninguna otra. Por eso vive aquí como atributo y no
    # como tabla aparte. La ATM agrupa todas las de su distrito.
    jass_nombre: Mapped[str | None] = mapped_column(String(120))
    latitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    poblacion_servida: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ubigeo: Mapped["Ubigeo"] = relationship(back_populates="comunidades")
    reservorios: Mapped[list["Reservorio"]] = relationship(back_populates="comunidad")


class Reservorio(Base):
    __tablename__ = "reservorio"
    reservorio_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comunidad_id: Mapped[int] = mapped_column(ForeignKey("comunidad.comunidad_id"))
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    volumen_m3: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    tipo_sistema: Mapped[str | None] = mapped_column(String(60))
    estado_infra: Mapped[str | None] = mapped_column(String(60))
    umbral_silencio_dias: Mapped[int] = mapped_column(SmallInteger, default=7)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    comunidad: Mapped["Comunidad"] = relationship(back_populates="reservorios")
    mediciones: Mapped[list["Medicion"]] = relationship(back_populates="reservorio")


class Usuario(Base):
    __tablename__ = "usuario"
    usuario_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombres: Mapped[str] = mapped_column(String(120))
    # Identificador de acceso desde la app: el DNI no cambia aunque el
    # operador cambie de número de celular, algo frecuente en zona rural.
    dni: Mapped[str | None] = mapped_column(String(8), unique=True, index=True)
    telefono: Mapped[str] = mapped_column(String(15), unique=True)
    clave_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[enums.RolUsuario] = mapped_column(pg_enum(enums.RolUsuario, "rol_usuario"))
    entidad: Mapped[str | None] = mapped_column(String(120))
    # Ámbito territorial del destinatario (RF-06): si están vacíos, el usuario
    # tiene alcance regional y recibe las alertas de todo su rol.
    ubigeo_id: Mapped[int | None] = mapped_column(ForeignKey("ubigeo.ubigeo_id"))
    comunidad_id: Mapped[int | None] = mapped_column(ForeignKey("comunidad.comunidad_id"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    asignaciones: Mapped[list["AsignacionOperador"]] = relationship(back_populates="usuario")


class AsignacionOperador(Base):
    __tablename__ = "asignacion_operador"
    asignacion_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    reservorio_id: Mapped[int] = mapped_column(ForeignKey("reservorio.reservorio_id"))
    fecha_inicio: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    fecha_fin: Mapped[date | None] = mapped_column(Date)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True)
    usuario: Mapped["Usuario"] = relationship(back_populates="asignaciones")
    reservorio: Mapped["Reservorio"] = relationship()


class ParametroNormativo(Base):
    __tablename__ = "parametro_normativo"
    parametro_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parametro: Mapped[str] = mapped_column(String(40), unique=True)
    unidad: Mapped[str] = mapped_column(String(15))
    umbral_amarillo: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    umbral_rojo: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    norma_referencia: Mapped[str] = mapped_column(String(80), default="D.S. 031-2010-SA")
    vigente: Mapped[bool] = mapped_column(Boolean, default=True)


class Medicion(Base):
    __tablename__ = "medicion"
    medicion_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    uuid_registro: Mapped[str] = mapped_column(Uuid(as_uuid=False), unique=True)
    reservorio_id: Mapped[int] = mapped_column(ForeignKey("reservorio.reservorio_id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cloro_mg_l: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    turbidez_unt: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    metodo_cloro: Mapped[enums.MetodoLectura] = mapped_column(
        pg_enum(enums.MetodoLectura, "metodo_lectura"), default=enums.MetodoLectura.MANUAL)
    observaciones: Mapped[str | None] = mapped_column(Text)
    nivel_riesgo: Mapped[enums.NivelRiesgo] = mapped_column(pg_enum(enums.NivelRiesgo, "nivel_riesgo"))
    estado_sync: Mapped[enums.EstadoSync] = mapped_column(
        pg_enum(enums.EstadoSync, "estado_sync"), default=enums.EstadoSync.PENDIENTE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reservorio: Mapped["Reservorio"] = relationship(back_populates="mediciones")
    usuario: Mapped["Usuario"] = relationship()
    evidencias: Mapped[list["EvidenciaFoto"]] = relationship(back_populates="medicion")
    recomendacion: Mapped["RecomendacionDosis"] = relationship(
        back_populates="medicion", uselist=False, foreign_keys="RecomendacionDosis.medicion_id")
    alerta: Mapped["Alerta"] = relationship(
        back_populates="medicion", uselist=False, foreign_keys="Alerta.medicion_id")


class EvidenciaFoto(Base):
    __tablename__ = "evidencia_foto"
    evidencia_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    medicion_id: Mapped[int] = mapped_column(ForeignKey("medicion.medicion_id"))
    ruta_archivo: Mapped[str] = mapped_column(String(255))
    latitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    medicion: Mapped["Medicion"] = relationship(back_populates="evidencias")


class RecomendacionDosis(Base):
    __tablename__ = "recomendacion_dosis"
    recomendacion_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    medicion_id: Mapped[int] = mapped_column(ForeignKey("medicion.medicion_id"), unique=True)
    gramos_hipoclorito: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    concentracion_insumo: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    plazo_remedicion_hrs: Mapped[int | None] = mapped_column(SmallInteger)
    protocolo: Mapped[str | None] = mapped_column(Text)
    medicion: Mapped["Medicion"] = relationship(back_populates="recomendacion", foreign_keys=[medicion_id])


class Alerta(Base):
    __tablename__ = "alerta"
    alerta_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    medicion_id: Mapped[int] = mapped_column(ForeignKey("medicion.medicion_id"), unique=True)
    nivel: Mapped[enums.NivelRiesgo] = mapped_column(pg_enum(enums.NivelRiesgo, "nivel_riesgo"))
    estado: Mapped[enums.EstadoAlerta] = mapped_column(
        pg_enum(enums.EstadoAlerta, "estado_alerta"), default=enums.EstadoAlerta.ACTIVA)
    fecha_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_cierre: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    medicion_cierre_id: Mapped[int | None] = mapped_column(ForeignKey("medicion.medicion_id"))
    resultado_cierre: Mapped[str | None] = mapped_column(String(120))
    usuario_cierre_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.usuario_id"))
    medicion: Mapped["Medicion"] = relationship(back_populates="alerta", foreign_keys=[medicion_id])
    medicion_cierre: Mapped["Medicion"] = relationship(foreign_keys=[medicion_cierre_id])
    notificaciones: Mapped[list["Notificacion"]] = relationship(back_populates="alerta")


class Notificacion(Base):
    __tablename__ = "notificacion"
    notificacion_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    alerta_id: Mapped[int] = mapped_column(ForeignKey("alerta.alerta_id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    canal: Mapped[enums.CanalNotif] = mapped_column(pg_enum(enums.CanalNotif, "canal_notif"))
    mensaje: Mapped[str] = mapped_column(Text)
    estado_entrega: Mapped[enums.EstadoNotif] = mapped_column(
        pg_enum(enums.EstadoNotif, "estado_notif"), default=enums.EstadoNotif.ENVIADO)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    alerta: Mapped["Alerta"] = relationship(back_populates="notificaciones")
    usuario: Mapped["Usuario"] = relationship()


class ResultadoLaboratorio(Base):
    __tablename__ = "resultado_laboratorio"
    resultado_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    reservorio_id: Mapped[int] = mapped_column(ForeignKey("reservorio.reservorio_id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    parametro: Mapped[str] = mapped_column(String(60))
    valor: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    unidad: Mapped[str | None] = mapped_column(String(20))
    dictamen: Mapped[enums.DictamenLab] = mapped_column(pg_enum(enums.DictamenLab, "dictamen_lab"))
    fecha_muestreo: Mapped[date] = mapped_column(Date)
    laboratorio: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reservorio: Mapped["Reservorio"] = relationship()


class Reporte(Base):
    __tablename__ = "reporte"
    reporte_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    ubigeo_id: Mapped[int] = mapped_column(ForeignKey("ubigeo.ubigeo_id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    periodo: Mapped[str] = mapped_column(String(7))
    formato: Mapped[str] = mapped_column(String(5), default="PDF")
    ruta_archivo: Mapped[str | None] = mapped_column(String(255))
    fecha_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SesionQR(Base):
    """Vinculación efímera web↔móvil por código QR (patrón WhatsApp/Discord Web).

    El ``token`` es el secreto público que viaja en el QR. El ``client_hash``
    ata la sesión al navegador que la generó: solo quien conserva el secreto de
    cliente original puede reclamar el acceso, aunque un tercero fotografíe el QR.
    """
    __tablename__ = "sesion_qr"
    sesion_qr_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    client_hash: Mapped[str] = mapped_column(String(64))
    estado: Mapped[enums.EstadoQR] = mapped_column(
        pg_enum(enums.EstadoQR, "estado_qr"), default=enums.EstadoQR.PENDIENTE)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.usuario_id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    escaneado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resuelto_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_origen: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    usuario: Mapped["Usuario"] = relationship()


class RecuperacionClave(Base):
    """Código de un solo uso para restablecer la clave (HU-01, RNF-05).

    El código viaja por SMS al celular registrado y **se guarda cifrado**: si
    alguien leyera la base de datos no podría usarlo. Vence a los 10 minutos y
    admite un número acotado de intentos.
    """
    __tablename__ = "recuperacion_clave"
    recuperacion_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    codigo_hash: Mapped[str] = mapped_column(String(255))
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    usado: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip_origen: Mapped[str | None] = mapped_column(String(45))
    usuario: Mapped["Usuario"] = relationship()


class Auditoria(Base):
    __tablename__ = "auditoria"
    auditoria_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.usuario_id"))
    accion: Mapped[str] = mapped_column(String(60))
    entidad_afectada: Mapped[str | None] = mapped_column(String(60))
    registro_id: Mapped[str | None] = mapped_column(String(60))
    detalle: Mapped[str | None] = mapped_column(Text)
    ip_origen: Mapped[str | None] = mapped_column(String(45))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
