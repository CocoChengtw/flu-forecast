"""
Clean raw downloads into weekly series.

Inputs  (data/raw/):
    flunet_us.csv    OWID Flu Explorer download (all countries, ISO weeks)
    nwss_flu_a.csv   CDC NWSS Influenza A wastewater samples (one row per sample, site level)

Outputs (data/processed/):
    flu_positivity_us_weekly.csv   week_start, pct_positive
    nwss_flu_a_weekly.csv          week_start, n_sites, median_log10_conc, median_site_z
    nwss_flu_a_state_weekly.csv    state, week_start, n_sites, median_log10_conc, median_site_z
                                   (state = 2-letter uppercase code, e.g. CA, for maps)

Run from the repo root:
    python src/clean.py
"""

from datetime import date
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

MIN_SITE_WEEKS = 20  # sites with less history are too noisy to standardize
SITE_COUNT_WINDOW = 8
SITE_COUNT_MIN_HISTORY = 4
MIN_SITE_COUNT_RATIO = 0.5


def filter_reporting_coverage(df: pd.DataFrame, groups=()):
    """Keep weeks with >=50% of the prior 8-week median site count.

    Use each geography's own history, with at least four prior reporting weeks.
    Calendar gaps contribute zero sites. Return retained rows and an audit table.
    This is a project completeness screen, not a CDC quality standard.
    """
    pieces = []
    grouped = df.groupby(list(groups), dropna=False) if groups else [(None, df)]
    for _, frame in grouped:
        frame = frame.copy()
        frame['week_start'] = pd.to_datetime(frame['week_start'])
        frame = frame.sort_values('week_start')
        if frame.week_start.duplicated().any():
            raise ValueError('Duplicate geography/week in wastewater data')
        counts = frame.set_index('week_start').n_sites
        calendar = pd.date_range(counts.index.min(), counts.index.max(), freq='W-SUN')
        counts = counts.reindex(calendar, fill_value=0)
        typical = counts.shift(1).rolling(SITE_COUNT_WINDOW, min_periods=SITE_COUNT_MIN_HISTORY).median()
        reported = counts.gt(0).astype(int).shift(1).rolling(SITE_COUNT_WINDOW, min_periods=SITE_COUNT_MIN_HISTORY).sum()
        typical = typical.where(reported >= SITE_COUNT_MIN_HISTORY)
        frame['typical_n_sites'] = frame.week_start.map(typical)
        frame['site_count_ratio'] = frame.n_sites / frame.typical_n_sites.where(frame.typical_n_sites > 0)
        frame['coverage_status'] = np.where(frame.site_count_ratio.isna(), 'insufficient_history',
            np.where(frame.site_count_ratio >= MIN_SITE_COUNT_RATIO, 'pass', 'low_site_count'))
        pieces.append(frame)
    audit = pd.concat(pieces, ignore_index=True)
    return audit.loc[audit.coverage_status.eq('pass')].copy(), audit


def save_coverage_outputs(national, state):
    """Preserve original aggregates; charts/maps should use *_filtered.csv."""
    for name, frame, groups in [('nwss_flu_a_weekly', national, ()),
                                ('nwss_flu_a_state_weekly', state, ('state',))]:
        filtered, audit = filter_reporting_coverage(frame, groups)
        filtered.to_csv(PROCESSED / f'{name}_filtered.csv', index=False)
        audit.to_csv(PROCESSED / f'{name}_coverage.csv', index=False)
        print(f'[{name}] retained {len(filtered)}/{len(audit)} rows; '
              f'{audit.coverage_status.value_counts().to_dict()}')


def iso_week_to_monday(week_str: str) -> pd.Timestamp:
    """'2016-W01' -> Monday of that ISO week."""
    year, week = week_str.split("-W")
    return pd.Timestamp(date.fromisocalendar(int(year), int(week), 1))


def report_gaps(series_dates: pd.Series, name: str, freq: str = "W-MON") -> None:
    full = pd.date_range(series_dates.min(), series_dates.max(), freq=freq)
    missing = full.difference(series_dates)
    print(f"[{name}] {series_dates.min().date()} to {series_dates.max().date()}, "
          f"{len(series_dates)} weeks, {len(missing)} missing weeks")
    if 0 < len(missing) <= 10:
        print(f"[{name}] missing: {[d.date() for d in missing]}")


