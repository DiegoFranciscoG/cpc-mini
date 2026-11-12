"""T-11: normalización de texto (tildes, unidades, abreviaturas, entidades HTML)."""

import pytest

from cpcmini.data.normalize import TextNormalizer, clean_display, strip_accents


@pytest.fixture
def norm(settings):
    return TextNormalizer(settings.data.text)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("PARACETAMOL 500MG TAB", "paracetamol 500 mg tableta"),
        ("Tabletas de acetaminofén de 500 mg", "tableta de paracetamol de 500 mg"),
        ("Jeringa 5ML", "jeringa 5 ml"),
        ("Alcohol antiséptico 1 LT", "alcohol antiseptico 1 l"),
        ("Cloro 3,5 lts", "cloro 3.5 l"),
        ("Papel bond 75GR", "papel bond 75 g"),
        ('Tubo PVC 2" ', "tubo pvc 2 pulgada"),
        ("Caja de revisi&oacute;n H.S. 0.60x0.60m", "caja de revision h s 0.60x0.60m"),
        ("ADQUISICIÓN DE RESMAS DE PAPEL", "resmas de papel"),
        ("   *RESMA  DE   PAPEL   ", "resma de papel"),
    ],
)
def test_normalize_cases(norm, raw, expected):
    assert norm.normalize(raw) == expected


def test_normalize_is_idempotent(norm):
    once = norm.normalize("Ibuprofeno 400MG CAPS x 100 unid")
    assert norm.normalize(once) == once


def test_empty_and_none(norm):
    assert norm.normalize("") == ""
    assert norm.normalize(None) == ""


def test_max_chars(norm, settings):
    assert len(norm.normalize("a " * 1000)) <= settings.data.text.max_chars


@pytest.mark.parametrize(
    "text",
    [
        "VER ESPECIFICACIONES TECNICAS EN LOS PLIEGOS",
        "de acuerdo a lo solicitado en los pliegos",
        "REVISAR TERMINOS DE REFERENCIA",
        "servicios",
        "123",
        "",
    ],
)
def test_generic_descriptions_are_not_informative(norm, text):
    assert not norm.is_informative(norm.normalize(text))


def test_specific_description_is_informative(norm):
    assert norm.is_informative(norm.normalize("Filtro de combustible para motor diesel"))


def test_signature_ignores_order_and_repeats(norm):
    a = norm.signature(norm.normalize("paracetamol 500 mg tableta"))
    b = norm.signature(norm.normalize("TABLETA paracetamol 500MG tab"))
    assert a == b


def test_helpers():
    assert strip_accents("Ñandú acción") == "Nandu accion"
    assert clean_display("Tuber&iacute;a  &amp;amp; codo") == "Tubería & codo"
    assert clean_display(None) == ""
