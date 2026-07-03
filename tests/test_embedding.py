"""FR-2: cosine similarity and the pluggable Embedder interface."""
import numpy as np

from castor import cosine_similarity
from castor.embedding import Embedder


def test_cosine_identical_vectors():
    v = np.array([1.0, 2.0, 3.0])
    assert cosine_similarity(v, v) == 1.0


def test_cosine_orthogonal_vectors():
    assert cosine_similarity(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == 0.0


def test_cosine_zero_vector_returns_zero_not_nan():
    assert cosine_similarity(np.zeros(3), np.array([1.0, 2.0, 3.0])) == 0.0


def test_embedder_is_abstract():
    try:
        Embedder()
        raised = False
    except TypeError:
        raised = True
    assert raised
