"""T-09: atribución y licencia presentes en las fichas y en la configuración publicada."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "SERCOP",
    "Open Contracting Partnership",
    "CC BY 3.0",
    "creativecommons.org/licenses/by/3.0/ec",
)


@pytest.mark.parametrize(
    "path",
    ["docs/dataset-card.md", "docs/model-card.md", "sample_data/README.md", "README.md"],
)
def test_cards_carry_attribution_and_license(path):
    text = " ".join((ROOT / path).read_text(encoding="utf-8").split())  # ignora saltos de línea
    for needle in REQUIRED:
        assert needle in text, f"{path} no menciona {needle!r}"


def test_attribution_reaches_manifest_and_api(settings):
    assert "SERCOP" in settings.data.source.attribution
    assert "Open Contracting Partnership" in settings.data.source.attribution
    assert settings.data.source.license == "CC BY 3.0 EC"
    assert settings.data.source.license_url.endswith("/by/3.0/ec/")
