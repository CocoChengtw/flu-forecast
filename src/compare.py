"""
Compare every model in results/forecasts/ on both test folds.
 
Outputs:
    results/metrics.csv            model x fold x horizon: MAE, RMSE, CRPS, 90% coverage
    results/metrics_summary.csv    model x fold, averaged over horizons, with % change vs naive
    results/figures/model_error_by_horizon.png
    results/figures/forecast_vs_actual.png   (main fold, horizons 1 and 4)
 
Any new forecast file (e.g. chronos.csv) is picked up automatically.
 
Run from the repo root:
    python -m src.compare
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import config
from src.evaluate import FORECAST_DIR, ROOT, forecast_path, load_data

FIGURES = ROOT / "results" / "figures"

# Fixed colors per model (validated categorical palette); naive is the gray reference
COLORS = {"naive": "#8a8a85", "arima": "#2a78d6", "ets": "#eb6834",
          "prophet": "#1baf7a", "chronos": "#eda100"}
ORDER = ["naive", "ets", "arima", "prophet", "chronos"]
INK, MUTED, GRID = "#1f1f1e", "#6b6b66", "#e6e5e0"


def models_available() -> list[str]:
    found = {p.stem for p in FORECAST_DIR.glob("*.csv")}
    return [m for m in ORDER if m in found] + sorted(found - set(ORDER))


def crps_samples(x: np.ndarray, y: float) -> float:
    """Sample CRPS: E|X - y| - 0.5 E|X - X'| (lower is better)."""
    x = np.sort(x)
    n = len(x)
    i = np.arange(1, n + 1)
    return np.mean(np.abs(x - y)) - np.sum((2 * i - n - 1) * x) / n ** 2
 
 
def score(forecasts: pd.DataFrame, actual: pd.Series) -> pd.DataFrame:
    rows = []
    for (model, origin, h, target), g in forecasts.groupby(
            ["model", "origin", "horizon", "target_week"]):
        if target not in actual.index:
            continue
        x, y = g["value"].to_numpy(), actual[target]
        lo, med, hi = np.quantile(x, [0.05, 0.5, 0.95])
        rows.append(dict(model=model, origin=origin, horizon=h, target_week=target,
                         actual=y, median=med, q05=lo, q95=hi,
                         err=med - y, crps=crps_samples(x, y), covered=lo <= y <= hi))
    return pd.DataFrame(rows)
 
 
def metrics(scored: pd.DataFrame) -> pd.DataFrame:
    return (scored.groupby(["model", "horizon"])
                  .agg(MAE=("err", lambda e: e.abs().mean()),
                       RMSE=("err", lambda e: np.sqrt((e ** 2).mean())),
                       CRPS=("crps", "mean"),
                       coverage_90=("covered", "mean"),
                       n=("err", "size"))
                  .reset_index())
 
 