# ---------------------------------------------------------------------------
# 1. FluNet / OWID: share of positive influenza tests, United States
# ---------------------------------------------------------------------------
def clean_flunet() -> pd.DataFrame:
    df = pd.read_csv(RAW / "flunet_us.csv")
    value_col = [c for c in df.columns if c.startswith("Share of positive tests")][0]

    us = df.loc[df["Entity"] == "United States", ["Week", value_col]].copy()
    us["week_start"] = us["Week"].map(iso_week_to_monday)
    out = (us.rename(columns={value_col: "pct_positive"})
             [["week_start", "pct_positive"]]
             .dropna()
             .sort_values("week_start")
             .reset_index(drop=True))

    report_gaps(out["week_start"], "flunet")
    return out


# ---------------------------------------------------------------------------
# 2. NWSS: Influenza A wastewater concentration, aggregated to weekly series
# ---------------------------------------------------------------------------
def nwss_site_week() -> pd.DataFrame:
    """One row per site per week, with log10 concentration and a site-level z-score."""
    usecols = ["site", "state_territory", "sample_collect_date",
               "pcr_target", "pcr_target_avg_conc_lin"]
    df = pd.read_csv(RAW / "nwss_flu_a.csv", usecols=usecols, low_memory=False)

    df = df[df["pcr_target"] == "fluav"].copy()
    df["sample_collect_date"] = pd.to_datetime(df["sample_collect_date"], errors="coerce")
    df = df.dropna(subset=["sample_collect_date", "pcr_target_avg_conc_lin"])
    df["state"] = df["state_territory"].astype(str).str.strip().str.upper()

    # Sunday of the sample's week, to match the MMWR weeks used by ILINet / ILI+
    d = df["sample_collect_date"]
    df["week_start"] = (d - pd.to_timedelta((d.dt.weekday + 1) % 7, unit="D")).dt.normalize()

    # Concentrations are log-normal and span orders of magnitude, so work on log10
    df["log10_conc"] = np.log10(df["pcr_target_avg_conc_lin"].clip(lower=0) + 1)

    site_week = (df.groupby(["site", "state", "week_start"], as_index=False)["log10_conc"]
                   .mean())

    # Labs and methods differ across sites, so standardize each site against its own history
    counts = site_week.groupby("site")["week_start"].transform("count")
    site_week = site_week[counts >= MIN_SITE_WEEKS].copy()
    grp = site_week.groupby("site")["log10_conc"]
    site_week["site_z"] = (site_week["log10_conc"] - grp.transform("mean")) / grp.transform("std")
    return site_week


def aggregate_sites(site_week: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    return (site_week.groupby(by)
                     .agg(n_sites=("site", "nunique"),
                          median_log10_conc=("log10_conc", "median"),
                          median_site_z=("site_z", "median"))
                     .reset_index()
                     .sort_values(by))


def clean_nwss() -> tuple[pd.DataFrame, pd.DataFrame]:
    site_week = nwss_site_week()

    national = aggregate_sites(site_week, ["week_start"])
    report_gaps(national["week_start"], "nwss", freq="W-SUN")

    state = aggregate_sites(site_week, ["state", "week_start"])
    latest = state["week_start"].max()
    n_latest = state.loc[state["week_start"] == latest, "state"].nunique()
    print(f"[nwss-state] {state['state'].nunique()} states/territories, "
          f"{n_latest} reporting in the latest week ({latest.date()})")
    return national, state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coverage-only', action='store_true',
                        help='Apply coverage screen to existing aggregates without raw downloads')
    args = parser.parse_args()
    PROCESSED.mkdir(parents=True, exist_ok=True)

    if args.coverage_only:
        save_coverage_outputs(pd.read_csv(PROCESSED / 'nwss_flu_a_weekly.csv'),
                              pd.read_csv(PROCESSED / 'nwss_flu_a_state_weekly.csv'))
        return

    flu = clean_flunet()
    flu.to_csv(PROCESSED / "flu_positivity_us_weekly.csv", index=False)

    ww_national, ww_state = clean_nwss()
    ww_national.to_csv(PROCESSED / "nwss_flu_a_weekly.csv", index=False)
    ww_state.to_csv(PROCESSED / "nwss_flu_a_state_weekly.csv", index=False)
    save_coverage_outputs(ww_national, ww_state)

    print("Saved to data/processed/")


if __name__ == "__main__":
    main()
