"""Pipeline central: clasificar → recomendar → alertar → notificar.

Usado tanto por el registro directo (`/mediciones`) como por la
sincronización por lotes (`/sync`). Es el punto único donde una medición
se convierte en decisión y acción, garantizando consistencia.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..enums import CanalNotif, EstadoAlerta, EstadoSync, NivelRiesgo, RolUsuario
from ..models import (
    Alerta, AsignacionOperador, Comunidad, Medicion, Notificacion,
    ParametroNormativo, RecomendacionDosis, Reservorio, Usuario,
)
from ..rules import Umbrales, calcular_dosis, clasificar, destinatarios_para
from ..rules.escalamiento import ambito_de
from . import notificaciones as notif

# Severidad para decidir si una alerta abierta debe escalar.
_SEVERIDAD = {NivelRiesgo.VERDE: 0, NivelRiesgo.AMARILLO: 1, NivelRiesgo.ROJO: 2}


def cargar_umbrales(db: Session) -> Umbrales:
    """Lee los umbrales configurables de ``parametro_normativo`` (RNF-07)."""
    filas = {p.parametro: p for p in db.query(ParametroNormativo).filter_by(vigente=True)}
    cloro = filas.get("cloro_residual")
    turb = filas.get("turbidez")
    return Umbrales(
        cloro_verde=float(cloro.umbral_amarillo) if cloro and cloro.umbral_amarillo else 0.50,
        cloro_rojo=float(cloro.umbral_rojo) if cloro and cloro.umbral_rojo else 0.30,
        turbidez_rojo=float(turb.umbral_rojo) if turb and turb.umbral_rojo else 5.0,
    )


def _hay_lab_no_conforme_abierto(db: Session, reservorio_id: int) -> bool:
    """Un dictamen de laboratorio NO CONFORME fuerza rojo hasta el cierre (RF-15)."""
    from ..models import ResultadoLaboratorio
    from ..enums import DictamenLab

    q = (
        db.query(ResultadoLaboratorio)
        .filter(ResultadoLaboratorio.reservorio_id == reservorio_id)
        .filter(ResultadoLaboratorio.dictamen == DictamenLab.NO_CONFORME)
    )
    return db.query(q.exists()).scalar()


def procesar_medicion(db: Session, medicion: Medicion) -> Alerta | None:
    """Clasifica la medición, genera recomendación y, si aplica, alerta+notifica.

    La ``medicion`` ya debe estar añadida a la sesión (con reservorio_id válido).
    Devuelve la alerta generada o ``None`` para nivel verde. No hace commit.
    """
    umbrales = cargar_umbrales(db)
    reservorio = db.get(Reservorio, medicion.reservorio_id)
    lab_no_conforme = _hay_lab_no_conforme_abierto(db, medicion.reservorio_id)

    resultado = clasificar(
        cloro_mg_l=float(medicion.cloro_mg_l) if medicion.cloro_mg_l is not None else None,
        turbidez_unt=float(medicion.turbidez_unt) if medicion.turbidez_unt is not None else None,
        observaciones=medicion.observaciones,
        lab_no_conforme=lab_no_conforme,
        umbrales=umbrales,
    )
    medicion.nivel_riesgo = resultado.nivel
    db.flush()  # asegura medicion_id

    # ── Recomendación de dosis (amarillo/rojo) ───────────────────
    reco = calcular_dosis(
        nivel=resultado.nivel,
        volumen_m3=float(reservorio.volumen_m3),
        cloro_medido=float(medicion.cloro_mg_l) if medicion.cloro_mg_l is not None else None,
        concentracion_insumo=70.0,
    )
    if reco is not None:
        db.add(RecomendacionDosis(
            medicion_id=medicion.medicion_id,
            gramos_hipoclorito=reco.gramos_hipoclorito,
            concentracion_insumo=reco.concentracion_insumo,
            plazo_remedicion_hrs=reco.plazo_remedicion_hrs,
            protocolo=reco.protocolo,
        ))

    # ── Verde: sin alerta ni notificación (regla antifatiga) ─────
    if resultado.nivel == NivelRiesgo.VERDE:
        return None

    # ── Agrupación: si el reservorio ya tiene un caso abierto, no se
    #    crea una alerta nueva ni se vuelve a notificar (evita alarmas
    #    injustificadas). Solo se notifica cuando el riesgo ESCALA.
    abierta = (
        db.query(Alerta)
        .join(Medicion, Alerta.medicion_id == Medicion.medicion_id)
        .filter(Medicion.reservorio_id == medicion.reservorio_id)
        .filter(Alerta.estado.in_([EstadoAlerta.ACTIVA, EstadoAlerta.EN_PROCESO]))
        .order_by(Alerta.fecha_generacion.desc())
        .first()
    )
    if abierta is not None:
        if _SEVERIDAD[resultado.nivel] > _SEVERIDAD[abierta.nivel]:
            abierta.nivel = resultado.nivel          # amarillo → rojo
            _notificar(db, abierta, medicion, reservorio,
                       protocolo=reco.protocolo if reco else None)
        return abierta

    # ── Alerta nueva ─────────────────────────────────────────────
    alerta = Alerta(
        medicion_id=medicion.medicion_id,
        nivel=resultado.nivel,
        estado=EstadoAlerta.ACTIVA,
    )
    db.add(alerta)
    db.flush()

    # ── Notificaciones según matriz de escalamiento ─────────────
    _notificar(db, alerta, medicion, reservorio,
               protocolo=reco.protocolo if reco else None)
    return alerta


def _destinatarios(db: Session, roles: list[RolUsuario], comunidad: Comunidad | None,
                   reservorio: Reservorio) -> list[Usuario]:
    """Usuarios a notificar, filtrados por rol y por jurisdicción territorial.

    Un usuario sin ámbito territorial declarado (ubigeo/comunidad vacíos) se
    considera de alcance regional y siempre recibe la alerta de su rol.
    """
    seleccion: list[Usuario] = []
    for rol in roles:
        candidatos = (
            db.query(Usuario)
            .filter(Usuario.rol == rol, Usuario.activo.is_(True))
            .all()
        )
        ambito = ambito_de(rol)
        for u in candidatos:
            if rol == RolUsuario.OPERADOR:
                # El operador se determina por su asignación vigente al reservorio.
                asignado = (
                    db.query(AsignacionOperador)
                    .filter_by(usuario_id=u.usuario_id,
                               reservorio_id=reservorio.reservorio_id, vigente=True)
                    .first()
                )
                if asignado:
                    seleccion.append(u)
            elif ambito == "comunidad":
                if u.comunidad_id is None or (comunidad and u.comunidad_id == comunidad.comunidad_id):
                    seleccion.append(u)
            elif ambito == "distrito":
                if u.ubigeo_id is None or (comunidad and u.ubigeo_id == comunidad.ubigeo_id):
                    seleccion.append(u)
            else:  # regional
                seleccion.append(u)
    return seleccion


def _notificar(db: Session, alerta: Alerta, medicion: Medicion,
               reservorio: Reservorio, protocolo: str | None) -> None:
    comunidad = db.get(Comunidad, reservorio.comunidad_id)
    roles = destinatarios_para(alerta.nivel)
    if not roles:
        return

    nombre_comunidad = comunidad.nombre if comunidad else "—"

    # Mensaje institucional (con valores y protocolo)
    mensaje_inst = notif.componer_mensaje_alerta(
        nivel=alerta.nivel.value,
        comunidad=nombre_comunidad,
        reservorio=reservorio.codigo,
        cloro=float(medicion.cloro_mg_l) if medicion.cloro_mg_l is not None else None,
        turbidez=float(medicion.turbidez_unt) if medicion.turbidez_unt is not None else None,
        protocolo=protocolo,
        medicion_id=medicion.medicion_id,
    )
    # Aviso a la población (lenguaje llano, sin cifras técnicas)
    mensaje_pob = notif.componer_mensaje_poblacion(alerta.nivel.value, nombre_comunidad)

    for u in _destinatarios(db, roles, comunidad, reservorio):
        es_poblacion = u.rol == RolUsuario.POBLACION
        mensaje = mensaje_pob if es_poblacion else mensaje_inst
        # El SMS es el canal garantizado en zonas sin datos (operador y población).
        canal = (CanalNotif.SMS
                 if u.rol in (RolUsuario.OPERADOR, RolUsuario.POBLACION)
                 else CanalNotif.WHATSAPP)
        estado = notif.enviar(canal, u.telefono, mensaje)
        db.add(Notificacion(
            alerta_id=alerta.alerta_id, usuario_id=u.usuario_id,
            canal=canal, mensaje=mensaje, estado_entrega=estado,
        ))
