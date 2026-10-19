"""
Diagnostics for probabilistic forecasts in the shared format
(model, origin, horizon, target_week, path_id, value).

Checks whether the 500 paths are sensible, not just whether the median is accurate:
  - zero share          fraction of path values that are exactly 0 (clipped)
  - 90% coverage        fraction of targets whose actual value falls inside the
                        5th-95th percentile band (should be close to 0.90)
  - interval width      95th - 5th percentile, split into peak vs. shoulder weeks,
                        since a good interval is narrow off-peak and wide at the peak
  - MAE                 of the path median

Usage, from the repo root:
    python -m src.diagnostics naive              # diagnose saved forecast files
    python -m src.diagnostics naive ets chronos
    python -m src.diagnostics --naive-variants   # naive with different seasonal windows
    python -m src.diagnostics naive --by-week    # also print the per-target-week table
    python -m src.diagnostics naive --fold 2024-25   # a different test fold
"""

import argparse
from functools import partial

import numpy as np
import pandas as pd

from src import config
from src.evaluate import forecast_path, load_data, rolling_forecast

# MMWR weeks 48-53 and 1-11 (roughly Dec-mid Mar) are the usual peak period.
# The rest of the test season (Oct-Nov, mid Mar-May) is the "shoulder".
PEAK_WEEKS = set(range(48, 54)) | set(range(1, 12))


def load_forecasts(model: str, fold: str = config.MAIN_FOLD) -> pd.DataFrame:
    return pd.read_csv(forecast_path(model, fold), parse_dates=["origin", "target_week"])


def quantile_table(forecasts: pd.DataFrame) -> pd.DataFrame:
    """One row per (model, origin, horizon, target_week): q05, median, q95, actual."""
    q = (forecasts.groupby(["model", "origin", "horizon", "target_week"])["value"]
                  .quantile([0.05, 0.5, 0.95]).unstack())
    q.columns = ["q05", "median", "q95"]
    q = q.reset_index()

    raw = load_data()
    q = q.merge(raw["ili_plus"].rename("actual"), left_on="target_week",
                right_index=True, how="inner")
    week = q["target_week"].map(raw["mmwr_week"])
    q["period"] = np.where(week.isin(PEAK_WEEKS), "peak", "shoulder")
    return q


def summarize(forecasts: pd.DataFrame) -> pd.DataFrame:
    """One row per model with the headline diagnostics."""
    q = quantile_table(forecasts)
    q["covered"] = (q["actual"] >= q["q05"]) & (q["actual"] <= q["q95"])
    q["width"] = q["q95"] - q["q05"]
    q["abs_err"] = (q["median"] - q["actual"]).abs()

    zeros = forecasts.groupby("model")["value"].apply(lambda v: (v == 0).mean())
    out = q.groupby("model").agg(coverage_90=("covered", "mean"), MAE=("abs_err", "mean"))
    widths = q.pivot_table(index="model", columns="period", values="width", aggfunc="median")
    out["width_shoulder"] = widths.get("shoulder")
    out["width_peak"] = widths.get("peak")
    out.insert(0, "zero_share", zeros)
    return out.reset_index()


def by_target_week(forecasts: pd.DataFrame) -> pd.DataFrame:
    """Per target week: zero share and the 5/50/95 percentiles across all paths and origins."""
    g = forecasts.groupby(["model", "target_week"])["value"]
    return pd.DataFrame({
        "zero_share": g.apply(lambda v: (v == 0).mean()),
        "q05": g.quantile(0.05),
        "median": g.median(),
        "q95": g.quantile(0.95),
    }).reset_index()


def naive_variants(fold: str = config.MAIN_FOLD) -> pd.DataFrame:
    """Re-run seasonal naive with different seasonal error windows (not saved).
    None = errors from all weeks of the year (the original version)."""
    from src.naive import seasonal_naive  # noqa: PLC0415

    runs = [rolling_forecast(partial(seasonal_naive, season_window=w),
                             f"naive_window_{w}", save=False, fold=fold)
            for w in (2, 4, 6, 8, None)]
    return summarize(pd.concat(runs, ignore_index=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("models", nargs="*", help="forecast files in results/forecasts/")
    parser.add_argument("--naive-variants", action="store_true")
    parser.add_argument("--by-week", action="store_true")
    parser.add_argument("--fold", default=config.MAIN_FOLD, choices=list(config.TEST_FOLDS))
    args = parser.parse_args()

    pd.set_option("display.width", 120)
    if args.naive_variants:
        print(naive_variants(args.fold).round(3).to_string(index=False))
    if args.models:
        fc = pd.concat([load_forecasts(m, args.fold) for m in args.models], ignore_index=True)
        print(summarize(fc).round(3).to_string(index=False))
        if args.by_week:
            table = by_target_week(fc)
            num = table.select_dtypes("number").columns
            table[num] = table[num].round(3)
            print(table.to_string(index=False))
    if not (args.naive_variants or args.models):
        parser.print_help()


if __name__ == "__main__":
    main()
