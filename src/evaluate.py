from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from src import config

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "processed" / "ili_plus_weekly.csv"
FORECAST_DIR = ROOT / "results" / "forecasts"

# 0. MMWR week helpers
def mmwr_year_start(year: int) -> date:
    """Sunday starting MMWR week 1 of `year` (the week containing Jan 4)."""
    jan4 = date(year, 1, 4)
    return jan4 - timedelta(days=(jan4.weekday() + 1) % 7)
 
 
def to_epiweek(d) -> int:
    """MMWR epiweek (e.g. 202552) of the week containing date `d`."""
    d = pd.Timestamp(d).date()
    year = d.year + 1
    while mmwr_year_start(year) > d:
        year -= 1
    return year * 100 + (d - mmwr_year_start(year)).days // 7 + 1

# 1. Load data
def load_data() -> pd.DataFrame:
    """Weekly ILI+ for config.REGION, indexed by week_start (Sunday), raw values."""
    df = pd.read_csv(DATA_FILE, parse_dates=["week_start"])
    df = df[df["region"] == config.REGION]
    df = (df.set_index("week_start")
            .sort_index()
            .loc[config.TRAIN_START:, ["epiweek", "ili_plus"]])
    df["mmwr_week"] = df["epiweek"] % 100
 
    gaps = pd.date_range(df.index.min(), df.index.max(), freq="W-SUN").difference(df.index)
    if len(gaps):
        print(f"Warning: {len(gaps)} missing weeks, e.g. {gaps[0].date()}")
    return df

def impute_covid(df: pd.DataFrame, cutoff: str = config.TEST_START) -> pd.DataFrame:
    """Replace ILI+ in the COVID window with the same-MMWR-week mean of other seasons.
 
    Only seasons before `cutoff` (the start of the test fold) are used for the
    means, so no test data leaks into training. Adds `is_imputed`.
    """
    df = df.copy()
    covid = (df.index >= config.COVID_START) & (df.index <= config.COVID_END)
    reference = (~covid) & (df.index < cutoff)
    weekly_mean = df.loc[reference].groupby("mmwr_week")["ili_plus"].mean()
    weekly_mean = weekly_mean.reindex(range(1, 54))
    if pd.isna(weekly_mean[53]):
        weekly_mean[53] = weekly_mean[52]
 
    df["is_imputed"] = covid
    df.loc[covid, "ili_plus"] = df.loc[covid, "mmwr_week"].map(weekly_mean).values
    return df

def prepare_series(cutoff: str = config.TEST_START) -> pd.Series:
    """Model-ready series: COVID-imputed ILI+, with epiweeks attached in .attrs."""
    df = impute_covid(load_data(), cutoff)
    s = df["ili_plus"].copy()
    s.attrs["epiweek"] = df["epiweek"]
    return s

# 2. Forecast origins: every week of the test period
def get_origins(s: pd.Series, start: str = config.TEST_START,
                end: str = config.TEST_END) -> pd.DatetimeIndex:
    """Every week of the test fold, as long as the full horizon is observed."""
    last_origin = s.index.max() - pd.Timedelta(weeks=max(config.HORIZONS))
    origins = s.loc[start:end].index
    return origins[origins <= last_origin]

# 3. Rolling forecast: the core
def forecast_path(model_name: str, fold: str = config.MAIN_FOLD):
    """Main fold: results/forecasts/<model>.csv; other folds in a subfolder."""
    if fold == config.MAIN_FOLD:
        return FORECAST_DIR / f"{model_name}.csv"
    return FORECAST_DIR / f"fold_{fold}" / f"{model_name}.csv"


def rolling_forecast(model_fn, model_name: str, save: bool = True,
                     fold: str = config.MAIN_FOLD) -> pd.DataFrame:
    """Run model_fn at every origin of a test fold (see config.TEST_FOLDS)."""
    start, end = config.TEST_FOLDS[fold]
    s = prepare_series(cutoff=start)
    horizon = max(config.HORIZONS)
    n_paths = config.N_PATHS
    frames = []

    for origin in get_origins(s, start, end):
        train = s.loc[:origin].copy()                     # data up to the origin only
        train.attrs["epiweek"] = s.attrs["epiweek"].loc[:origin]

        paths = np.asarray(model_fn(train, horizon, n_paths), dtype=float)
        if paths.shape != (n_paths, horizon):
            raise ValueError(f"{model_name}: expected shape {(n_paths, horizon)}, "
                             f"got {paths.shape} at origin {origin.date()}")

        h = np.tile(np.arange(1, horizon + 1), n_paths)
        frames.append(pd.DataFrame({
            "model": model_name,
            "origin": origin,
            "horizon": h,
            "target_week": origin + pd.to_timedelta(7 * h, unit="D"),
            "path_id": np.repeat(np.arange(n_paths), horizon),
            "value": paths.ravel(),
        }))

    out = pd.concat(frames, ignore_index=True)
    if save:
        path = forecast_path(model_name, fold)
        path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(path, index=False)
        print(f"{model_name} [{fold}]: {out['origin'].nunique()} origins -> "
              f"{path.relative_to(ROOT)} ({len(out):,} rows)")
    return out

# 4. Point-forecast metrics
def point_metrics(forecasts: pd.DataFrame) -> pd.DataFrame:
    """MAE and RMSE of the path median vs. observed raw ILI+, by model and horizon."""
    actual = load_data()["ili_plus"].rename("actual")
    median = (forecasts.groupby(["model", "origin", "horizon", "target_week"])["value"]
                       .median().rename("forecast").reset_index())
    m = median.merge(actual, left_on="target_week", right_index=True, how="inner")
    m["err"] = m["forecast"] - m["actual"]
    return (m.groupby(["model", "horizon"])
             .agg(MAE=("err", lambda e: e.abs().mean()),
                  RMSE=("err", lambda e: np.sqrt((e ** 2).mean())),
                  n=("err", "size"))
             .reset_index())