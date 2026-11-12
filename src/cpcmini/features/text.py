"""Representación TF-IDF: n-gramas de caracteres (robustos a errores y abreviaturas) + palabras."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.preprocessing import normalize


def build_vectorizer(
    char_ngram_range: tuple[int, int],
    word_ngram_range: tuple[int, int],
    max_features_char: int,
    max_features_word: int,
    min_df: int,
    max_df: float = 1.0,
) -> FeatureUnion:
    char = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=char_ngram_range,
        max_features=max_features_char,
        min_df=min_df,
        max_df=max_df,
        sublinear_tf=True,
        dtype=np.float32,
    )
    word = TfidfVectorizer(
        analyzer="word",
        ngram_range=word_ngram_range,
        token_pattern=r"(?u)\b\w+\b",  # noqa: S106 - patrón de tokens, no una contraseña
        max_features=max_features_word,
        min_df=min_df,
        max_df=max_df,
        sublinear_tf=True,
        dtype=np.float32,
    )
    return FeatureUnion([("char", char), ("word", word)])


def transform(vectorizer: FeatureUnion, texts: Sequence[str]) -> sp.csr_matrix:
    """Transforma y re-normaliza a norma L2 = 1 (necesario para similitud coseno)."""
    matrix = vectorizer.transform(list(texts))
    out: sp.csr_matrix = normalize(sp.csr_matrix(matrix, dtype=np.float32), norm="l2", copy=False)
    return out
