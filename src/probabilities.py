"""
Event probabilities from simulated paths, and their Brier scores.

Works on any forecast file in the shared format (model, origin, horizon,
target_week, path_id, value), so every model's probabilities are computed the
same way. Definitions follow notes/analysis_log.md section 6 and src/config.py:

- Threshold crossing (HIGH_THRESHOLD = main output, EARLY_RISE_THRESHOLD = secondary).
  If observed ILI+ at the origin is at or below the threshold, the forecast is
  P(any of the next 1-4 weeks is above it) = share of paths whose maximum over
  weeks 1-4 is above it. If it is already above, the status is "above" and no
  probability is reported (it would sit near 100% for weeks), so those origins
  are not scored.
- Onset: onset week = first of ONSET_CONSECUTIVE_WEEKS (2) consecutive weeks above
  EARLY_RISE_THRESHOLD, counting only weeks from MMWR week 40 of the origin's
  season. If onset has not happened by the origin, the forecast is
  P(onset is confirmed by the end of the 4-week window), i.e. a run of 2 weeks
  above the threshold among [the last observed week(s), path weeks 1-4]. If it
  already happened, the status is "passed" and the origin is not scored.
- Peak timing is NOT computed: "the season peaks within the next 4 weeks"
  depends on weeks after the 4-week horizon, so it can't be read off the paths
  or scored reliably with them.

Observed outcomes use raw ILI+ (as in point_metrics). Which origins are scored
depends only on observed data, so all models are scored on the same origins.

Usage, from the repo root:
    python -m src.probabilities naive chronos
    python -m src.probabilities naive chronos --fold 2024-25
"""

import argparse

import numpy as np
import pandas as pd

from src import config
from src.evaluate import ROOT, forecast_path, load_data, mmwr_year_start

PROB_DIR = ROOT / "results" / "probabilities"

THRESHOLDS = {
    "high": config.HIGH_THRESHOLD,
    "early_rise": config.EARLY_RISE_THRESHOLD,
}


# 1. Probabilities from paths
def to_path_array(forecasts: pd.DataFrame) -> tuple[pd.DatetimeIndex, np.ndarray]:
    """One model's forecasts as (origins, array of shape (n_origins, n_paths, horizon))."""
    if forecasts["model"].nunique() != 1:
        raise ValueError("to_path_array expects forecasts for a single model")
    f = forecasts.sort_values(["origin", "path_id", "horizon"])
    origins = pd.DatetimeIndex(f["origin"].unique())
    n_paths = f["path_id"].nunique()
    horizon = f["horizon"].nunique()
    if len(f) != len(origins) * n_paths * horizon:
        raise ValueError("forecasts are not a complete origin x path x horizon grid")
    return origins, f["value"].to_numpy().reshape(len(origins), n_paths, horizon)


def crossing_probability(paths: np.ndarray, threshold: float) -> np.ndarray:
    """P(any horizon is above threshold): share of paths whose max exceeds it.
    paths: (..., n_paths, horizon) -> (...)."""
    return (paths.max(axis=-1) > threshold).mean(axis=-1)


def has_run(above: np.ndarray, k: int) -> np.ndarray:
    """True where the last axis contains k consecutive True values."""
    run = np.zeros(above.shape[:-1], dtype=int)
    found = np.zeros(above.shape[:-1], dtype=bool)
    for t in range(above.shape[-1]):
        run = np.where(above[..., t], run + 1, 0)
        found |= run >= k
    return found


def onset_probability(paths: np.ndarray, recent_above: np.ndarray, threshold: float,
                      k: int = config.ONSET_CONSECUTIVE_WEEKS) -> np.ndarray:
    """P(k consecutive weeks above threshold within [recent observed weeks, paths]).

    paths: (n_origins, n_paths, horizon). recent_above: (n_origins, k-1) booleans,
    whether each of the last k-1 observed weeks up to the origin (oldest first)
    was above the threshold and in the current season. A run can start in those
    weeks, e.g. origin week above + path week 1 above is onset at the origin week.
    Returns (n_origins,).
    """
    prefix = np.broadcast_to(recent_above[:, None, :],
                             (paths.shape[0], paths.shape[1], recent_above.shape[1]))
    above = np.concatenate([prefix, paths > threshold], axis=-1)
    return has_run(above, k).mean(axis=-1)


def brier_score(prob, outcome) -> float:
    """Mean squared difference between forecast probability and the 0/1 outcome."""
    prob = np.asarray(prob, dtype=float)
    outcome = np.asarray(outcome, dtype=float)
    if prob.shape != outcome.shape:
        raise ValueError("prob and outcome must have the same shape")
    if ((prob < 0) | (prob > 1)).any() or not np.isin(outcome, [0, 1]).all():
        raise ValueError("prob must be in [0, 1] and outcome must be 0/1")
    return float(np.mean((prob - outcome) ** 2))


# 2. Observed events
def season_start(origin) -> pd.Timestamp:
    """Sunday of MMWR week 40 of the season containing `origin`."""
    origin = pd.Timestamp(origin)
    year = origin.year
    start = pd.Timestamp(mmwr_year_start(year)) + pd.Timedelta(weeks=39)
    if origin < start:
        start = pd.Timestamp(mmwr_year_start(year - 1)) + pd.Timedelta(weeks=39)
    return start


