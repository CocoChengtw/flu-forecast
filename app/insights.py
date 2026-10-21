"""
Numbers behind the dashboard. Pure Python, no web code, so every function can
be checked on its own. Used by app/export_data.py and app/assistant_server.py.

Display unit: ILI+ is the % of outpatient visits that are flu, so
ILI+ x 10 = flu visits per 1,000 doctor visits. Everything shown to users
uses that unit; model files and config stay in raw ILI+.
"""

import numpy as np
import pandas as pd

from src import config
from src.evaluate import mmwr_year_start
from src.probabilities import crossing_probability

PER_1000 = 10                     # raw ILI+ -> flu visits per 1,000 visits
SURGE_LINE = config.HIGH_THRESHOLD
SEASON_LINE = config.EARLY_RISE_THRESHOLD
WATCH_PROB = 0.5                  # chance of crossing within 4 weeks that triggers "Surge watch"
COVID_SEASON = 2020               # 2020-21: flu nearly absent, left out of comparisons

# Case-study week for the dashboard: the main test season's decision point, 4 weeks
# before the Dec 14, 2025 crossing, where all five models have forecasts and they
# disagree most (surge chances 6% to 84%). The outcome is known, so the page can show
# what happened next.
CASE_WEEK = "2025-11-16"

# Signal levels, lowest to highest. The web page holds the actions for each.
LEVELS = ["Quiet", "Elevated", "Surge watch", "Surge"]


# 1. Seasons
def season_of(d: pd.Timestamp) -> int:
    """Start year of the flu season (MMWR week 40 to week 39) containing date d."""
    start = mmwr_year_start(d.year) + pd.Timedelta(weeks=39)
    return d.year if d.date() >= start else d.year - 1


def season_start(year: int) -> pd.Timestamp:
    """Sunday starting MMWR week 40 of `year`."""
    return pd.Timestamp(mmwr_year_start(year) + pd.Timedelta(weeks=39))


def season_label(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


def by_season(history: pd.Series) -> pd.DataFrame:
    """One row per week: season, week of season (0 = early Oct), value per 1,000."""
    df = history.rename("ili_plus").to_frame()
    df["season"] = [season_of(d) for d in df.index]
    df["week"] = [(d - season_start(s)).days // 7 for d, s in zip(df.index, df["season"])]
    df["per_1000"] = df["ili_plus"] * PER_1000
    return df


def surge_history(history: pd.Series) -> pd.DataFrame:
    """For each complete past season: when it crossed the surge line, when it fell
    back, and its peak. Crossing = first of 2 weeks in a row above the line."""
    df = by_season(history)
    rows = []
    for s, g in df.groupby("season"):
        g = g[g["week"] <= 33]                        # weeks 40-20
        if s == COVID_SEASON or len(g) < 30:
            continue
        above = (g["ili_plus"] > SURGE_LINE).to_numpy()
        start = next((i for i in range(len(g) - 1) if above[i] and above[i + 1]), None)
        last = np.where(above)[0][-1] if start is not None else None
        peak = g["ili_plus"].idxmax()
        rows.append({
            "season": s,
            "label": season_label(s),
            "start": g.index[start] if start is not None else pd.NaT,
            "end": g.index[last] if start is not None else pd.NaT,
            "start_week": g["week"].iloc[start] if start is not None else np.nan,
            "end_week": g["week"].iloc[last] if start is not None else np.nan,
            "peak": peak,
            "peak_week": g.loc[peak, "week"],
            "peak_per_1000": g.loc[peak, "per_1000"],
            "weeks_above": int(above.sum()),
        })
    return pd.DataFrame(rows)


# 2. Forecast summaries
def crossing_probs(paths: np.ndarray, current: float, threshold: float) -> list[float] | None:
    """P(any of the next k weeks is above threshold), k = 1..horizon, using the team's
    src/probabilities.py so the page matches the reported Brier scores (k = horizon is
    exactly its crossing_probability). None when already above (the event rule)."""
    if current > threshold:
        return None
    return [float(crossing_probability(paths[:, :k], threshold)) for k in range(1, paths.shape[1] + 1)]


def bands(paths: np.ndarray) -> dict[str, list[float]]:
    """Forecast ranges per week, per 1,000 visits."""
    q = np.percentile(paths * PER_1000, [5, 25, 50, 75, 95], axis=0)
    return {k: [round(float(v), 3) for v in row]
            for k, row in zip(["p5", "p25", "p50", "p75", "p95"], q)}


def one_in(ili_plus: float) -> int | None:
    """0.104 -> 960 (flu is about 1 in 960 doctor visits)."""
    if ili_plus <= 0:
        return None
    n = 100 / ili_plus
    return int(round(n, -1) if n >= 100 else round(n))


def trend_word(history: pd.Series) -> str:
    """Direction over the last 3 weeks."""
    recent = history.iloc[-4:]
    if len(recent) < 4 or recent.iloc[0] <= 0:
        return "steady"
    change = recent.iloc[-1] / recent.iloc[0] - 1
    if change > 0.25:
        return "rising"
    if change < -0.25:
        return "falling"
    return "steady"


def signal_level(current: float, probs: list[float] | None) -> int:
    """0 Quiet, 1 Elevated, 2 Surge watch, 3 Surge."""
    if probs is None:
        return 3
    if probs[-1] >= WATCH_PROB:
        return 2
    if current > SEASON_LINE:
        return 1
    return 0
