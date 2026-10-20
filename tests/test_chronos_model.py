"""Run from the repo root: python -m pytest tests
The model tests load amazon/chronos-t5-mini (downloaded on first use) and take ~1 min."""

import numpy as np
import pandas as pd
import pytest

from src import config
from src.evaluate import forecast_path, prepare_series, rolling_forecast

COLUMNS = ["model", "origin", "horizon", "target_week", "path_id", "value"]


def test_rolling_forecast_passes_only_data_up_to_origin():
    """Leak check: model_fn only ever sees weeks up to the origin (both folds)."""
    for fold, (start, _) in config.TEST_FOLDS.items():
        seen = []

        def spy(train, horizon, n_paths):
            seen.append(train.index[-1])
            assert train.attrs["epiweek"].index[-1] == train.index[-1]
            return np.zeros((n_paths, horizon))

        out = rolling_forecast(spy, "spy", save=False, fold=fold)
        assert seen == list(pd.DatetimeIndex(out["origin"].unique()))
        assert min(seen) == pd.Timestamp(start)


@pytest.fixture(scope="module")
def train():
    pytest.importorskip("chronos")
    s = prepare_series()
    t = s.loc[:config.TEST_START].copy()
    t.attrs["epiweek"] = s.attrs["epiweek"].loc[:config.TEST_START]
    return t


def test_chronos_shape_and_values(train):
    from src.chronos_model import chronos_forecast
    paths = chronos_forecast(train, 4, config.N_PATHS)
    assert paths.shape == (config.N_PATHS, 4)
    assert np.isfinite(paths).all()
    assert (paths >= 0).all()


def test_chronos_is_reproducible(train):
    from src.chronos_model import chronos_forecast
    a = chronos_forecast(train, 4, 50)
    b = chronos_forecast(train.copy(), 4, 50)
    np.testing.assert_array_equal(a, b)


def test_chronos_forecast_unchanged_by_future_data(train):
    """Corrupting every week after the origin doesn't change the origin's forecast."""
    from src.chronos_model import chronos_forecast
    s = prepare_series()
    s.loc[s.index > train.index[-1]] = 999.0
    corrupted = s.loc[:train.index[-1]]
    np.testing.assert_array_equal(chronos_forecast(train, 4, 50),
                                  chronos_forecast(corrupted, 4, 50))


def test_chronos_rejects_missing_values(train):
    from src.chronos_model import chronos_forecast
    bad = train.copy()
    bad.iloc[-3] = np.nan
    with pytest.raises(ValueError):
        chronos_forecast(bad, 4, 10)


@pytest.mark.parametrize("fold", list(config.TEST_FOLDS))
def test_saved_chronos_file_matches_shared_schema(fold):
    path = forecast_path("chronos", fold)
    if not path.exists():
        pytest.skip(f"{path} not found; run python -m src.chronos_model")
    fc = pd.read_csv(path, parse_dates=["origin", "target_week"])
    naive = pd.read_csv(forecast_path("naive", fold), parse_dates=["origin", "target_week"])

    assert list(fc.columns) == COLUMNS
    assert (fc["model"] == "chronos").all()
    assert fc["value"].notna().all() and (fc["value"] >= 0).all()
    assert set(fc["horizon"]) == set(config.HORIZONS)
    assert fc["path_id"].nunique() == config.N_PATHS
    assert (fc["target_week"] - fc["origin"] == pd.to_timedelta(7 * fc["horizon"], unit="D")).all()
    # same origins as the baseline, so the comparison is fair
    assert set(fc["origin"]) == set(naive["origin"])
    assert len(fc) == fc["origin"].nunique() * config.N_PATHS * len(config.HORIZONS)
