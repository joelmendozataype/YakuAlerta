"""Gestión de entidades del sistema — HU-04 / RF-01, RF-04.

Alta de comunidades, reservorios, usuarios y asignaciones operador↔reservorio.

Quién administra
----------------
El **Área Técnica Municipal (ATM)** administra su distrito: es quien conoce a
las JASS, visita los reservorios y mantiene el directorio al día. El rol ADMIN
conserva el alcance regional para la configuración transversal.

Dos salvaguardas sostienen esa delegación (RNF-05, mínimo privilegio):

1. **Ámbito territorial**: la ATM solo ve y crea entidades de su propio
   distrito; no puede tocar las de otro.
2. **Sin escalamiento de privilegios**: la ATM da de alta perfiles de campo
   (operador, directivo JASS, autoridad local y contacto comunitario), pero no
   cuentas regionales (DESA, DRVCS) ni administradores.
"""
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import requiere_roles
from ..enums import (
    ACTORES, GRUPOS_DEL_TABLERO, GRUPOS_DE_LA_APP, ROLES_POR_GRUPO, RolUsuario,
)
from ..models import (
    AsignacionOperador, Comunidad, Reservorio, Ubigeo, Usuario,
)
from ..schemas import (
    ActorOut, ClaveTemporalOut, ComunidadIn, ComunidadOut, JassOut, ReservorioIn,
    ReservorioOut, UbigeoOut, UsuarioIn, UsuarioOut, UsuarioPatch,
)
from ..rules.escalamiento import ambito_de
from ..services.codigo_reservorio import siguiente_codigo
from ..services.identidad import entidad_de, exigir_territorio, resolver_comunidad
from ..services.directorio_jass import listar_jass
from ..services.perfil import perfil_de
from ..models import Auditoria
from ..security import hash_clave

router = APIRouter(prefix="/admin", tags=["admin"])

# La ATM administra su distrito; el ADMIN, todo el ámbito regional.
_administra = requiere_roles(RolUsuario.ATM, RolUsuario.ADMIN)

# Perfiles de campo que la ATM puede dar de alta.
ROLES_QUE_CREA_LA_ATM = {
    RolUsuario.OPERADOR,
    RolUsuario.DIRECTIVO_JASS,
    RolUsuario.AUTORIDAD_LOCAL,
    RolUsuario.POBLACION,
}


def _es_regional(usuario: Usuario) -> bool:
    """El ADMIN (y cualquier cuenta sin distrito) trabaja sin restricción."""
    return usuario.rol == RolUsuario.ADMIN or usuario.ubigeo_id is None


def _exige_su_distrito(usuario: Usuario, ubigeo_id: int | None) -> None:
    """Impide que una ATM administre entidades de otro distrito."""
    if _es_regional(usuario):
        return
    if ubigeo_id != usuario.ubigeo_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo puede administrar entidades de su propio distrito.",
        )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, f"Violación de integridad: {e.orig}")


def _muestra(db: Session, rol: RolUsuario,
             quien: Usuario) -> tuple[Comunidad | None, Ubigeo | None]:
    """Territorio de muestra para ilustrar cómo se nombrará la entidad.

    Quien administra un distrito ve el suyo; el ADMIN, que no tiene distrito
    propio, ve el primero de la región para que el ejemplo sea concreto en vez
    de decir «su distrito».
    """
    ambito = ambito_de(rol)
    if ambito == "regional":
        return None, None

    ubigeo = (db.get(Ubigeo, quien.ubigeo_id) if quien.ubigeo_id
              else db.query(Ubigeo).order_by(Ubigeo.codigo_ubigeo).first())
    if ambito != "comunidad":
        return None, ubigeo

    q = db.query(Comunidad)
    if ubigeo:
        q = q.filter(Comunidad.ubigeo_id == ubigeo.ubigeo_id)
    return q.order_by(Comunidad.nombre).first(), ubigeo


