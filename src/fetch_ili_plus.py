"""
Fetch weekly ILINet and clinical-lab flu positivity from the Delphi Epidata API
(Carnegie Mellon) and compute ILI+.

    ILI+ = weighted ILI% x (flu test positivity % / 100)

Regions: "nat" (United States) and "hhs9" (HHS Region 9, includes California).
No API key is needed.

Output (data/processed/):
    ili_plus_weekly.csv
        region, epiweek, week_start (Sunday of the MMWR week),
        wili, pct_positive, ili_plus

Run from the repo root:
    python src/fetch_ili_plus.py
"""

from datetime import date, timedelta
import argparse
import json
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

API = "https://api.delphi.cmu.edu/epidata"
REGIONS = ["nat", "hhs9"]
START_EPIWEEK = 201540   # clinical-lab positivity starts in the 2015-16 season
END_EPIWEEK = 203052     # far future; the API returns what exists


def mmwr_week_start(epiweek: int) -> date:
    """Sunday that starts MMWR week `epiweek` (e.g. 202552)."""
    year, week = divmod(epiweek, 100)
    jan4 = date(year, 1, 4)
    week1_start = jan4 - timedelta(days=(jan4.weekday() + 1) % 7)
    return week1_start + timedelta(weeks=week - 1)


def fetch(endpoint: str, fields: list[str]) -> pd.DataFrame:
    import requests
    params = {
        "regions": ",".join(REGIONS),
        "epiweeks": f"{START_EPIWEEK}-{END_EPIWEEK}",
    }
    resp = requests.get(f"{API}/{endpoint}/", params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("result") != 1:
        raise RuntimeError(f"{endpoint}: {payload.get('message')}")
    df = pd.DataFrame(payload["epidata"])
    return df[["region", "epiweek"] + fields]


def build_flu_a(existing: pd.DataFrame, lab: pd.DataFrame) -> pd.DataFrame:
    """Add type-A positivity without silently mixing revised total-positivity data."""
    merged = existing.merge(lab[['region', 'epiweek', 'percent_positive', 'percent_a']],
                            on=['region', 'epiweek'], how='left', validate='one_to_one')
    if merged[['percent_positive', 'percent_a']].isna().any().any():
        raise ValueError('Missing clinical-lab values for existing ILI+ weeks')
    if not np.allclose(merged.pct_positive, merged.percent_positive, rtol=0, atol=1e-5):
        raise ValueError('Clinical positivity has been revised; review data vintages before refreshing ILI+')
    if not (merged.percent_a.between(0, 100) &
            (merged.percent_a <= merged.percent_positive + 1e-5)).all():
        raise ValueError('Invalid influenza-A positivity')
    merged['pct_positive_a'] = merged.percent_a
    merged['ili_plus_a'] = merged.wili * merged.pct_positive_a / 100
    return merged[['region', 'epiweek', 'week_start', 'wili', 'pct_positive_a', 'ili_plus_a']]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--flu-a-only', action='store_true',
                        help='Add flu-A output using existing ILI+, leaving the shared target untouched')
    parser.add_argument('--clinical-json', type=Path,
                        help='Use a saved Delphi clinical response instead of requesting it again')
    args = parser.parse_args()
    PROCESSED.mkdir(parents=True, exist_ok=True)

    if args.clinical_json:
        payload = json.loads(args.clinical_json.read_text())
        if payload.get('result') != 1:
            raise ValueError('Unsuccessful saved Delphi response')
        lab = pd.DataFrame(payload['epidata'])
    else:
        lab = fetch('fluview_clinical', ['percent_positive', 'percent_a'])

    if args.flu_a_only:
        existing = pd.read_csv(PROCESSED / 'ili_plus_weekly.csv')
        flu_a = build_flu_a(existing, lab)
        flu_a.to_csv(PROCESSED / 'ili_plus_a_weekly.csv', index=False)
        print(f'Saved {len(flu_a)} flu-A rows; shared ILI+ unchanged')
        return

    ili = fetch("fluview", ["wili"])

    df = (ili.merge(lab, on=["region", "epiweek"], how="inner")
             .rename(columns={"percent_positive": "pct_positive"}))
    df["ili_plus"] = df["wili"] * df["pct_positive"] / 100
    df["week_start"] = df["epiweek"].map(mmwr_week_start)
    df = (df[["region", "epiweek", "week_start", "wili", "pct_positive", "ili_plus"]]
            .sort_values(["region", "epiweek"])
            .reset_index(drop=True))

    for region, g in df.groupby("region"):
        print(f"[{region}] {g['epiweek'].min()} to {g['epiweek'].max()}, "
              f"{len(g)} weeks, peak ILI+ {g['ili_plus'].max():.2f}")

    out = PROCESSED / "ili_plus_weekly.csv"
    df.to_csv(out, index=False)
    build_flu_a(df, lab).to_csv(PROCESSED / 'ili_plus_a_weekly.csv', index=False)
    print(f"Saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
