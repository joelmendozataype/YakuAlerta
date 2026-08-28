"""Código de un reservorio — estructura R{n}-{DISTRITO}-{COMUNIDAD}.

El código no se escribe a mano. Es el rótulo con el que la JASS identifica el
tanque en campo y con el que la ATM lo busca en el tablero: si cada quien lo
teclea a su manera, deja de servir para lo único que existe.

    R1-LIRCAY-COM-01
    │  │      └── comunidad a la que pertenece
    │  └───────── distrito
    └──────────── correlativo dentro del distrito

El correlativo es por distrito, no por comunidad: así el número identifica al
reservorio dentro de la jurisdicción que lo administra.
"""
import re
import unicodedata

from sqlalchemy.orm import Session

from ..models import Comunidad, Reservorio, Ubigeo


def _normalizar(texto: str) -> str:
    """Deja el texto apto para un código: sin tildes, sin espacios sueltos."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    limpio = re.sub(r"[^A-Za-z0-9-]+", "-", sin_tildes.upper()).strip("-")
    return re.sub(r"-{2,}", "-", limpio)


def siguiente_codigo(db: Session, comunidad: Comunidad) -> str:
    """Arma el código del próximo reservorio de esa comunidad."""
    ubigeo = db.get(Ubigeo, comunidad.ubigeo_id)
    distrito = _normalizar(ubigeo.distrito if ubigeo else "SIN-DISTRITO")

    # Correlativo dentro del distrito: se cuentan los reservorios de todas sus
    # comunidades, no solo los de esta.
    usados = (
        db.query(Reservorio)
        .join(Comunidad, Reservorio.comunidad_id == Comunidad.comunidad_id)
        .filter(Comunidad.ubigeo_id == comunidad.ubigeo_id)
        .count()
    )

    # Si un código ya existiera —por una carga previa o un borrado—, se avanza
    # hasta encontrar uno libre en vez de fallar con un choque de unicidad.
    comunidad_norm = _normalizar(comunidad.nombre)
    n = usados + 1
    while True:
        codigo = f"R{n}-{distrito}-{comunidad_norm}"
        if not db.query(Reservorio).filter_by(codigo=codigo).first():
            return codigo
        n += 1
