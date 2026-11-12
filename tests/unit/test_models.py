"""Escalones 1 y 4 sobre datos diminutos; cuantización (T-07 unidad); etiquetas jerárquicas."""

import numpy as np
import pytest

from cpcmini.models.base import CodeClassifier, topk_from_scores
from cpcmini.models.hierarchical import HierarchicalLinear
from cpcmini.models.labels import HierarchyLabels
from cpcmini.models.quantize import quantize_model, quantize_rows
from cpcmini.models.retrieval import KnnRetrieval, vote

TEXTS = [
    "paracetamol 500 mg tableta",
    "paracetamol 1 g tableta",
    "paracetamol jarabe 120 ml",
    "ibuprofeno 400 mg tableta",
    "ibuprofeno 600 mg capsula",
    "ibuprofeno suspension 100 ml",
    "resma papel bond a4 75 g",
    "resma papel bond a4 80 g",
    "papel bond inen 75 g",
    "limpieza de oficinas",
    "limpieza de edificio administrativo",
    "limpieza de viviendas sector norte",
]
CODES = [
    "352600111",
    "352600111",
    "352600111",
    "352600112",
    "352600112",
    "352600112",
    "321290418",
    "321290418",
    "321290419",
    "853300012",
    "853300012",
    "853300011",
]


@pytest.fixture
def small_linear_cfg(settings):
    return settings.models.linear.model_copy(
        update={"max_features_char": 2000, "max_features_word": 500, "min_df": 1, "max_iter": 50}
    )


@pytest.mark.parametrize("loss", ["log_loss", "hinge"])
def test_hierarchical_learns_and_ranks(small_linear_cfg, loss):
    model = HierarchicalLinear(small_linear_cfg.model_copy(update={"loss": loss}), seed=1)
    model.fit(TEXTS, CODES)
    assert isinstance(model, CodeClassifier)
    cands = model.predict_candidates(["paracetamol 750 mg tableta", "resma papel bond a4"], 3)
    assert cands.codes[0][0] == "352600111"
    assert cands.codes[1][0].startswith("32129")
    for probs in cands.probs:
        assert np.all(np.diff(probs) <= 1e-12) and probs.sum() <= 1.0 + 1e-9
    assert model.nbytes() > 0


def test_hierarchical_is_deterministic(small_linear_cfg):
    a = HierarchicalLinear(small_linear_cfg, seed=3).fit(TEXTS, CODES)
    b = HierarchicalLinear(small_linear_cfg, seed=3).fit(TEXTS, CODES)
    qa = a.predict_candidates(TEXTS, 3)
    qb = b.predict_candidates(TEXTS, 3)
    assert qa.codes == qb.codes
    for x, y in zip(qa.probs, qb.probs, strict=True):
        np.testing.assert_allclose(x, y)


def test_single_child_nodes_and_unfitted(small_linear_cfg):
    model = HierarchicalLinear(small_linear_cfg).fit(["a b c", "a b d"], ["111110001", "111110001"])
    cands = model.predict_candidates(["a b"], 3)
    assert cands.codes == [["111110001"]] and cands.probs[0][0] == pytest.approx(1.0)
    with pytest.raises(RuntimeError):
        HierarchicalLinear(small_linear_cfg).predict_candidates(["x"], 3)


def test_quantization_preserves_predictions(small_linear_cfg):
    model = HierarchicalLinear(small_linear_cfg, seed=1).fit(TEXTS, CODES)
    q = quantize_model(model)
    assert q.name.endswith("_int8")
    assert q.nbytes() < model.nbytes()
    assert q.predict_candidates(TEXTS, 1).codes == model.predict_candidates(TEXTS, 1).codes
    assert quantize_model(q).nodes.keys() == q.nodes.keys()  # re-cuantizar no rompe nada


def test_quantize_rows_error_bound():
    rng = np.random.default_rng(0)
    w = rng.normal(size=(5, 50)).astype(np.float32)
    w[2] = 0.0
    q, scale = quantize_rows(w)
    assert q.dtype == np.int8
    err = np.abs(q.astype(np.float32) * scale[:, None] - w)
    assert np.all(err <= scale[:, None] / 2 + 1e-6)


def test_vote_weights_by_similarity():
    codes, probs = vote(["a", "b", "a"], np.array([0.9, 0.95, 0.5]), power=1.0, k=5)
    assert codes == ["a", "b"] and probs.sum() == pytest.approx(1.0)
    codes, _ = vote(["a", "b", "a"], np.array([0.9, 0.95, 0.5]), power=8.0, k=5)
    assert codes[0] == "b"
    assert vote([], np.array([]), 1.0, 3)[0] == []


def test_knn_retrieval(settings):
    cfg = settings.models.retrieval.model_copy(update={"min_df": 1, "max_df": 1.0, "k": 3})
    model = KnnRetrieval(cfg).fit(TEXTS, CODES)
    cands = model.predict_candidates(["ibuprofeno 400 mg capsula", "zzzz qqqq"], 3)
    assert cands.codes[0][0] == "352600112"
    assert cands.codes[1] == []  # sin vecinos: no inventa
    assert model.nbytes() > 0
    with pytest.raises(RuntimeError):
        KnnRetrieval(cfg).neighbors(["x"])


def test_hierarchy_labels_combine():
    labels = HierarchyLabels.from_codes(["111110001", "111110002", "222220001"])
    p5 = np.array([[0.8, 0.2]])
    p9 = np.array([[0.1, 0.3, 0.6]])
    out = labels.combine(p5, p9)
    assert out.sum() == pytest.approx(1.0)
    assert out[0, 1] == pytest.approx(0.8 * 0.75)
    cands = labels.to_candidates(out, 2)
    assert cands.codes[0] == ["111110002", "111110001"]  # empate 0.2-0.2: orden del catálogo


def test_topk_from_scores():
    codes, probs = topk_from_scores(np.array(["a", "b", "c"]), np.array([[0.2, 0.5, 0.3]]), 2)
    assert codes == [["b", "c"]] and probs[0].tolist() == [0.5, 0.3]
