"""
Build app/public/data.json: everything the dashboard shows, in one file.

Reads the shared ILI+ data and every model file in results/forecasts/, so a
new model appears on the page after re-running this script. Run it after
fetching new data or saving new model results:

    python app/export_data.py

Live forecast: if a model saves a forecast from the latest week to
results/forecasts/live/<model>.csv (shared format, one origin), it is used.
Otherwise the seasonal baseline is run here, since it takes under a second.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

APP = Path(__file__).resolve().parent
ROOT = APP.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(APP))

import insights as ins                                             # noqa: E402
from src import config                                             # noqa: E402
from src.evaluate import FORECAST_DIR, forecast_path, load_data, prepare_series  # noqa: E402
from src.compare import crps_samples                               # noqa: E402
from src.naive import seasonal_naive                               # noqa: E402

OUT = APP / "public" / "data.json"
HORIZON = max(config.HORIZONS)

# Every model the team plans to run. Missing files show as "coming" on the page.
MODELS = [
    {"id": "naive", "name": "Seasonal baseline", "kind": "Baseline",
     "about": "Same week last year", "owner": "Coco"},
    {"id": "ets", "name": "Exponential smoothing", "kind": "Statistical",
     "about": "Weights recent weeks most", "owner": "Coco"},
    {"id": "arima", "name": "ARIMA", "kind": "Statistical",
     "about": "Weekly patterns plus the yearly cycle", "owner": "Coco"},
    {"id": "prophet", "name": "Prophet", "kind": "Statistical",
     "about": "Trend plus seasonality", "owner": "Coco"},
    {"id": "chronos", "name": "Chronos", "kind": "AI",
     "about": "Pre-trained AI forecasting model", "owner": "Christina"},
]


def day(d) -> str:
    return pd.Timestamp(d).strftime("%Y-%m-%d")


def r(x: float, n: int = 3) -> float:
    return round(float(x), n)


def to_paths(fc: pd.DataFrame) -> np.ndarray:
    return fc.pivot(index="path_id", columns="horizon", values="value").to_numpy()


def live_forecast(history: pd.Series) -> tuple[str, pd.Timestamp, np.ndarray]:
    """(model id, origin, paths) for the latest week."""
    for m in MODELS[::-1]:                                 # prefer the most advanced model
        path = FORECAST_DIR / "live" / f"{m['id']}.csv"
        if path.exists():
            fc = pd.read_csv(path, parse_dates=["origin"])
            origin = fc["origin"].max()
            return m["id"], origin, to_paths(fc[fc["origin"] == origin])
    s = prepare_series(cutoff=day(history.index.max()))
    return "naive", s.index.max(), seasonal_naive(s, HORIZON, config.N_PATHS)


# Sample results for models whose real results aren't saved yet, so the page can
# show what they will add. They live only in data.json (flagged "sample": true and
# labeled on the page), never in results/forecasts/. Turn off once real results exist.
SAMPLE_MODELS = False
# (how much of the true future each sample model "sees", base spread, spread growth
# per week ahead, how much recent momentum it carries forward)
SAMPLE_SPECS = {
    "ets": (0.55, 0.30, 0.10, 0.80),
    "arima": (0.60, 0.28, 0.09, 0.75),
    "prophet": (0.40, 0.38, 0.12, 0.50),
    "chronos": (0.72, 0.22, 0.08, 0.90),
}


def real_paths(model: str, fold: str) -> dict | None:
    """{origin: paths} from a saved forecast file, or None if it doesn't exist."""
    path = forecast_path(model, fold)
    if not path.exists():
        return None
    fc = pd.read_csv(path, parse_dates=["origin"])
    return {o: to_paths(g) for o, g in fc.groupby("origin")}


def momentum(history: pd.Series, origin: pd.Timestamp) -> float:
    """Weekly growth factor over the last 2 weeks, clipped to a sensible range."""
    past = history.loc[:origin].iloc[-3:]
    g = (max(past.iloc[-1], 1e-3) / max(past.iloc[0], 1e-3)) ** 0.5
    return float(np.clip(g, 0.7, 1.5))


