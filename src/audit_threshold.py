"""Validate the shared data and reproduce the fixed pre-test threshold.

Run python -m src.audit_threshold.
"""
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from src import config


def mmwr_week_start(epiweek):
    """Independent Sunday-based check: MMWR week 1 contains January 4."""
    year, week = divmod(epiweek, 100)
    jan4 = date(year, 1, 4)
    return jan4 - timedelta(days=(jan4.weekday()+1) % 7) + timedelta(weeks=week-1)


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / 'data/processed/ili_plus_weekly.csv'
    rows = [r for r in csv.DictReader(source.open()) if r['region'] == config.REGION]
    rows.sort(key=lambda r: int(r['epiweek']))
    assert rows, 'No rows for configured region'
    assert all(n == 1 for n in Counter(r['epiweek'] for r in rows).values()), 'Duplicate weeks'
    for r in rows:
        r['date'] = date.fromisoformat(r['week_start'])
        r['value'] = float(r['ili_plus'])
        assert r['date'] == mmwr_week_start(int(r['epiweek']))
        assert all(math.isfinite(float(r[k])) for k in ('wili', 'pct_positive', 'ili_plus'))
        assert 0 <= float(r['wili']) <= 100 and 0 <= float(r['pct_positive']) <= 100
        assert math.isclose(r['value'], float(r['wili']) * float(r['pct_positive']) / 100, abs_tol=1e-12)
    assert all((b['date']-a['date']).days == 7 for a,b in zip(rows, rows[1:])), 'Missing weeks'
    cutoff = date.fromisoformat(config.TEST_START)
    off = defaultdict(list)
    for r in rows:
        y,w = divmod(int(r['epiweek']),100)
        if r['date'] < cutoff and w in config.OFFSEASON_WEEKS:
            off[y].append(r)
    eligible = [y for y,g in off.items() if len(g) == len(config.OFFSEASON_WEEKS)
                and not any(date.fromisoformat(config.COVID_START) <= r['date'] <= date.fromisoformat(config.COVID_END) for r in g)]
    years = sorted(eligible)[-config.THRESHOLD_N_SEASONS:]
    assert len(years) == config.THRESHOLD_N_SEASONS
    values = [r['value'] for y in years for r in off[y]]
    mean, sd = statistics.mean(values), statistics.stdev(values)
    threshold = mean + config.THRESHOLD_N_SD * sd
    assert math.isclose(threshold, config.THRESHOLD, abs_tol=1e-12), 'Config threshold differs; review before updating'
    seasons = defaultdict(list)
    for r in rows:
        y,w = divmod(int(r['epiweek']),100)
        if w >= 40 or w <= 20:
            seasons[y if w >= 40 else y-1].append(r)
    events = []
    for y,g in sorted(seasons.items()):
        n = config.ONSET_CONSECUTIVE_WEEKS
        onset = next((g[i]['week_start'] for i in range(len(g)-n+1)
                      if all(x['value'] > threshold for x in g[i:i+n])), None)
        peak = max(g, key=lambda r:r['value'])
        complete = int(g[0]['epiweek']) % 100 == 40 and int(g[-1]['epiweek']) % 100 == 20
        events.append(dict(season=f'{y}-{y+1}', complete=complete, onset=onset,
                           above_at_season_start=g[0]['value'] > threshold,
                           observed_peak_week=peak['week_start'], observed_peak_value=peak['value']))
    target_end = date.fromisoformat(config.TEST_END) + timedelta(weeks=max(config.HORIZONS))
    assert rows[-1]['date'] >= target_end, 'Test targets unavailable'
    result = dict(region=config.REGION, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  first_week=rows[0]['week_start'], last_week=rows[-1]['week_start'], observations=len(rows),
                  duplicate_weeks=0, missing_weeks=0, formula_verified=True,
                  configured_train_start=config.TRAIN_START, actual_train_start=rows[0]['week_start'],
                  required_last_test_target=str(target_end), threshold=threshold,
                  threshold_offseason_years=years, threshold_n=len(values), mean=mean, sample_sd=sd,
                  method='Pooled raw weeks 21-39, latest 3 complete non-COVID offseasons strictly before TEST_START; sample SD (ddof=1).',
                  caveats=['Research threshold, not official CDC ILI+ baseline.',
                           'Fixed threshold applied to older seasons is descriptive, not historical real-time calibration.',
                           'Some historical onsets are in October; do not tune to force November-December.',
                           'Season-start exceedance can be left-censored; incomplete-season peaks are provisional.',
                           'Downloaded historical values may be revised; this is not an as-of-vintage audit.'],
                  historical_events=events)
    out=root/'results/audit_threshold.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
