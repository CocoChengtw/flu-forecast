"""
Download state-level ILI+ for the dashboard map.

Same measure as the national series: weighted ILI% (ILINet) x clinical-lab
% flu positive / 100, from the Delphi Epidata API. Recent weeks only, since
the map shows where flu is now. Some states don't report to ILINet (e.g.
Florida), so they show as "no data".

    python app/fetch_states.py
"""

import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluate import to_epiweek                                # noqa: E402

OUT = ROOT / "data" / "processed" / "ili_plus_state_weekly.csv"
API = "https://api.delphi.cmu.edu/epidata"
WEEKS_BACK = 12
STATES = ("al ak az ar ca co ct de dc fl ga hi id il in ia ks ky la me md ma mi mn ms mo mt ne "
          "nv nh nj nm ny nc nd oh ok or pa ri sc sd tn tx ut vt va wa wv wi wy").split()


def fetch(endpoint: str, fields: list[str], weeks: str) -> pd.DataFrame:
    r = requests.get(f"{API}/{endpoint}/", params={"regions": ",".join(STATES), "epiweeks": weeks}, timeout=60)
    r.raise_for_status()
    body = r.json()
    if body.get("result") != 1:
        raise RuntimeError(f"{endpoint}: {body.get('message')}")
    return pd.DataFrame(body["epidata"])[["region", "epiweek", *fields]]


def main() -> None:
    today = pd.Timestamp.today().normalize()
    weeks = f"{to_epiweek(today - pd.Timedelta(weeks=WEEKS_BACK + 2))}-{to_epiweek(today)}"
    ili = fetch("fluview", ["wili"], weeks)
    lab = fetch("fluview_clinical", ["percent_positive"], weeks)
    df = ili.merge(lab, on=["region", "epiweek"], how="inner").dropna()
    df["ili_plus"] = df["wili"] * df["percent_positive"] / 100
    df["state"] = df["region"].str.upper()
    df = df[["state", "epiweek", "wili", "percent_positive", "ili_plus"]].sort_values(["state", "epiweek"])
    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT.relative_to(ROOT)}: {df['state'].nunique()} states, "
          f"weeks {df['epiweek'].min()}-{df['epiweek'].max()}")


if __name__ == "__main__":
    main()