def sample_paths(model: str, fold: str, history: pd.Series) -> dict:
    """Illustrative forecasts: a blend of what actually happened and recent momentum,
    with model-specific accuracy and spread."""
    see, sd0, sd1, carry = SAMPLE_SPECS[model]
    rng = np.random.default_rng([config.RANDOM_SEED, sum(map(ord, model + fold))])
    start, end = config.TEST_FOLDS[fold]
    out = {}
    for o in history.loc[start:end].index:
        after = history.loc[o + pd.Timedelta(weeks=1):o + pd.Timedelta(weeks=HORIZON)]
        if len(after) < HORIZON:
            continue
        last = max(history.loc[o], 5e-3)
        g = momentum(history, o) ** carry
        h = np.arange(1, HORIZON + 1)
        w = see * (1 - 0.08 * (h - 1))
        log_mid = w * np.log(np.maximum(after.to_numpy(), 5e-3)) + (1 - w) * np.log(last * g ** h)
        out[o] = np.exp(log_mid + rng.normal(0, 1, (config.N_PATHS, HORIZON)) * (sd0 + sd1 * h))
    return out


def sample_live(model: str, history: pd.Series, origin: pd.Timestamp) -> np.ndarray:
    """Illustrative forecast from the latest week: recent momentum, damped per model."""
    _, sd0, sd1, carry = SAMPLE_SPECS[model]
    rng = np.random.default_rng([config.RANDOM_SEED, sum(map(ord, model))])
    h = np.arange(1, HORIZON + 1)
    mid = history.loc[origin] * momentum(history, origin) ** (carry * h)
    return mid * np.exp(rng.normal(0, 1, (config.N_PATHS, HORIZON)) * (sd0 + sd1 * h))


def first_crossing(history: pd.Series, start, end) -> pd.Timestamp | None:
    """First of 2 weeks in a row above the surge line within a test season."""
    s = history.loc[start:pd.Timestamp(end) + pd.Timedelta(weeks=HORIZON)]
    above = (s > ins.SURGE_LINE).to_numpy()
    return next((s.index[i] for i in range(len(s) - 1) if above[i] and above[i + 1]), None)


def summarize(paths_by_origin: dict, fold: str, history: pd.Series) -> dict:
    """Every forecast in a test season with what happened, plus accuracy, surge-call
    score, interval coverage and how many weeks of warning the model gave."""
    origins, briers, errors, hits, crps = [], [], [[] for _ in range(HORIZON)], [], []
    crossing = first_crossing(history, *config.TEST_FOLDS[fold])
    warning = 0
    for origin, paths in sorted(paths_by_origin.items()):
        current = float(history.loc[origin])
        after = history.loc[origin + pd.Timedelta(weeks=1):origin + pd.Timedelta(weeks=HORIZON)]
        probs = ins.crossing_probs(paths, current, ins.SURGE_LINE)
        crossed = bool((after > ins.SURGE_LINE).any())
        b = ins.bands(paths)
        for k, v in enumerate(after.to_numpy()):
            errors[k].append(abs(np.median(paths[:, k]) - v))
            crps.append(crps_samples(paths[:, k], v))         # same CRPS as src/compare.py
            hits.append(b["p5"][k] <= v * ins.PER_1000 <= b["p95"][k])
        if probs is not None:
            briers.append((probs[-1] - crossed) ** 2)
            if crossing is not None and origin < crossing and probs[-1] >= 0.5 and not warning:
                warning = (crossing - origin).days // 7
        origins.append({"origin": day(origin), "bands": b, "actual": [r(v * ins.PER_1000) for v in after],
                        "chance": None if probs is None else r(probs[-1]), "crossed": crossed})
    return {
        "origins": origins,
        "mae": [r(np.mean(e) * ins.PER_1000) for e in errors],
        "brier": r(np.mean(briers)) if briers else None,
        "coverage": r(np.mean(hits), 2) if hits else None,
        "crps": r(np.mean(crps) * ins.PER_1000) if crps else None,
        "warningWeeks": warning,
        "crossing": day(crossing) if crossing is not None else None,
    }


def model_entry(m: dict, history: pd.Series, origin: pd.Timestamp, live_naive: np.ndarray) -> dict:
    folds, sample = {}, False
    for fold in config.TEST_FOLDS:
        paths = real_paths(m["id"], fold)
        if paths is None and SAMPLE_MODELS and m["id"] in SAMPLE_SPECS:
            paths, sample = sample_paths(m["id"], fold, history), True
        folds[fold] = summarize(paths, fold, history) if paths else None
    live = live_naive if m["id"] == "naive" else (
        sample_live(m["id"], history, origin) if sample else None)
    current = float(history.loc[origin])
    probs = None if live is None else ins.crossing_probs(live, current, ins.SURGE_LINE)
    return {**m, "sample": sample, "folds": folds,
            "live": None if live is None else {"chance": None if probs is None else [r(p) for p in probs],
                                               "mid4": ins.bands(live)["p50"][-1]}}


