"""Detección conservadora de datos personales en descripciones (prueba T-04).

Si un ítem contiene una cédula válida, un RUC de persona natural, un teléfono o un correo,
se excluye del dataset publicado (minimización, LOPDP).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from cpcmini.config import PiiConfig

_DIGIT_RUNS = re.compile(r"(?<!\d)\d{10}(?:001)?(?!\d)")


def is_valid_cedula(number: str, provinces_max: int = 24, extra: tuple[int, ...] = (30,)) -> bool:
    """Cédula ecuatoriana: provincia, tercer dígito < 6 y verificador módulo 10."""
    if len(number) != 10 or not number.isdigit():
        return False
    province = int(number[:2])
    if not (1 <= province <= provinces_max or province in extra):
        return False
    if int(number[2]) >= 6:
        return False
    total = 0
    for i, ch in enumerate(number[:9]):
        value = int(ch) * (2 if i % 2 == 0 else 1)
        total += value - 9 if value > 9 else value
    check = (10 - total % 10) % 10
    return check == int(number[9])


@dataclass(frozen=True)
class PiiDetector:
    cfg: PiiConfig
    _email: re.Pattern[str] = field(init=False, repr=False)
    _phones: tuple[re.Pattern[str], ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_email", re.compile(self.cfg.email_regex))
        object.__setattr__(self, "_phones", tuple(re.compile(p) for p in self.cfg.phone_regexes))

    def findings(self, text: str | None) -> list[str]:
        """Tipos de dato personal encontrados (vacío si no hay)."""
        if not text:
            return []
        found: list[str] = []
        if self._email.search(text):
            found.append("email")
        if any(p.search(text) for p in self._phones):
            found.append("phone")
        extra = tuple(self.cfg.cedula_extra_provinces)
        for match in _DIGIT_RUNS.finditer(text):
            if is_valid_cedula(match.group()[:10], self.cfg.cedula_provinces_max, extra):
                found.append("ruc" if len(match.group()) == 13 else "cedula")
                break
        return found

    def has_pii(self, text: str | None) -> bool:
        return bool(self.findings(text))
