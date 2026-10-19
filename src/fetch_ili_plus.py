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
from pathlib import Path

import pandas as pd
import requests

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


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)

    ili = fetch("fluview", ["wili"])
    lab = fetch("fluview_clinical", ["percent_positive"])

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
    print(f"Saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
