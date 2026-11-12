"""Decodificación restringida para el escalón generativo (prueba T-05).

La salida del modelo generativo sólo puede ser una secuencia de tokens que forme un código válido
del catálogo de entrenamiento, o la respuesta de abstención ("no sé"). Se implementa con un trie de
secuencias de tokens; el adaptador de Hugging Face usa ``allowed_next`` como
``prefix_allowed_tokens_fn`` de ``generate``.
"""

from __future__ import annotations

import heapq
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

ScoreFn = Callable[[Sequence[int]], npt.NDArray[np.float64]]


@dataclass
class _Node:
    children: dict[int, _Node] = field(default_factory=dict)
    value: str | None = None


class CodeTrie:
    """Trie de secuencias de tokens → texto de salida (código o abstención)."""

    def __init__(self, eos_id: int) -> None:
        self.root = _Node()
        self.eos_id = eos_id
        self.values: set[str] = set()

    def add(self, token_ids: Sequence[int], value: str) -> None:
        node = self.root
        for tok in [*token_ids, self.eos_id]:
            node = node.children.setdefault(tok, _Node())
        node.value = value
        self.values.add(value)

    @classmethod
    def build(
        cls, values: Iterable[str], encode: Callable[[str], list[int]], eos_id: int
    ) -> CodeTrie:
        trie = cls(eos_id)
        for value in values:
            trie.add(encode(value), value)
        return trie

    def _walk(self, prefix: Sequence[int]) -> _Node | None:
        node: _Node | None = self.root
        for tok in prefix:
            if node is None:
                return None
            node = node.children.get(tok)
        return node

    def allowed_next(self, prefix: Sequence[int]) -> list[int]:
        node = self._walk(prefix)
        return sorted(node.children) if node else []

    def value_of(self, sequence: Sequence[int]) -> str | None:
        node = self._walk(sequence)
        return node.value if node else None


def log_softmax(logits: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    shifted = logits - logits.max()
    out: npt.NDArray[np.float64] = shifted - np.log(np.exp(shifted).sum())
    return out


def constrained_beam(
    score: ScoreFn, trie: CodeTrie, beams: int, max_steps: int
) -> list[tuple[str, float]]:
    """Búsqueda en haz restringida al trie. Devuelve (valor, log-prob) de secuencias completas.

    ``score(prefix)`` devuelve los logits del siguiente token dado el prefijo generado.
    Cualquier token fuera del trie recibe probabilidad cero, así que toda salida es válida.
    """
    frontier: list[tuple[float, tuple[int, ...]]] = [(0.0, ())]
    finished: list[tuple[float, str]] = []
    for _ in range(max_steps):
        candidates: list[tuple[float, tuple[int, ...]]] = []
        for logp, seq in frontier:
            allowed = trie.allowed_next(seq)
            if not allowed:
                continue
            logits = np.asarray(score(seq), dtype=np.float64)
            masked = np.full_like(logits, -np.inf)
            masked[allowed] = logits[allowed]
            lp = log_softmax(masked)
            for tok in allowed:
                new_seq = (*seq, tok)
                value = trie.value_of(new_seq) if tok == trie.eos_id else None
                if value is not None:
                    finished.append((logp + float(lp[tok]), value))
                else:
                    candidates.append((logp + float(lp[tok]), new_seq))
        frontier = heapq.nlargest(beams, candidates, key=lambda c: c[0])
        if not frontier:
            break
    best = heapq.nlargest(beams, finished, key=lambda c: c[0])
    return [(value, logp) for logp, value in best]
