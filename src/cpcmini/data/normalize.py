"""Normalización de descripciones: minúsculas, tildes, unidades y abreviaturas (prueba T-11)."""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field
from functools import cached_property

from cpcmini.config import TextConfig

_SPACES = re.compile(r"\s+")
_DECIMAL_COMMA = re.compile(r"(?<=\d),(?=\d)")
_NON_ALNUM = re.compile(r"[^a-z0-9.\s]")
_STRAY_DOTS = re.compile(r"(?<!\d)\.|\.(?!\d)")
_ALPHA = re.compile(r"[a-z]")


def clean_display(text: str | None) -> str:
    """Texto legible: decodifica entidades HTML (``&Oacute;`` → ``Ó``) y colapsa espacios."""
    if not text:
        return ""
    return _SPACES.sub(" ", html.unescape(html.unescape(text))).strip()


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


@dataclass(frozen=True)
class TextNormalizer:
    """Normalizador determinista configurado desde ``configs/data.yaml``."""

    cfg: TextConfig
    _generic: tuple[re.Pattern[str], ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        compiled = tuple(re.compile(p) for p in self.cfg.generic_patterns)
        object.__setattr__(self, "_generic", compiled)

    @cached_property
    def _unit_map(self) -> dict[str, str]:
        return {alias: canon for canon, aliases in self.cfg.units.items() for alias in aliases}

    @cached_property
    def _unit_glued(self) -> re.Pattern[str]:
        aliases = sorted(self._unit_map, key=len, reverse=True)
        return re.compile(r"(\d)(" + "|".join(map(re.escape, aliases)) + r")\b")

    def normalize(self, text: str | None) -> str:
        if not text:
            return ""
        out = strip_accents(clean_display(text)).lower()
        out = out.replace('"', " pulgada ").replace("''", " pulgada ")
        out = _DECIMAL_COMMA.sub(".", out)
        out = _NON_ALNUM.sub(" ", out)
        out = _STRAY_DOTS.sub(" ", out)
        out = self._unit_glued.sub(r"\1 \2", out)
        tokens = [self._canon(tok) for tok in out.split()]
        out = " ".join(tok for tok in tokens if tok)
        out = self._strip_prefix(out)
        return _SPACES.sub(" ", out).strip()[: self.cfg.max_chars]

    def _canon(self, token: str) -> str:
        if token in self.cfg.abbreviations:
            return self.cfg.abbreviations[token]
        return self._unit_map.get(token, token)

    def _strip_prefix(self, text: str) -> str:
        for prefix in self.cfg.strip_prefixes:
            if text.startswith(prefix + " ") and len(text) > len(prefix) + 3:
                return text[len(prefix) + 1 :]
        return text

    def signature(self, normalized: str) -> str:
        """Firma casi-idéntica: tokens únicos ordenados (detecta reordenamientos)."""
        return " ".join(sorted(set(normalized.split())))

    def is_informative(self, normalized: str) -> bool:
        """Falso si la descripción es vacía, muy corta o genérica (remite a pliegos, etc.)."""
        if len(normalized) < self.cfg.min_chars:
            return False
        alpha_tokens = [t for t in normalized.split() if _ALPHA.search(t)]
        if len(alpha_tokens) < self.cfg.min_alpha_tokens:
            return False
        return not any(p.search(normalized) for p in self._generic)
