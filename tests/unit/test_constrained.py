"""T-05: la salida del generativo siempre es un código válido del catálogo o "no sé"."""

import numpy as np
import pytest

from cpcmini.models.constrained import CodeTrie, constrained_beam, log_softmax

VOCAB = 40
EOS = 39


def encode(value: str) -> list[int]:
    """Tokenizador de juguete: un token por dígito (0-9) y por letra (10-35)."""
    out = []
    for ch in value:
        if ch.isdigit():
            out.append(int(ch))
        elif ch == " ":
            out.append(36)
        else:
            out.append(10 + (ord(ch) % 26))
    return out


CATALOG = ["352600111", "352600112", "321290418", "853300012", "013492912"]
ABSTAIN = "no se"


@pytest.fixture
def trie():
    return CodeTrie.build([*CATALOG, ABSTAIN], encode, EOS)


def test_trie_allows_only_catalog_paths(trie):
    assert trie.allowed_next([]) == sorted({encode(v)[0] for v in [*CATALOG, ABSTAIN]})
    assert trie.allowed_next(encode("3526001")) == [1]
    assert trie.allowed_next(encode("352600111")) == [EOS]
    assert trie.allowed_next(encode("99")) == []
    assert trie.value_of([*encode("321290418"), EOS]) == "321290418"
    assert trie.value_of(encode("321")) is None


@pytest.mark.parametrize("seed", range(25))
def test_t05_random_model_always_valid(trie, seed):
    rng = np.random.default_rng(seed)

    def score(prefix):  # "modelo" adversarial: logits aleatorios, favorece tokens inválidos
        logits = rng.normal(size=VOCAB) * 5
        logits[20:35] += 50
        return logits

    out = constrained_beam(score, trie, beams=3, max_steps=12)
    assert out, "debe devolver al menos una secuencia completa"
    for value, logp in out:
        assert value in trie.values
        assert logp <= 0.0
    assert [lp for _, lp in out] == sorted((lp for _, lp in out), reverse=True)


def test_beam_finds_most_likely_code(trie):
    target = [*encode("853300012"), EOS]

    def score(prefix):
        logits = np.zeros(VOCAB)
        logits[target[len(prefix)]] = 10.0
        return logits

    out = constrained_beam(score, trie, beams=2, max_steps=12)
    assert out[0][0] == "853300012"


def test_log_softmax_normalizes():
    lp = log_softmax(np.array([1.0, 2.0, 3.0]))
    assert np.exp(lp).sum() == pytest.approx(1.0)