# ─── Los actores del sistema ────────────────────────────────────
@router.get("/actores", response_model=list[ActorOut])
def listar_actores(db: Session = Depends(get_db),
                   usuario: Usuario = Depends(_administra)):
    """Los siete actores, con dónde entra cada uno y cuántas cuentas tiene.

    El catálogo no se escribe aquí: sale de la misma declaración que gobierna
    las dos pantallas de ingreso, para que el panel no pueda quedar contando
    una cosa mientras el login ofrece otra.
    """
    q = db.query(Usuario)
    if not _es_regional(usuario):
        q = q.filter(Usuario.ubigeo_id == usuario.ubigeo_id)
    cuentas = q.all()

    salida: list[ActorOut] = []
    for orden, (grupo, nombre, principal) in enumerate(ACTORES, start=1):
        roles = ROLES_POR_GRUPO[grupo]
        suyas = [u for u in cuentas if u.rol in roles]
        salida.append(ActorOut(
            orden=orden, grupo=grupo, actor=nombre, rol_principal=principal,
            movil=grupo in GRUPOS_DE_LA_APP,
            tablero=grupo in GRUPOS_DEL_TABLERO,
            roles=list(roles),
            ambito=ambito_de(principal),
            entidad_ejemplo=entidad_de(db, principal, *_muestra(db, principal, usuario)),
            cuentas=len(suyas),
            activas=sum(1 for u in suyas if u.activo),
        ))
    return salida


# ─── Directorio de JASS ─────────────────────────────────────────
@router.get("/jass", response_model=list[JassOut])
def directorio_jass(db: Session = Depends(get_db),
                    usuario: Usuario = Depends(_administra)):
    """Las JASS del distrito de la ATM.

    Una JASS por comunidad; la ATM acompaña a todas las de su distrito y ve de
    un vistazo cuál dejó de reportar y cuál tiene el agua en rojo.
    """
    return listar_jass(db, None if _es_regional(usuario) else usuario.ubigeo_id)


# ─── Ubigeo ──────────────────────────────────────────────────────
@router.get("/ubigeos", response_model=list[UbigeoOut])
def listar_ubigeos(db: Session = Depends(get_db),
                   usuario: Usuario = Depends(_administra)):
    q = db.query(Ubigeo).order_by(Ubigeo.distrito)
    if not _es_regional(usuario):
        q = q.filter(Ubigeo.ubigeo_id == usuario.ubigeo_id)
    return [UbigeoOut.model_validate(u) for u in q]


# ─── Comunidades ─────────────────────────────────────────────────
@router.get("/comunidades", response_model=list[ComunidadOut])
def listar_comunidades(db: Session = Depends(get_db),
                       usuario: Usuario = Depends(_administra)):
    q = (db.query(Comunidad, Ubigeo)
           .join(Ubigeo, Comunidad.ubigeo_id == Ubigeo.ubigeo_id)
           .order_by(Ubigeo.provincia, Ubigeo.distrito, Comunidad.nombre))
    if not _es_regional(usuario):
        q = q.filter(Comunidad.ubigeo_id == usuario.ubigeo_id)
    # Con su territorio: el nombre de una comunidad solo distingue dentro de
    # su distrito, y el ADMIN las ve de todos.
    return [
        ComunidadOut.model_validate(c).model_copy(
            update={"provincia": u.provincia, "distrito": u.distrito})
        for c, u in q
    ]


@router.post("/comunidades", response_model=ComunidadOut, status_code=201)
def crear_comunidad(datos: ComunidadIn, db: Session = Depends(get_db),
                    usuario: Usuario = Depends(_administra)):
    _exige_su_distrito(usuario, datos.ubigeo_id)
    c = Comunidad(**datos.model_dump())
    db.add(c)
    _commit(db)
    db.refresh(c)
    return ComunidadOut.model_validate(c)


