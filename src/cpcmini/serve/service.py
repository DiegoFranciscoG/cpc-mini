"""Servicio de predicción: normaliza → modelo → calibración → abstención → etiquetas del catálogo."""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass

from cpcmini.config import Settings
from cpcmini.data.normalize import TextNormalizer
from cpcmini.db.repository import CatalogRepository
from cpcmini.models.base import CodeClassifier
from cpcmini.models.calibration import calibrate
from cpcmini.models.registry import ModelMeta
from cpcmini.serve.schemas import CandidateOut, PredictionOut

INTENDED_USE = (
    "Sugerir los tres códigos CPC más probables para una descripción de compra pública y "
    "ayudar a revisar ítems posiblemente mal clasificados, siempre con revisión humana."
)
NOT_INTENDED_USE = (
    "Decisiones automáticas sin revisión humana, sanciones, auditorías concluyentes o "
    "cualquier uso que trate la sugerencia como clasificación oficial del SERCOP."
)
MSG_OK = "Sugerencias ordenadas por confianza. Revisa el código antes de usarlo."
MSG_ABSTAIN = (
    "No sé: la confianza está por debajo del umbral calibrado. Se muestran candidatos sólo "
    "como referencia; describe el producto con más detalle (material, medida, uso)."
)
MSG_EMPTY = "No sé: la descripción no tiene información suficiente para sugerir un código."


@dataclass
class Predictor:
    model: CodeClassifier
    meta: ModelMeta
    settings: Settings
    normalizer: TextNormalizer

    @classmethod
    def build(cls, model: CodeClassifier, meta: ModelMeta, settings: Settings) -> Predictor:
        return cls(model, meta, settings, TextNormalizer(settings.data.text))

    def predict(
        self, descriptions: Sequence[str], catalog: CatalogRepository
    ) -> list[PredictionOut]:
        start = time.perf_counter()
        normalized = [self.normalizer.normalize(d) for d in descriptions]
        informative = [self.normalizer.is_informative(n) for n in normalized]
        texts = [n if ok else "" for n, ok in zip(normalized, informative, strict=True)]
        k = self.settings.models.top_k
        raw = self.model.predict_candidates(texts, k)
        cands = calibrate(raw, self.meta.temperature)
        labels = catalog.get_many(code for row in cands.codes for code in row)
        elapsed = (time.perf_counter() - start) * 1000 / max(1, len(descriptions))
        out: list[PredictionOut] = []
        for desc, ok, codes, probs in zip(
            descriptions, informative, cands.codes, cands.probs, strict=True
        ):
            items = (
                [
                    CandidateOut(
                        code9=c,
                        code5=c[:5],
                        label=labels[c].label if c in labels else "",
                        confidence=round(min(1.0, max(0.0, float(p))), 4),
                    )
                    for c, p in zip(codes[:k], probs[:k].tolist(), strict=False)
                ]
                if ok
                else []
            )
            top = items[0].confidence if items else 0.0
            abstained = (not ok) or top < self.meta.threshold
            message = MSG_EMPTY if not ok else (MSG_ABSTAIN if abstained else MSG_OK)
            out.append(
                PredictionOut(
                    description=desc,
                    abstained=abstained,
                    message=message,
                    threshold=round(self.meta.threshold, 4),
                    candidates=items,
                    model=self.meta.name,
                    latency_ms=round(elapsed, 2),
                )
            )
        return out
