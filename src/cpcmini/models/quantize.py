"""Cuantización int8 por fila de los pesos lineales (prueba T-07: pierde < 2 puntos)."""

from __future__ import annotations

import copy

import numpy as np
import numpy.typing as npt

from cpcmini.models.hierarchical import HierarchicalLinear, LocalModel

INT8_MAX = 127


def quantize_rows(
    weight: npt.NDArray[np.float32],
) -> tuple[npt.NDArray[np.int8], npt.NDArray[np.float32]]:
    """Simétrica por fila: ``w ≈ q * scale`` con ``q`` en [-127, 127]."""
    max_abs = np.abs(weight).max(axis=1)
    scale = np.where(max_abs > 0, max_abs / INT8_MAX, 1.0).astype(np.float32)
    q = np.clip(np.rint(weight / scale[:, None]), -INT8_MAX, INT8_MAX).astype(np.int8)
    return q, scale


def quantize_model(model: HierarchicalLinear) -> HierarchicalLinear:
    """Copia del modelo con todos los nodos en int8 (los vectorizadores se comparten)."""
    out = copy.copy(model)
    out.nodes = {}
    for key, node in model.nodes.items():
        if node.weight is None or node.scale is not None:
            out.nodes[key] = node
            continue
        q, scale = quantize_rows(node.weight.astype(np.float32))
        out.nodes[key] = LocalModel(
            classes=node.classes,
            cols=node.cols,
            weight=q,
            bias=node.bias,
            scale=scale,
            margin_scale=node.margin_scale,
        )
    out.name = f"{model.name}_int8"
    return out
