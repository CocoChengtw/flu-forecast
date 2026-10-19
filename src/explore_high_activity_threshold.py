"""Descriptive pre-test threshold exploration; never changes shared config.

Run from the repository root: python -m src.explore_high_activity_threshold
"""

from pathlib import Path

import pandas as pd

from src.config import COVID_END, COVID_START, REGION, TEST_START

ROOT = Path(__file__).resolve().parents[1]


def run():
    data = pd.read_csv(ROOT / "data/processed/ili_plus_weekly.csv")
    data = data.loc[(data.region == REGION) & (data.week_start < TEST_START)].copy()
    data["week"] = data.epiweek % 100
    data["season"] = data.epiweek // 100 - (data.week < 40).astype(int)
    data["covid"] = data.week_start.between(COVID_START, COVID_END)
    active = data.loc[(data.week >= 40) | (data.week <= 20)].copy()
    assert not active.week_start.duplicated().any()
    assert active.ili_plus.notna().all()
    assert (active.week_start < TEST_START).all()
    # Require every MMWR week 40–52 and 1–20, plus week 53 when present.
    required = set(range(40, 53)) | set(range(1, 21))
    complete = [s for s, g in active.groupby("season")
                if required.issubset(set(g.week)) and not g.covid.any()]
    seasons = sorted(complete)[-3:]
    assert len(seasons) == 3
    recent = active.loc[active.season.isin(seasons)]
    broad = active.loc[~active.covid]
    rows = []
    for name, frame in [("recent_three_seasons", recent), ("all_pretest_non_covid", broad)]:
        for q in (0.70, 0.75, 0.80):
            threshold = frame.ili_plus.quantile(q, interpolation="linear")
            rows.append(dict(reference=name, n=len(frame), percentile=q,
                             threshold=threshold,
                             weeks_above=int((frame.ili_plus > threshold).sum())))
    candidates = pd.DataFrame(rows)
    diagnostics = []
    for label, threshold in [
        *[(f"p{int(q * 100)}", recent.ili_plus.quantile(q)) for q in (0.70, 0.75, 0.80)],
        ("comparison_0.5", 0.5),
    ]:
        for season, frame in recent.groupby("season"):
            frame = frame.sort_values("week_start")
            above = frame.ili_plus > threshold
            first = frame.loc[above, "week_start"]
            peak_date = frame.loc[frame.ili_plus.idxmax(), "week_start"]
            diagnostics.append(dict(
                candidate=label, threshold=threshold, season=f"{season}–{str(season+1)[-2:]}",
                n=len(frame), weeks_above=int(above.sum()),
                first_above=first.iloc[0] if len(first) else "none",
                peak_week=peak_date,
                weeks_first_above_to_peak=(pd.Timestamp(peak_date)-pd.Timestamp(first.iloc[0])).days//7
                if len(first) else None,
                already_above_at_window_start=bool(above.iloc[0]),
            ))
    diagnostics = pd.DataFrame(diagnostics)
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    candidates.to_csv(out / "high_activity_candidates.csv", index=False)
    diagnostics.to_csv(out / "high_activity_season_diagnostics.csv", index=False)
    print("Reference seasons:", seasons)
    print(candidates.to_string(index=False))
    print(diagnostics.to_string(index=False))
    return candidates, diagnostics


if __name__ == "__main__":
    run()