def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
 
 
def plot_error_by_horizon(table: pd.DataFrame, models: list[str]) -> None:
    folds = list(config.TEST_FOLDS)
    fig, axes = plt.subplots(1, len(folds), figsize=(11, 4.2), sharey=True)
    for ax, fold in zip(np.atleast_1d(axes), folds):
        t = table[table["fold"] == fold]
        for m in models:
            g = t[t["model"] == m].sort_values("horizon")
            if g.empty:
                continue
            ls = "--" if m == "naive" else "-"
            ax.plot(g["horizon"], g["CRPS"], ls, color=COLORS.get(m, MUTED), lw=2,
                    marker="o", ms=6, mec="white", mew=1.5, label=m)
            ax.annotate(m, (g["horizon"].iloc[-1], g["CRPS"].iloc[-1]), xytext=(6, 0),
                        textcoords="offset points", va="center", fontsize=9, color=INK)
        ax.set_title(f"Test fold {fold}" + (" (main)" if fold == config.MAIN_FOLD else ""),
                     fontsize=11, color=INK, loc="left")
        ax.set_xticks(config.HORIZONS)
        ax.set_xlabel("Weeks ahead", color=MUTED, fontsize=9)
        ax.set_xlim(0.8, max(config.HORIZONS) + 0.7)
        style(ax)
    np.atleast_1d(axes)[0].set_ylabel("CRPS (lower is better)", color=MUTED, fontsize=9)
    np.atleast_1d(axes)[0].legend(frameon=False, fontsize=9, loc="upper left")
    fig.suptitle("Forecast error by horizon", x=0.06, ha="left", fontsize=13,
                 color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGURES / "model_error_by_horizon.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
 
 
def plot_forecast_vs_actual(scored: pd.DataFrame, actual: pd.Series,
                            models: list[str]) -> None:
    start, end = config.TEST_FOLDS[config.MAIN_FOLD]
    horizons = [1, 4]
    fig, axes = plt.subplots(len(models), len(horizons), figsize=(11, 2.3 * len(models)),
                             sharex=True, sharey=True, squeeze=False)
    window = actual[(actual.index >= start) &
                    (actual.index <= pd.Timestamp(end) + pd.Timedelta(weeks=4))]
    ylim = 1.6 * window.max()   # shared scale set by the observed season
    for r, m in enumerate(models):
        for c, h in enumerate(horizons):
            ax = axes[r, c]
            g = scored[(scored["model"] == m) & (scored["horizon"] == h)].sort_values("target_week")
            color = COLORS.get(m, MUTED)
            ax.fill_between(g["target_week"], g["q05"], g["q95"], color=color, alpha=0.18, lw=0)
            ax.plot(g["target_week"], g["median"], color=color, lw=2)
            ax.plot(window.index, window.values, color=INK, lw=1.4)
            ax.axhline(config.HIGH_THRESHOLD, color=MUTED, lw=0.9, ls=":")
            ax.set_ylim(0, ylim)
            over = g["q95"] > ylim
            if over.any():   # intervals cut off by the shared axis: say so instead of squashing
                ax.text(0.99, 0.95, f"band exceeds axis in {over.sum()} week{'s' if over.sum() > 1 else ''} "
                        f"(max {g['q95'].max():.1f})",
                        transform=ax.transAxes, ha="right", va="top", fontsize=8, color=MUTED)
            if r == 0:
                ax.set_title(f"{h} week{'s' if h > 1 else ''} ahead", fontsize=11,
                             color=INK, loc="left")
            if c == 0:
                ax.set_ylabel(m, color=color, fontsize=11, fontweight="bold")
            style(ax)
    fig.text(0.06, -0.01, "Black = observed ILI+.  Line = path median, band = 90% interval.  "
             "Dotted = high-activity threshold.", fontsize=9, color=MUTED)
    fig.suptitle(f"Forecasts vs. observed ILI+, {config.MAIN_FOLD} season", x=0.06,
                 ha="left", fontsize=13, color=INK, fontweight="bold")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIGURES / "forecast_vs_actual.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
 
 
def main() -> None:
    actual = load_data()["ili_plus"]
    models = models_available()
    tables, main_scored = [], None
    for fold in config.TEST_FOLDS:
        fcs = [pd.read_csv(forecast_path(m, fold), parse_dates=["origin", "target_week"])
               for m in models if forecast_path(m, fold).exists()]
        scored = score(pd.concat(fcs, ignore_index=True), actual)
        t = metrics(scored)
        t.insert(1, "fold", fold)
        tables.append(t)
        if fold == config.MAIN_FOLD:
            main_scored = scored
    table = pd.concat(tables, ignore_index=True)
 
    summary = (table.groupby(["model", "fold"])[["MAE", "RMSE", "CRPS", "coverage_90"]]
                    .mean().reset_index())
    naive = summary[summary["model"] == "naive"].set_index("fold")
    for col in ["MAE", "CRPS"]:
        summary[f"{col}_vs_naive_%"] = 100 * (summary[col] / summary["fold"].map(naive[col]) - 1)
 
    out = ROOT / "results"
    table.round(4).to_csv(out / "metrics.csv", index=False)
    summary.round(4).to_csv(out / "metrics_summary.csv", index=False)
    FIGURES.mkdir(parents=True, exist_ok=True)
    plot_error_by_horizon(table, models)
    plot_forecast_vs_actual(main_scored, actual, models)
 
    pd.set_option("display.width", 140)
    print(summary.sort_values(["fold", "CRPS"]).round(3).to_string(index=False))
    print("\nSaved results/metrics.csv, results/metrics_summary.csv, and 2 figures.")
 
 
if __name__ == "__main__":
    main()