"""Etiquetas jerárquicas para el codificador (escalón 2): 5 dígitos y luego 9 dentro de la rama."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from cpcmini.models.base import CandidateSet


@dataclass(frozen=True)
class HierarchyLabels:
    codes9: tuple[str, ...]
    codes5: tuple[str, ...]

    @classmethod
    def from_codes(cls, codes: Sequence[str]) -> HierarchyLabels:
        c9 = tuple(sorted(set(codes)))
        return cls(codes9=c9, codes5=tuple(sorted({c[:5] for c in c9})))

    def index9(self) -> dict[str, int]:
        return {c: i for i, c in enumerate(self.codes9)}

    def index5(self) -> dict[str, int]:
        return {c: i for i, c in enumerate(self.codes5)}

    def parent_index(self) -> npt.NDArray[np.int64]:
        idx5 = self.index5()
        return np.array([idx5[c[:5]] for c in self.codes9], dtype=np.int64)

    def combine(
        self, p5: npt.NDArray[np.float64], p9: npt.NDArray[np.float64]
    ) -> npt.NDArray[np.float64]:
        """P(código) = P(rama) · P(código | rama), con P(código | rama) renormalizada en la rama."""
        parent = self.parent_index()
        branch_mass = np.zeros_like(p5)
        for row in range(p9.shape[0]):
            np.add.at(branch_mass[row], parent, p9[row])
        within = p9 / np.maximum(branch_mass[:, parent], 1e-12)
        out: npt.NDArray[np.float64] = p5[:, parent] * within
        return out

    def to_candidates(self, probs: npt.NDArray[np.float64], k: int) -> CandidateSet:
        labels = np.asarray(self.codes9)
        codes: list[list[str]] = []
        values: list[npt.NDArray[np.float64]] = []
        for row in probs:
            top = np.argsort(-row, kind="stable")[:k]
            codes.append([str(c) for c in labels[top]])
            values.append(row[top].astype(np.float64))
        return CandidateSet(codes, values)