def season_layers(seasons: pd.DataFrame, dates: list[pd.Timestamp], current_season: int) -> list[dict]:
    """For each date: the normal range of past seasons at that time of year
    (25th to 75th percentile and median) and last season's value."""
    past = seasons[(seasons["season"] < current_season) & (seasons["season"] != ins.COVID_SEASON)]
    out = []
    for d in dates:
        s = ins.season_of(d)
        wk = min((d - ins.season_start(s)).days // 7, 51)    # week 52 exists only in 53-week years
        vals = past[(past["week"] == wk) & (past["season"] < s)]["per_1000"]
        last = past[(past["week"] == wk) & (past["season"] == s - 1)]["per_1000"]
        out.append({"date": day(d),
                    "lo": r(vals.quantile(0.25)) if len(vals) else None,
                    "mid": r(vals.median()) if len(vals) else None,
                    "hi": r(vals.quantile(0.75)) if len(vals) else None,
                    "last": r(last.iloc[0]) if len(last) else None})
    return out


def lead_time_from(level: float, seasons: pd.DataFrame, surges: pd.DataFrame) -> list[int]:
    """Weeks from the first week a past season reached `level` (raw ILI+) to its surge crossing."""
    weeks = []
    for row in surges.dropna(subset=["start_week"]).itertuples():
        g = seasons[seasons["season"] == row.season]
        reached = g[(g["ili_plus"] >= level) & (g["week"] <= row.start_week)]
        if len(reached):
            weeks.append(int(row.start_week - reached["week"].iloc[0]))
    return weeks


def state_snapshot() -> dict | None:
    """Latest ILI+ per state (within the last 4 weeks) and the change over 3 weeks."""
    path = ROOT / "data" / "processed" / "ili_plus_state_weekly.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    newest = df["epiweek"].max()
    rows = []
    for state, g in df.groupby("state"):
        g = g.sort_values("epiweek")
        if newest - g["epiweek"].iloc[-1] > 4:              # stale: treat as no data
            continue
        v = g["ili_plus"].iloc[-1]
        prev = g["ili_plus"].iloc[-4] if len(g) >= 4 else np.nan
        rows.append({"state": state, "epiweek": int(g["epiweek"].iloc[-1]),
                     "v": r(v * ins.PER_1000), "change": None if pd.isna(prev) else r((v - prev) * ins.PER_1000)})
    return {"epiweek": int(newest), "states": rows}


def main() -> None:
    history = load_data()["ili_plus"]
    model_id, origin, paths = live_forecast(history)
    current = float(history.loc[origin])
    probs = ins.crossing_probs(paths, current, ins.SURGE_LINE)
    level = ins.signal_level(current, probs)

    seasons = ins.by_season(history)
    surges = ins.surge_history(history)
    this_season = ins.season_of(origin)
    crossed = surges.dropna(subset=["start"])
    typical = ins.season_start(this_season) + pd.Timedelta(weeks=int(crossed["start_week"].median()))

    recent = history.loc[origin - pd.Timedelta(weeks=20):origin]
    fc_dates = [origin + pd.Timedelta(weeks=k) for k in range(1, HORIZON + 1)]
    b = ins.bands(paths)

    # Numbers behind the recommendations: all from the forecast or past seasons
    lead = lead_time_from(max(current, ins.SEASON_LINE), seasons, surges)
    stats = {
        "medianPeak": r(surges["peak_per_1000"].median(), 1),
        "maxPeak": r(surges["peak_per_1000"].max(), 1),
        "medianWeeksAbove": int(crossed["weeks_above"].median()),
        "lagToPeak": int((crossed["peak_week"] - crossed["start_week"]).median()),
        "weeksToTypical": max(int((typical - origin).days // 7), 0),
        "earliestCrossing": day(ins.season_start(this_season) + pd.Timedelta(weeks=int(crossed["start_week"].min()))),
        "leadMedian": int(np.median(lead)) if lead else None,
        "leadMin": min(lead) if lead else None,
        "leadMax": max(lead) if lead else None,
        "high4": b["p95"][-1],
        "mid4": b["p50"][-1],
        "weeksAboveSoFar": int((history.loc[ins.season_start(this_season):origin] > ins.SURGE_LINE).sum()),
        "seasonsCrossed": len(crossed),
        "seasonsTotal": len(surges),
    }
    # Audience-specific numbers: test positivity (clinics), peak timing (hospitals),
    # state spread (public health), odds per visit (individuals)
    raw = pd.read_csv(ROOT / "data" / "processed" / "ili_plus_weekly.csv", parse_dates=["week_start"])
    pos = raw[raw["region"] == config.REGION].set_index("week_start")["pct_positive"]
    peak_pos = [pos.get(p) for p in surges["peak"] if p in pos.index]
    states = state_snapshot()
    nat_now = current * ins.PER_1000
    risers = sorted([st for st in (states or {}).get("states", []) if st["change"] is not None],
                    key=lambda st: st["change"], reverse=True)
    earliest = ins.season_start(this_season) + pd.Timedelta(weeks=int(crossed["start_week"].min()))
    stats.update({
        "posNow": r(pos.loc[origin], 1),
        "posPeak": r(np.median(peak_pos), 0),
        "peakDate": day(typical + pd.Timedelta(weeks=stats["lagToPeak"])),
        "oneInPeak": ins.one_in(stats["medianPeak"] / ins.PER_1000),
        "weeksToEarliest": max(int((earliest - origin).days // 7), 0),
        "statesAbove": sum(st["v"] > nat_now for st in (states or {}).get("states", [])),
        "statesTotal": len((states or {}).get("states", [])),
        "topRiser": risers[0] if risers else None,
    })
    layers = season_layers(seasons, list(recent.index) + fc_dates, this_season)
    normal_now = next(l["mid"] for l in layers if l["date"] == day(origin))
    stats["normalNow"] = normal_now
    stats["vsNormal"] = r(current * ins.PER_1000 / normal_now, 1) if normal_now else None
    data = {
        "updated": day(origin),
        "lines": {"surge": r(ins.SURGE_LINE * ins.PER_1000, 2),
                  "season": r(ins.SEASON_LINE * ins.PER_1000, 2)},
        "now": {
            "value": r(current * ins.PER_1000, 2),
            "oneIn": ins.one_in(current),
            "trend": ins.trend_word(history.loc[:origin]),
            "level": level,
            "levelName": ins.LEVELS[level],
            "chance": None if probs is None else [r(p) for p in probs],
            "model": model_id,
        },
        "recent": [{"date": day(d), "v": r(v * ins.PER_1000)} for d, v in recent.items()],
        # Weekly values covering every test season, for the backtest replay
        "weekly": [{"date": day(d), "v": r(v * ins.PER_1000)}
                   for d, v in history.loc[pd.Timestamp(min(f[0] for f in config.TEST_FOLDS.values()))
                                         - pd.Timedelta(weeks=12):].items()],
        "forecast": {"dates": [day(d) for d in fc_dates], **b},
        "layers": layers,
        "stats": stats,
        "states": states,
        "seasons": [
            {"season": int(s), "label": ins.season_label(s),
             "points": [[int(w), r(v)] for w, v in zip(g["week"], g["per_1000"]) if w <= 34]}
            for s, g in seasons.groupby("season") if s != ins.COVID_SEASON
        ],
        "currentSeason": this_season,
        "surges": [
            {"label": row.label,
             "start": None if pd.isna(row.start) else day(row.start),
             "end": None if pd.isna(row.end) else day(row.end),
             "startWeek": None if pd.isna(row.start_week) else int(row.start_week),
             "endWeek": None if pd.isna(row.end_week) else int(row.end_week),
             "peak": day(row.peak), "peakWeek": int(row.peak_week),
             "peakValue": r(row.peak_per_1000, 1), "weeksAbove": row.weeks_above}
            for row in surges.itertuples()
        ],
        "typicalCrossing": day(typical),
        "models": [model_entry(m, history, origin, paths) for m in MODELS],
        "mainFold": config.MAIN_FOLD,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    print(f"Wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.0f} KB), "
          f"data through {data['updated']}, level: {data['now']['levelName']}")


if __name__ == "__main__":
    main()
