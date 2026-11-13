"""Análisis de errores: por categoría de compra y confusiones más frecuentes entre ramas."""

from __future__ import annotations

from collections import Counter
from typing import Any

import polars as pl

from cpcmini.eval.metrics import hits_at_k, level_view
from cpcmini.models.base import CandidateSet

CATEGORY_NAMES = {"goods": "Bienes", "services": "Servicios", "works": "Obras", "": "Sin categoría"}


def error_analysis(cands: CandidateSet, frame: pl.DataFrame, top: int = 10) -> dict[str, Any]:
    truth = frame["code9"].to_list()
    ranked9, _ = level_view(cands, 9)
    ranked5, _ = level_view(cands, 5)
    hit9 = hits_at_k(ranked9, truth, 9, 1)
    hit5 = hits_at_k(ranked5, truth, 5, 1)
    categories = [c or "" for c in frame["category"].to_list()]
    by_category: dict[str, dict[str, float]] = {}
    for cat in sorted(set(categories)):
        idx = [i for i, c in enumerate(categories) if c == cat]
        by_category[CATEGORY_NAMES.get(cat, cat)] = {
            "n": float(len(idx)),
            "top1_9": round(float(hit9[idx].mean()), 4),
            "top1_5": round(float(hit5[idx].mean()), 4),
        }
    confusions: Counter[tuple[str, str]] = Counter()
    example: dict[tuple[str, str], str] = {}
    descriptions = frame["description"].to_list()
    for i, (r, t) in enumerate(zip(ranked5, truth, strict=True)):
        pred = r[0] if r else "(sin candidato)"
        if pred != t[:5]:
            key = (t[:5], pred)
            confusions[key] += 1
            example.setdefault(key, descriptions[i])
    return {
        "n": len(truth),
        "by_category": by_category,
        "confusions_5": [
            {"true": t, "pred": p, "n": n, "example": example[(t, p)]}
            for (t, p), n in confusions.most_common(top)
        ],
    }


def render_errors(analysis: dict[str, Any], labels: dict[str, str]) -> str:
    lines = [
        "",
        "## Análisis de errores",
        "",
        f"Muestra aleatoria fija de {analysis['n']} descripciones de prueba, modelo en servicio.",
        "",
        "| Categoría | Descripciones | Top-1 9 díg. | Top-1 5 díg. |",
        "|---|---|---|---|",
    ]
    for cat, m in analysis["by_category"].items():
        lines.append(
            f"| {cat} | {int(m['n'])} | {100 * m['top1_9']:.1f} % | {100 * m['top1_5']:.1f} % |"
        )
    lines += [
        "",
        "Confusiones más frecuentes entre subclases de 5 dígitos (verdadera → predicha):",
        "",
        "| Verdadera | Predicha | Casos | Ejemplo |",
        "|---|---|---|---|",
    ]
    for c in analysis["confusions_5"]:
        t, p = c["true"], c["pred"]
        t_label = labels.get(t, "")
        p_label = labels.get(p, "")
        example = c["example"].replace("|", "/")[:70]
        lines.append(f"| {t} {t_label} | {p} {p_label} | {c['n']} | {example} |")
    return "\n".join(lines) + "\n"


def branch_labels(catalog: pl.DataFrame) -> dict[str, str]:
    """Etiqueta aproximada de cada rama: la del código de 9 dígitos con más ítems (no es oficial)."""
    top = catalog.sort(["code5", "n_items"], descending=[False, True]).group_by("code5").first()
    return {r["code5"]: f"({r['label'][:40].lower()}…)" for r in top.iter_rows(named=True)}
