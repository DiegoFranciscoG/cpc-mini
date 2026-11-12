"""Informe comparativo de la escalera de modelos (reports/resultados.md)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PENDING_GPU = {
    "mmbert_small": "2. Codificador: mmBERT-small jerárquico (Kaggle, GPU)",
    "qwen3_lora": "3. Generativo: Qwen3-0.6B-Base + LoRA, salida restringida (Kaggle, GPU)",
}


def load_metrics(reports_dir: str | Path) -> dict[str, dict[str, Any]]:
    folder = Path(reports_dir) / "metrics"
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(folder.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        out[data["model"]] = data
    return out


def select_winner(metrics: dict[str, dict[str, Any]]) -> str:
    """El ganador se elige en VALIDACIÓN (top-1 a 9 dígitos; desempate top-3); prueba sólo reporta."""

    def key(name: str) -> tuple[float, float]:
        val = metrics[name]["validation"]["level_9"]
        return (val["top1"]["value"], val["top3"]["value"])

    return max(metrics, key=key)


def _ci(m: dict[str, float]) -> str:
    return f"{100 * m['value']:.1f} ({100 * m['low']:.1f}–{100 * m['high']:.1f})"


def _pct(x: float) -> str:
    return f"{100 * x:.1f}"


def render(metrics: dict[str, dict[str, Any]], manifest: dict[str, Any]) -> str:
    lines: list[str] = ["# Resultados de la escalera de modelos", ""]
    lines += [
        f"Dataset `{manifest['dataset_hash'][:12]}` · prueba = años 2025–2026 (descripciones nunca vistas "
        "en entrenamiento ni validación) · intervalos al 95 % por bootstrap.",
        "",
        "## Comparación en prueba",
        "",
        "| Escalón | Top-1 9 díg. | Top-3 9 díg. | Top-1 5 díg. | Top-3 5 díg. | F1 macro 9 | ECE 9 | "
        "Cobertura @90 % | Latencia p50 | Tamaño |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for m in metrics.values():
        t9, t5 = m["test"]["level_9"], m["test"]["level_5"]
        lines.append(
            f"| {m['family']} | {_ci(t9['top1'])} | {_ci(t9['top3'])} | {_ci(t5['top1'])} | "
            f"{_ci(t5['top3'])} | {_ci(t9['macro_f1'])} | {t9['ece']:.3f} | {_pct(t9['coverage_at_target'])} % | "
            f"{m['latency_cpu']['p50_ms']:.1f} ms | {m['size_mb']:.0f} MB |"
        )
    for family in PENDING_GPU.values():
        lines.append(
            f"| {family} | pendiente | pendiente | pendiente | pendiente | pendiente | — | — | — | — |"
        )
    if metrics:
        winner = select_winner(metrics)
        lines += [
            "",
            f"**Ganador (elegido en validación):** `{winner}` — {metrics[winner]['family']}.",
            "",
        ]
    lines += [
        "Los escalones 2 y 3 necesitan GPU: el código, las pruebas de humo y los cuadernos de Kaggle están "
        "en el repositorio, pero sus métricas sólo se publican cuando se ejecutan (nada se inventa).",
        "",
        "## Abstención (umbral calibrado en validación para 90 % de exactitud)",
        "",
        "| Modelo | Umbral | Cobertura en prueba | Exactitud de lo respondido |",
        "|---|---|---|---|",
    ]
    for name, m in metrics.items():
        a = m["test"]["abstention"]
        lines.append(
            f"| `{name}` | {a['threshold']:.3f} | {_pct(a['coverage'])} % | {_pct(a['answered_top1'])} % |"
        )
    lines += [
        "",
        "## Rendimiento por frecuencia del código en entrenamiento (top-1, 9 dígitos)",
        "",
    ]
    groups = sorted({g for m in metrics.values() for g in m["test"]["by_train_frequency"]})
    lines += ["| Modelo | " + " | ".join(groups) + " |", "|---" * (len(groups) + 1) + "|"]
    for name, m in metrics.items():
        freq = m["test"]["by_train_frequency"]
        cells = [
            f"{_pct(freq[g]['top1'])} % (n={int(freq[g]['n'])})" if g in freq else "—"
            for g in groups
        ]
        lines.append(f"| `{name}` | " + " | ".join(cells) + " |")
    lines += ["", "## Subconjuntos de prueba (top-1 / top-3, 9 dígitos)", ""]
    subsets = sorted({s for m in metrics.values() for s in m["test"]["subsets"]})
    lines += ["| Modelo | " + " | ".join(subsets) + " |", "|---" * (len(subsets) + 1) + "|"]
    for name, m in metrics.items():
        subs = m["test"]["subsets"]
        cells = [
            f"{_pct(subs[s]['level_9']['top1'])} / {_pct(subs[s]['level_9']['top3'])} "
            f"(n={subs[s]['level_9']['n']})"
            if s in subs
            else "—"
            for s in subsets
        ]
        lines.append(f"| `{name}` | " + " | ".join(cells) + " |")
    quant = {n: m["quantization"] for n, m in metrics.items() if "quantization" in m}
    if quant:
        lines += [
            "",
            "## Cuantización int8 (T-07)",
            "",
            "| Modelo | Top-1 float32 | Top-1 int8 | Pérdida | Pesos float32 | Pesos int8 | Latencia int8 p50 |",
            "|---|---|---|---|---|---|---|",
        ]
        for name, q in quant.items():
            lines.append(
                f"| `{name}` | {_pct(q['float32_top1_9'])} % | {_pct(q['int8_top1_9'])} % | "
                f"{100 * q['drop']:.2f} pts | {q['float32_weights_mb']:.0f} MB | "
                f"{q['int8_weights_mb']:.0f} MB | {q['int8_latency_cpu']['p50_ms']:.1f} ms |"
            )
    return "\n".join(lines) + "\n"


def write_results(reports_dir: str | Path, manifest: dict[str, Any], extra: str = "") -> Path:
    metrics = load_metrics(reports_dir)
    out = Path(reports_dir) / "resultados.md"
    out.write_text(render(metrics, manifest) + extra, encoding="utf-8")
    return out