# ─── Reservorios ─────────────────────────────────────────────────
@router.get("/reservorios", response_model=list[ReservorioOut])
def listar_reservorios(db: Session = Depends(get_db),
                       usuario: Usuario = Depends(_administra)):
    q = db.query(Reservorio).order_by(Reservorio.codigo)
    if not _es_regional(usuario):
        q = (q.join(Comunidad, Reservorio.comunidad_id == Comunidad.comunidad_id)
              .filter(Comunidad.ubigeo_id == usuario.ubigeo_id))
    return [ReservorioOut.model_validate(r) for r in q]


@router.post("/reservorios", response_model=ReservorioOut, status_code=201)
def crear_reservorio(datos: ReservorioIn, db: Session = Depends(get_db),
                     usuario: Usuario = Depends(_administra)):
    comunidad = db.get(Comunidad, datos.comunidad_id)
    if not comunidad:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comunidad no encontrada")
    _exige_su_distrito(usuario, comunidad.ubigeo_id)

    campos = datos.model_dump()
    # El código lo arma el servidor con la estructura acordada; solo se respeta
    # el enviado si viene explícito (migraciones o cargas históricas).
    campos["codigo"] = campos.get("codigo") or siguiente_codigo(db, comunidad)

    r = Reservorio(**campos)
    db.add(r)
    _commit(db)
    db.refresh(r)
    return ReservorioOut.model_validate(r)


# ─── Usuarios ────────────────────────────────────────────────────
@router.get("/usuarios", response_model=list[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db),
                    usuario: Usuario = Depends(_administra)):
    q = db.query(Usuario).order_by(Usuario.nombres)
    if not _es_regional(usuario):
        q = q.filter(Usuario.ubigeo_id == usuario.ubigeo_id)
    # Con el territorio resuelto: el padrón se lee por comunidad y distrito,
    # no por un identificador numérico.
    return [perfil_de(db, u) for u in q]


@router.post("/usuarios", response_model=UsuarioOut, status_code=201)
def crear_usuario(datos: UsuarioIn, db: Session = Depends(get_db),
                  usuario: Usuario = Depends(_administra)):
    if not _es_regional(usuario):
        # La ATM no puede crear cuentas de rango igual o superior al suyo.
        if datos.rol not in ROLES_QUE_CREA_LA_ATM:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"La ATM puede registrar perfiles de campo "
                f"({', '.join(sorted(r.value for r in ROLES_QUE_CREA_LA_ATM))}). "
                f"Las cuentas regionales las crea la DIRESA/DESA.",
            )
        # La cuenta nace en el distrito de quien la registra.
        datos.ubigeo_id = usuario.ubigeo_id

    # La comunidad puede llegar escrita a mano: si aún no existe en ese
    # distrito, nace con su JASS y su primer reservorio.
    creada = reservorio = None
    if datos.comunidad_id is None and datos.comunidad_nombre:
        comunidad, nueva, reservorio = resolver_comunidad(
            db, datos.ubigeo_id, datos.comunidad_nombre, datos.rol)
        datos.comunidad_id = comunidad.comunidad_id
        creada = comunidad.nombre if nueva else None

    # El territorio que exige su ámbito, y la entidad que de él se desprende.
    exigir_territorio(datos.rol, datos.comunidad_id)
    comunidad = db.get(Comunidad, datos.comunidad_id) if datos.comunidad_id else None
    if comunidad is not None and datos.ubigeo_id is None:
        datos.ubigeo_id = comunidad.ubigeo_id
    ubigeo = db.get(Ubigeo, datos.ubigeo_id) if datos.ubigeo_id else None

    u = Usuario(
        nombres=datos.nombres, dni=datos.dni, telefono=datos.telefono,
        clave_hash=hash_clave(datos.clave), rol=datos.rol,
        entidad=datos.entidad or entidad_de(db, datos.rol, comunidad, ubigeo),
        ubigeo_id=datos.ubigeo_id, comunidad_id=datos.comunidad_id,
    )
    db.add(u)
    _commit(db)
    db.refresh(u)

    salida = perfil_de(db, u)
    salida.comunidad_creada = creada
    salida.reservorio_creado = reservorio.codigo if reservorio and creada else None
    return salida


