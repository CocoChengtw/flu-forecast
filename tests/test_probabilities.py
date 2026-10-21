"""Run from the repo root: python -m pytest tests"""

import numpy as np
import pandas as pd
import pytest

from src import config
from src.probabilities import (
    brier_score, crossing_probability, event_probabilities, has_run,
    observed_events, onset_probability, season_start, to_path_array,
)

THR = 1.0


def make_forecasts(paths: np.ndarray, origins) -> pd.DataFrame:
    """Shared-format forecasts from an array of shape (n_origins, n_paths, horizon)."""
    n_o, n_p, h = paths.shape
    rows = []
    for i, o in enumerate(origins):
        for p in range(n_p):
            for k in range(h):
                rows.append(("m", o, k + 1, o + pd.Timedelta(weeks=k + 1), p, paths[i, p, k]))
    return pd.DataFrame(rows, columns=["model", "origin", "horizon", "target_week",
                                       "path_id", "value"])


def test_to_path_array_shape_and_order():
    rng = np.random.default_rng(0)
    paths = rng.random((3, 5, 4))
    origins = pd.date_range("2025-10-05", periods=3, freq="W-SUN")
    fc = make_forecasts(paths, origins).sample(frac=1, random_state=1)   # shuffled rows
    got_origins, got = to_path_array(fc)
    assert got.shape == (3, 5, 4)
    assert (got_origins == origins).all()
    np.testing.assert_array_equal(got, paths)


def test_crossing_probability_counts_any_week_strictly_above():
    paths = np.array([[[0.5, 0.5, 0.5, 1.5],     # crosses in week 4
                       [0.5, 0.5, 0.5, 0.5],     # never
                       [1.0, 1.0, 1.0, 1.0],     # equal is not above
                       [2.0, 0.0, 0.0, 0.0]]])   # crosses in week 1
    assert crossing_probability(paths, THR)[0] == 0.5


def test_probabilities_are_bounded():
    rng = np.random.default_rng(1)
    paths = rng.normal(1, 1, (10, 500, 4))
    p = crossing_probability(paths, THR)
    q = onset_probability(paths, rng.random((10, 1)) > 0.5, THR)
    for x in (p, q):
        assert ((x >= 0) & (x <= 1)).all()


def test_has_run():
    above = np.array([[1, 0, 1, 0, 1],
                      [0, 1, 1, 0, 0],
                      [0, 0, 0, 1, 1]], dtype=bool)
    assert has_run(above, 2).tolist() == [False, True, True]
    assert has_run(above, 1).tolist() == [True, True, True]
    assert has_run(above, 3).tolist() == [False, False, False]


def test_onset_uses_observed_origin_week():
    # One path: week 1 above only. Onset needs 2 consecutive weeks, so it
    # happens only if the observed origin week was also above.
    paths = np.array([[[2.0, 0.0, 2.0, 0.0]]])
    assert onset_probability(paths, np.array([[True]]), THR)[0] == 1
    assert onset_probability(paths, np.array([[False]]), THR)[0] == 0


def test_brier_score():
    assert brier_score([1, 0], [1, 0]) == 0
    assert brier_score([0, 1], [1, 0]) == 1
    assert brier_score([0.5, 0.5], [1, 0]) == pytest.approx(0.25)
    assert brier_score([0.8, 0.3, 0.6], [1, 0, 0]) == pytest.approx((0.04 + 0.09 + 0.36) / 3)
    with pytest.raises(ValueError):
        brier_score([1.2], [1])
    with pytest.raises(ValueError):
        brier_score([0.5], [2])


def test_season_start_is_mmwr_week_40():
    assert season_start("2025-09-28") == pd.Timestamp("2025-09-28")   # 2025 week 40 itself
    assert season_start("2026-03-01") == pd.Timestamp("2025-09-28")
    assert season_start("2025-09-21") == pd.Timestamp("2024-09-29")   # week 39 -> previous season


def synthetic_actual():
    weeks = pd.date_range("2025-09-07", periods=20, freq="W-SUN")
    # season starts 2025-09-28 (week 40); 09-21 above but before the season
    values = [0, 0, 2, 0, 0, 2, 0, 2, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    return pd.Series(np.array(values, dtype=float) * THR, index=weeks)


def test_observed_events_status_and_outcomes(monkeypatch):
    monkeypatch.setattr("src.probabilities.THRESHOLDS", {"high": THR})
    monkeypatch.setattr(config, "EARLY_RISE_THRESHOLD", THR)
    actual = synthetic_actual()
    origins = pd.DatetimeIndex(["2025-09-28", "2025-10-05", "2025-10-19", "2025-11-02"])
    obs = observed_events(origins, actual, horizon=4).set_index("origin")

    # 09-28: below; weeks 10-05..10-26 -> 10-12 above; onset pair 10-26/11-02 is outside
    assert obs.loc["2025-09-28", "high_status"] == "below"
    assert obs.loc["2025-09-28", "high_outcome"] == 1
    assert obs.loc["2025-09-28", "onset_outcome"] == 0
    # 10-05: window reaches 11-02, so the 10-26/11-02 pair counts
    assert obs.loc["2025-10-05", "onset_outcome"] == 1
    # 10-19: origin week is below, onset still pending
    assert obs.loc["2025-10-19", "onset_status"] == "pending"
    # 11-02: 10-26 and 11-02 both above -> onset has passed; origin is above
    assert obs.loc["2025-11-02", "onset_status"] == "passed"
    assert obs.loc["2025-11-02", "high_status"] == "above"


def test_event_probabilities_masks_unscored_origins(monkeypatch):
    monkeypatch.setattr("src.probabilities.THRESHOLDS", {"high": THR})
    monkeypatch.setattr(config, "EARLY_RISE_THRESHOLD", THR)
    actual = synthetic_actual()
    origins = pd.DatetimeIndex(["2025-09-28", "2025-11-02"])
    paths = np.full((2, 10, 4), 2 * THR)            # every path above in every week
    probs = event_probabilities(make_forecasts(paths, origins), actual).set_index(["event", "origin"])

    assert probs.loc[("high", pd.Timestamp("2025-09-28")), "probability"] == 1
    assert np.isnan(probs.loc[("high", pd.Timestamp("2025-11-02")), "probability"])
    assert np.isnan(probs.loc[("onset", pd.Timestamp("2025-11-02")), "probability"])


def test_naive_file_probabilities():
    """The saved naive forecasts give bounded probabilities on every scored origin."""
    fc = pd.read_csv(config_forecast("naive"), parse_dates=["origin", "target_week"])
    probs = event_probabilities(fc)
    scored = probs.dropna(subset=["probability"])
    assert scored["probability"].between(0, 1).all()
    assert set(probs["event"]) == {"high", "early_rise", "onset"}
    assert probs["outcome"].isin([0, 1]).all()


def config_forecast(model):
    from src.evaluate import forecast_path
    path = forecast_path(model)
    if not path.exists():
        pytest.skip(f"{path} not found")
    return path