def observed_events(origins, actual: pd.Series, horizon: int = max(config.HORIZONS),
                    k: int = config.ONSET_CONSECUTIVE_WEEKS) -> pd.DataFrame:
    """Per origin: what was known at the origin (status) and what happened next (outcome).

    actual: raw weekly ILI+ indexed by week_start. Weeks before the origin's
    season (MMWR week 40) are treated as below the threshold for onset.
    """
    week = pd.Timedelta(weeks=1)
    rows = []
    for origin in origins:
        future = actual.reindex([origin + h * week for h in range(1, horizon + 1)])
        if future.isna().any():
            raise ValueError(f"observed data missing for weeks after {origin.date()}")
        row = {"origin": origin, "actual_origin": actual[origin]}

        for name, thr in THRESHOLDS.items():
            row[f"{name}_status"] = "above" if actual[origin] > thr else "below"
            row[f"{name}_outcome"] = int((future > thr).any())

        # Onset (early rise): only weeks in the current season count
        thr = config.EARLY_RISE_THRESHOLD
        season = actual.loc[season_start(origin):origin + horizon * week] > thr
        past = season.loc[:origin].to_numpy()
        row["onset_status"] = "passed" if has_run(past, k) else "pending"
        recent = season.loc[:origin].iloc[-(k - 1):].to_numpy() if k > 1 else np.array([])
        recent = np.concatenate([np.zeros(k - 1 - len(recent), dtype=bool), recent])
        row["recent_above"] = recent
        window = np.concatenate([recent, (future > thr).to_numpy()])
        row["onset_outcome"] = int(has_run(window, k))
        rows.append(row)
    return pd.DataFrame(rows)


# 3. Put it together
def event_probabilities(forecasts: pd.DataFrame, actual: pd.Series | None = None) -> pd.DataFrame:
    """Long table, one row per (model, origin, event):
    model, origin, event, threshold, status, probability, outcome.
    probability is NaN when status is "above"/"passed" (not forecast, not scored)."""
    if actual is None:
        actual = load_data()["ili_plus"]
    out = []
    for model, f in forecasts.groupby("model"):
        origins, paths = to_path_array(f)
        obs = observed_events(origins, actual, horizon=paths.shape[-1])
        recent = np.stack(obs["recent_above"].to_numpy())

        probs = {name: crossing_probability(paths, thr) for name, thr in THRESHOLDS.items()}
        probs["onset"] = onset_probability(paths, recent, config.EARLY_RISE_THRESHOLD)
        thresholds = {**THRESHOLDS, "onset": config.EARLY_RISE_THRESHOLD}
        scored = {"high": "below", "early_rise": "below", "onset": "pending"}

        for event, p in probs.items():
            status = obs[f"{event}_status"].to_numpy()
            out.append(pd.DataFrame({
                "model": model,
                "origin": origins,
                "event": event,
                "threshold": thresholds[event],
                "status": status,
                "probability": np.where(status == scored[event], p, np.nan),
                "outcome": obs[f"{event}_outcome"].to_numpy(),
            }))
    return pd.concat(out, ignore_index=True)


def brier_table(probs: pd.DataFrame) -> pd.DataFrame:
    """Brier score per model and event, over the origins where a probability is reported."""
    scored = probs.dropna(subset=["probability"])
    origin_sets = scored.groupby(["event", "model"])["origin"].apply(frozenset)
    for event, sets in origin_sets.groupby(level="event"):
        if sets.nunique() > 1:
            raise ValueError(f"{event}: models are scored on different origins")
    return (scored.groupby(["model", "event"])
                  .apply(lambda g: pd.Series({
                      "brier": brier_score(g["probability"], g["outcome"]),
                      "n_origins": len(g),
                      "event_rate": g["outcome"].mean(),
                  }), include_groups=False)
                  .reset_index())


def probability_path(model_name: str, fold: str = config.MAIN_FOLD):
    """Same layout as forecast files: main fold at the top, other folds in a subfolder."""
    if fold == config.MAIN_FOLD:
        return PROB_DIR / f"{model_name}.csv"
    return PROB_DIR / f"fold_{fold}" / f"{model_name}.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("models", nargs="+", help="forecast files in results/forecasts/")
    parser.add_argument("--fold", default=config.MAIN_FOLD, choices=list(config.TEST_FOLDS))
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()

    frames = []
    for m in args.models:
        fc = pd.read_csv(forecast_path(m, args.fold), parse_dates=["origin", "target_week"])
        p = event_probabilities(fc)
        if not args.no_save:
            path = probability_path(m, args.fold)
            path.parent.mkdir(parents=True, exist_ok=True)
            p.to_csv(path, index=False)
            print(f"{m} [{args.fold}] -> {path.relative_to(ROOT)}")
        frames.append(p)

    pd.set_option("display.width", 120)
    print(brier_table(pd.concat(frames, ignore_index=True)).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
