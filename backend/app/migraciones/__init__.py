"""Ajustes de esquema que ``create_all`` no puede hacer por sí solo.

SQLAlchemy crea las tablas que faltan, pero no altera las que ya existen. Lo
que se agrega a una tabla viva vive aquí, y se ejecuta al arrancar.
"""
from .evidencia_en_base import migrar as migrar_evidencia_a_base

__all__ = ["migrar_evidencia_a_base"]
