"""Construcción del perfil que la app recibe al iniciar sesión."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Comunidad, Ubigeo, Usuario
from ..schemas import UsuarioOut


def perfil_de(db: Session, usuario: Usuario) -> UsuarioOut:
    """Añade el territorio del usuario para encabezar las pantallas."""
    salida = UsuarioOut.model_validate(usuario)

    # El distrito puede venir de su ámbito directo o del de su comunidad.
    comunidad = db.get(Comunidad, usuario.comunidad_id) if usuario.comunidad_id else None
    ubigeo_id = usuario.ubigeo_id or (comunidad.ubigeo_id if comunidad else None)
    ubigeo = db.get(Ubigeo, ubigeo_id) if ubigeo_id else None

    if ubigeo:
        salida.departamento = ubigeo.departamento
        salida.provincia = ubigeo.provincia
        salida.distrito = ubigeo.distrito
    if comunidad:
        salida.comunidad = comunidad.nombre
    return salida
