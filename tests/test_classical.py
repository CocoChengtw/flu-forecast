"""Run from the repo root: python -m pytest tests/test_classical.py (~30 s)."""

import numpy as np
import pytest

from src import classical, config
from src.evaluate import prepare_series


@pytest.fixture(scope="module")
def train():
    s = prepare_series()
    return s.loc[:config.TEST_START].copy()


@pytest.mark.parametrize("name", ["ets", "arima", "prophet"])
def test_same_paths_on_rerun(train, name):
    """Seeded simulation: rerunning a model on the same data gives identical paths,
    even if something else has used the global numpy RNG in between."""
    if name == "prophet":
        pytest.importorskip("prophet")
    fn = classical.make_arima((2, 0, 0), 4) if name == "arima" else getattr(classical, name)
    first = fn(train, 4, 50)
    np.random.seed(None)
    np.random.rand(100)
    second = fn(train, 4, 50)
    assert first.shape == (50, 4)
    np.testing.assert_array_equal(first, second)


def test_ets_fit_converges(train):
    assert classical.fit_ets(train).mle_retvals["converged"]
