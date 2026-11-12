"""T-04 (unidad): detección de cédula, RUC de persona natural, teléfonos y correos."""

import pytest

from cpcmini.data.pii import PiiDetector, is_valid_cedula


def make_cedula(prefix9: str) -> str:
    """Completa el dígito verificador módulo 10 a un prefijo sintético (números ficticios)."""
    total = 0
    for i, ch in enumerate(prefix9):
        value = int(ch) * (2 if i % 2 == 0 else 1)
        total += value - 9 if value > 9 else value
    return prefix9 + str((10 - total % 10) % 10)


SYNTHETIC = make_cedula("240000001")


def test_cedula_checksum():
    assert is_valid_cedula(SYNTHETIC)
    wrong = SYNTHETIC[:9] + str((int(SYNTHETIC[9]) + 1) % 10)
    assert not is_valid_cedula(wrong)
    assert not is_valid_cedula(make_cedula("990000001"))  # provincia inexistente
    assert not is_valid_cedula(make_cedula("249000001"))  # tercer dígito >= 6 (no persona natural)
    assert is_valid_cedula(make_cedula("300000001"))  # código 30 (ecuatorianos en el exterior)
    assert not is_valid_cedula("12345")


@pytest.fixture
def detector(settings):
    return PiiDetector(settings.data.pii)


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        (f"Proveedor con cédula {SYNTHETIC}", "cedula"),
        (f"RUC {SYNTHETIC}001 servicios", "ruc"),
        ("llamar al 0991234567", "phone"),
        ("Tel: 02 2440 050 oficina", "phone"),
        ("+593 99 123 4567", "phone"),
        ("escribir a compras@ejemplo.ec", "email"),
    ],
)
def test_detects(detector, text, kind):
    assert kind in detector.findings(text)


@pytest.mark.parametrize(
    "text",
    [
        "PARACETAMOL 500 MG CAJA X 100",
        "Tubo PVC 110 mm x 6 m",
        "Transformador 50 kVA 13800 GRdY",
        "Código de producto 1234567890 lote 5",  # 10 dígitos que no pasan el verificador
        "",
    ],
)
def test_no_false_positive(detector, text):
    assert detector.findings(text) == []
    assert not detector.has_pii(text)