# ─── Asignaciones operador ↔ reservorio ─────────────────────────
@router.post("/asignaciones", status_code=201)
def asignar_operador(usuario_id: int, reservorio_id: int,
                     db: Session = Depends(get_db),
                     usuario: Usuario = Depends(_administra)):
    operador = db.get(Usuario, usuario_id)
    if not operador or operador.rol != RolUsuario.OPERADOR:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El usuario debe existir y ser OPERADOR")

    reservorio = db.get(Reservorio, reservorio_id)
    if not reservorio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservorio no encontrado")
    comunidad = db.get(Comunidad, reservorio.comunidad_id)
    _exige_su_distrito(usuario, comunidad.ubigeo_id if comunidad else None)

    a = AsignacionOperador(usuario_id=usuario_id, reservorio_id=reservorio_id)
    db.add(a)
    _commit(db)
    return {"asignacion_id": a.asignacion_id, "usuario_id": usuario_id,
            "reservorio_id": reservorio_id}


# ─── Corrección de cuentas ya creadas ───────────────────────────
def _exige_poder_sobre(quien: Usuario, objetivo: Usuario) -> None:
    """Quién puede tocar la cuenta de quién.

    Tres reglas, en orden: nadie se desactiva a sí mismo (dejaría el sistema
    sin quien lo administre), la ATM no sale de su distrito y la ATM no toca
    cuentas de rango igual o superior al suyo.
    """
    if quien.usuario_id == objetivo.usuario_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No puede modificar su propia cuenta desde aquí.",
        )
    if _es_regional(quien):
        return
    _exige_su_distrito(quien, objetivo.ubigeo_id)
    if objetivo.rol not in ROLES_QUE_CREA_LA_ATM:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Esa cuenta es de ámbito regional: la administra la DIRESA/DESA.",
        )


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioOut)
def corregir_usuario(usuario_id: int, datos: UsuarioPatch,
                     db: Session = Depends(get_db),
                     usuario: Usuario = Depends(_administra)):
    """Corrige los datos de una cuenta, o la activa y desactiva.

    Desactivar es la baja: un operador que deja la JASS conserva su historial
    de mediciones —no se borra nada— pero deja de poder entrar.
    """
    objetivo = db.get(Usuario, usuario_id)
    if objetivo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    _exige_poder_sobre(usuario, objetivo)

    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No hay nada que corregir.")
    for campo, valor in cambios.items():
        setattr(objetivo, campo, valor)

    db.add(Auditoria(
        usuario_id=usuario.usuario_id,
        accion="BAJA_USUARIO" if cambios.get("activo") is False else "EDITA_USUARIO",
        entidad_afectada="usuario", registro_id=str(objetivo.usuario_id),
    ))
    _commit(db)
    db.refresh(objetivo)
    return perfil_de(db, objetivo)


@router.post("/usuarios/{usuario_id}/clave", response_model=ClaveTemporalOut)
def restablecer_clave(usuario_id: int, db: Session = Depends(get_db),
                      usuario: Usuario = Depends(_administra)):
    """Genera una clave provisional para entregarla en mano.

    Se muestra una sola vez a quien administra: no queda guardada en claro en
    ningún lado. Es la salida para el operador que olvidó su clave y no tiene
    señal para recibir el código de recuperación por SMS.
    """
    objetivo = db.get(Usuario, usuario_id)
    if objetivo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    _exige_poder_sobre(usuario, objetivo)

    temporal = f"yaku{secrets.randbelow(1_000_000):06d}"
    objetivo.clave_hash = hash_clave(temporal)
    db.add(Auditoria(
        usuario_id=usuario.usuario_id, accion="RESET_CLAVE",
        entidad_afectada="usuario", registro_id=str(objetivo.usuario_id),
    ))
    _commit(db)
    return ClaveTemporalOut(usuario_id=objetivo.usuario_id,
                            nombres=objetivo.nombres, clave_temporal=temporal)
