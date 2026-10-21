"""Descriptive national wastewater/flu-A ILI+ comparison, not a forecast test.

Run: python -m src.explore_wastewater_lead
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.audit_threshold import mmwr_week_start

ROOT = Path(__file__).resolve().parents[1]
LAGS = range(-4, 5)


def lag_correlations(frame, difference=False):
    """Positive lag compares wastewater(t) with ILI+(t+lag).

    Input is a regular Sunday calendar for one season. All lags use the same
    valid anchor dates, so missing observations/edges cannot favor one lag.
    """
    values = frame[['wastewater', 'ili_plus_a']]
    if difference:
        values = values.diff()
    targets = pd.DataFrame({lag: values.ili_plus_a.shift(-lag) for lag in LAGS})
    valid = values.wastewater.notna() & targets.notna().all(axis=1)
    x = values.loc[valid, 'wastewater']
    return [(lag, x.corr(targets.loc[valid, lag]), int(valid.sum())) for lag in LAGS]


def run():
    data = ROOT / 'data/processed'
    ww = pd.read_csv(data / 'nwss_flu_a_weekly_filtered.csv', parse_dates=['week_start']).set_index('week_start')
    ili = pd.read_csv(data / 'ili_plus_a_weekly.csv', parse_dates=['week_start'])
    ili = ili.loc[ili.region.eq('nat')].set_index('week_start')
    joined = pd.concat([ww.median_site_z.rename('wastewater'), ili.ili_plus_a], axis=1, sort=True).sort_index()
    joined = joined.reindex(pd.date_range(joined.index.min(), joined.index.max(), freq='W-SUN'))
    seasons, excluded = {}, []
    for year in range(ww.index.min().year, ili.index.max().year + 1):
        start, end = pd.Timestamp(mmwr_week_start(year*100+40)), pd.Timestamp(mmwr_week_start((year+1)*100+20))
        calendar = pd.date_range(start, end, freq='W-SUN')
        frame = joined.reindex(calendar)
        if frame.notna().all(axis=1).all():
            seasons[f'{year}–{str(year+1)[-2:]}'] = frame
        else:
            excluded.append(f'{year}–{str(year+1)[-2:]} ({int(frame.notna().all(axis=1).sum())}/{len(frame)} paired weeks)')
    rows = []
    for season, frame in seasons.items():
        for difference in [False, True]:
            for lag, corr, n in lag_correlations(frame, difference):
                rows.append(dict(season=season, comparison='weekly_change' if difference else 'level',
                                 lag_weeks=lag, pearson_r=corr, paired_weeks=n))
    result = pd.DataFrame(rows)
    out = ROOT / 'results'
    (out/'figures').mkdir(parents=True, exist_ok=True)
    result.to_csv(out/'wastewater_lag_correlations.csv', index=False)
    fig, axes = plt.subplots(len(seasons), 1, figsize=(10, 2.5*len(seasons)), squeeze=False)
    for ax, (season, frame) in zip(axes[:, 0], seasons.items()):
        scaled = (frame-frame.mean())/frame.std()
        ax.plot(frame.index, scaled.wastewater, label='Wastewater influenza A', color='#137d8b')
        ax.plot(frame.index, scaled.ili_plus_a, label='Influenza-A ILI+', color='#d06b32')
        ax.set_title(season, loc='left'); ax.set_ylabel('Within-season z-score'); ax.grid(alpha=.2)
    axes[0, 0].legend(loc='upper right', fontsize=8)
    fig.suptitle('National influenza-A signals: seasonal timing', fontsize=14)
    fig.tight_layout(rect=(0, .03, 1, .97))
    fig.text(.02, .01, 'Each signal standardized separately for visual comparison; observed dates, not publication dates.', fontsize=9)
    fig.savefig(out/'figures/06_wastewater_overlay.png', dpi=160); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, mode, title in zip(axes, ['level', 'weekly_change'], ['Levels', 'Week-to-week changes']):
        for season, group in result[result.comparison.eq(mode)].groupby('season'):
            ax.plot(group.lag_weeks, group.pearson_r, marker='o', label=season)
        ax.axvline(0, color='gray', linestyle='--', linewidth=1)
        ax.set_title(title); ax.set_xlabel('Lag (weeks): positive = wastewater earlier')
        ax.set_xticks(list(LAGS)); ax.set_ylim(-1, 1); ax.grid(alpha=.2)
    axes[0].set_ylabel('Pearson correlation'); axes[1].legend(fontsize=8)
    fig.suptitle('Exploratory lag comparison (same anchor weeks at every lag)')
    fig.tight_layout(); fig.savefig(out/'figures/07_wastewater_lags.png', dpi=160); plt.close(fig)
    print('Excluded incomplete seasons:', '; '.join(excluded))
    for (season, mode), group in result.groupby(['season','comparison'], sort=False):
        best = group.loc[group.pearson_r.idxmax()]
        zero = group.loc[group.lag_weeks.eq(0), 'pearson_r'].iloc[0]
        print(f'{season} {mode}: best lag={best.lag_weeks:+d}, r={best.pearson_r:.3f}, same-week r={zero:.3f}, n={best.paired_weeks}')
    return result


if __name__ == '__main__':
    run()
