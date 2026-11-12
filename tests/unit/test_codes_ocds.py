"""Reglas de códigos CPC y lectura de registros OCDS."""

import pytest

from cpcmini.data.codes import clean_code, code_at_level, digits_of, is_valid_code
from cpcmini.data.ocds import items_of_record, record_year


@pytest.mark.parametrize(
    ("raw", "extra", "expected"),
    [
        ("831110911", "83111.09.1", "831110911"),
        ("134929123", "01349.29.1", "0134929123"),  # sección 0: se restaura el cero
        ("11110011", "01111.00.1", "011110011"),
        ("41234567", "41234.56.7", None),  # 8 dígitos genuinos: no alcanza el nivel 9
        ("3814019111", "", "3814019111"),
        ("83111.09.1", None, None),  # sólo 8 dígitos
        ("", "01349.29.1", None),
        (None, None, None),
        ("12345678901234", "", None),  # demasiado largo
    ],
)
def test_clean_code(settings, raw, extra, expected):
    assert clean_code(raw, extra, settings.data.codes) == expected


def test_zero_not_restored_when_prefix_differs(settings):
    assert clean_code("834567891", "01349.29.1", settings.data.codes) == "834567891"


def test_levels_and_validation():
    assert code_at_level("831110911", 5) == "83111"
    with pytest.raises(ValueError, match="menos de 9"):
        code_at_level("8311", 9)
    assert is_valid_code("831110911", {"831110911"})
    assert not is_valid_code("83111091x", {"83111091x"})
    assert digits_of(None) == ""


def test_items_prefer_awards_and_fallback_to_tender(settings):
    record = {
        "ocid": "ocds-x-1",
        "date": "2024-01-02T00:00:00-05:00",
        "tender": {
            "procurementMethodDetails": "Catálogo electrónico - Mejor oferta en el convenio X",
            "mainProcurementCategory": "goods",
            "items": [{"id": "t", "description": "tender", "classification": {"id": "1"}}],
        },
        "awards": [
            {
                "items": [
                    {
                        "id": "a",
                        "description": "award",
                        "classification": {"id": "831110911", "scheme": "CPC", "description": "X"},
                    }
                ]
            }
        ],
    }
    items = items_of_record(record, settings.data.items)
    assert [i.source for i in items] == ["award"]
    assert items[0].method == "Catálogo electrónico"
    assert items[0].year == 2024
    record["awards"] = []
    items = items_of_record(record, settings.data.items)
    assert [i.description for i in items] == ["tender"]


def test_record_without_date_is_skipped(settings):
    assert record_year({"date": None}) is None
    assert items_of_record({"ocid": "x"}, settings.data.items) == []
