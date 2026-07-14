"""Pruebas del parser de SMS estructurado (CA-HU11)."""
import pytest

from app.routers.sync import parse_sms


def test_parse_sms_completo():
    d = parse_sms("YA;RES-001;CL:0.10;TB:8;OBS:agua turbia;UUID:abc-123")
    assert d["reservorio_codigo"] == "RES-001"
    assert d["cloro_mg_l"] == 0.10
    assert d["turbidez_unt"] == 8.0
    assert d["observaciones"] == "agua turbia"
    assert d["uuid_registro"] == "abc-123"


def test_parse_sms_minimo():
    d = parse_sms("YA;RES-002;CL:0.55")
    assert d["reservorio_codigo"] == "RES-002"
    assert d["cloro_mg_l"] == 0.55
    assert "turbidez_unt" not in d


def test_parse_sms_invalido():
    with pytest.raises(ValueError):
        parse_sms("HOLA;RES-001;CL:0.5")
