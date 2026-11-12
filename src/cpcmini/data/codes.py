"""Reglas sobre los códigos CPC: limpieza, niveles (prefijos) y validación."""

from __future__ import annotations

import re

from cpcmini.config import CodesConfig

_NON_DIGIT = re.compile(r"\D+")


def digits_of(raw: object) -> str:
    return _NON_DIGIT.sub("", str(raw)) if raw is not None else ""


def clean_code(raw: object, additional: object, cfg: CodesConfig) -> str | None:
    """Código sólo con dígitos, o ``None`` si no es un CPC utilizable.

    En OCDS del SERCOP, ``classification.id`` pierde el cero inicial de la sección 0 del CPC
    (p. ej. ``134929123`` frente a ``01349.29.1`` en ``additionalClassifications``). Si el código
    adicional empieza con 0 y el principal no, se restaura el cero (verificado en
    docs/verificacion.md).
    """
    digits = digits_of(raw)
    if not digits:
        return None
    extra = digits_of(additional)
    if (
        cfg.restore_leading_zero
        and extra.startswith("0")
        and not digits.startswith("0")
        and extra[1:5] == digits[:4]
    ):
        digits = "0" + digits
    if not cfg.min_digits <= len(digits) <= cfg.max_digits:
        return None
    return digits


def code_at_level(code: str, level: int) -> str:
    """Prefijo de ``level`` dígitos (5 = subclase CPC, 9 = nivel SERCOP)."""
    if len(code) < level:
        raise ValueError(f"El código {code!r} tiene menos de {level} dígitos")
    return code[:level]


def is_valid_code(code: str, catalog: set[str] | frozenset[str]) -> bool:
    return code.isdigit() and code in catalog
