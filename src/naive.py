"""
Seasonal naive baseline: forecast = ILI+ in the same MMWR week of the previous year.

Uncertainty comes from a block bootstrap of historical errors
(actual - same week last year):

- Errors are drawn only from the same time of year (within SEASON_WINDOW weeks
  of the forecast target). Naive errors near the winter peak can be +/-1.5,
  while off-season errors are around +/-0.03; mixing them would give summer
  forecasts absurdly wide intervals and many negative values clipped to 0.
- Errors involving imputed COVID weeks are excluded, since they aren't real.
- Each path takes `horizon` consecutive errors from one random past week, so
  week-to-week movement within a path stays realistic.

Off-season paths can still be exactly 0 after clipping. That's expected: actual
off-season ILI+ is only ~0.01-0.05, so 0 is a near-correct value, not a bug.

Run from the repo root:
    python -m src.naive
"""

import numpy as np
import pandas as pd

from src import config
from src.evaluate import point_metrics, rolling_forecast, to_epiweek

# Draw errors from historical weeks within this many weeks of the target week.
SEASON_WINDOW = 4


def same_week_last_year(values: pd.Series, epiweeks: pd.Series, target_epiweeks) -> np.ndarray:
    """Value in the same MMWR week one year earlier; week 53 falls back to week 52."""
    lookup = dict(zip(epiweeks.values, values.values))
    out = []
    for ew in target_epiweeks:
        year, week = divmod(int(ew), 100)
        prev = (year - 1) * 100 + week
        if prev not in lookup and week == 53:
            prev = (year - 1) * 100 + 52
        out.append(lookup.get(prev, np.nan))
    return np.array(out, dtype=float)


def week_distance(a: np.ndarray, b: int) -> np.ndarray:
    """Distance between MMWR week numbers on a 52-week circle (week 53 ~ week 52)."""
    a = np.minimum(a, 52)
    b = min(b, 52)
    d = np.abs(a - b)
    return np.minimum(d, 52 - d)


def seasonal_naive(train: pd.Series, horizon: int, n_paths: int,
                   season_window: int | None = SEASON_WINDOW) -> np.ndarray:
    """Seasonal naive paths. season_window=None draws errors from all weeks of the
    year (the original version, kept for comparison in src/diagnostics.py)."""
    epiweeks = train.attrs["epiweek"]

    # Point forecast for the next `horizon` weeks
    future_ew = [to_epiweek(train.index[-1] + pd.Timedelta(weeks=k))
                 for k in range(1, horizon + 1)]
    point = same_week_last_year(train, epiweeks, future_ew)

    # Historical errors: actual - same week last year
    baseline = same_week_last_year(train, epiweeks, epiweeks.values)
    errors = train.values - baseline

    # Exclude errors involving imputed COVID weeks (as actual or as last year's value)
    covid_end_plus_year = pd.Timestamp(config.COVID_END) + pd.Timedelta(weeks=53)
    touches_covid = (train.index >= config.COVID_START) & (train.index <= covid_end_plus_year)
    valid = ~np.isnan(errors) & ~touches_covid

    # Candidate block starts: a full run of `horizon` valid errors, at the same time of year
    n = len(errors)
    idx = np.arange(n - horizon + 1)
    full_block = np.array([valid[i:i + horizon].all() for i in idx], dtype=bool)
    candidates = idx[full_block]
    if season_window is not None:
        week_gap = week_distance(epiweeks.values[:n - horizon + 1] % 100, future_ew[0] % 100)
        seasonal = idx[full_block & (week_gap <= season_window)]
        if len(seasonal) >= 10:       # else: not enough history at this time of year
            candidates = seasonal

    rng = np.random.default_rng([config.RANDOM_SEED, len(train)])
    starts = rng.choice(candidates, size=n_paths)
    noise = errors[starts[:, None] + np.arange(horizon)]

    # Center the noise so the path median equals the naive point forecast.
    # Otherwise skewed errors at the same time of year shift the median away
    # from "same week last year", which changes the baseline itself.
    noise = noise - np.median(noise, axis=0)

    return np.clip(point + noise, 0, None)   # ILI+ can't be negative


if __name__ == "__main__":
    for fold in config.TEST_FOLDS:
        fc = rolling_forecast(seasonal_naive, "naive", fold=fold)
        print(point_metrics(fc).to_string(index=False))
