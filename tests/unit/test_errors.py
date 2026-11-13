"""Análisis de errores por categoría y confusiones entre ramas."""

import numpy as np
import polars as pl

from cpcmini.eval.errors import branch_labels, error_analysis, render_errors
from cpcmini.models.base import CandidateSet


def test_error_analysis_and_render():
    frame = pl.DataFrame(
        {
            "code9": ["111110001", "111110002", "222220001", "222220001"],
            "category": ["goods", "goods", "works", ""],
            "description": ["a", "b|c", "d", "e"],
        }
    )
    cands = CandidateSet(
        [["111110001"], ["111110001"], ["111110001"], []],
        [np.array([0.9]), np.array([0.8]), np.array([0.6]), np.array([])],
    )
    out = error_analysis(cands, frame)
    assert out["n"] == 4
    assert out["by_category"]["Bienes"] == {"n": 2.0, "top1_9": 0.5, "top1_5": 1.0}
    assert out["by_category"]["Obras"]["top1_5"] == 0.0
    assert out["by_category"]["Sin categoría"]["n"] == 1.0
    pairs = {(c["true"], c["pred"]): c["n"] for c in out["confusions_5"]}
    assert pairs == {("22222", "11111"): 1, ("22222", "(sin candidato)"): 1}
    catalog = pl.DataFrame(
        {
            "code5": ["11111", "11111"],
            "code9": ["111110001", "111110002"],
            "label": ["PAPEL BOND", "OTRO"],
            "n_items": [5, 9],
        }
    )
    labels = branch_labels(catalog)
    assert labels["11111"].startswith("(otro")
    text = render_errors(out, labels)
    assert "## Análisis de errores" in text and "| Bienes | 2 |" in text
