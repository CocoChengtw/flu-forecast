"""Descriptive national ILI+ analysis using shared settings. Run python -m src.eda."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from src import config
from src.audit_threshold import main as audit, mmwr_week_start

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / 'results/figures'


def run():
    audit()
    FIGURES.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(ROOT / 'data/processed/ili_plus_weekly.csv', parse_dates=['week_start'])
    df = df[df.region.eq(config.REGION)].sort_values('week_start').copy()
    df['year'] = df.epiweek // 100
    df['week'] = df.epiweek % 100
    df['season_year'] = df.year - df.week.lt(40).astype(int)
    df['season'] = df.season_year.astype(str) + '-' + (df.season_year + 1).astype(str)
    df['season_position'] = df.apply(lambda r: (r.week_start.date() - mmwr_week_start(int(r.season_year)*100+40)).days // 7, axis=1)
    df['covid_window'] = df.week_start.between(config.COVID_START, config.COVID_END)
    train = df[df.week_start.lt(pd.Timestamp(config.TEST_START))].copy()
    active = train[train.week.ge(40) | train.week.le(20)]
    records = []
    for season,g in active.groupby('season',sort=True):
        g = g.sort_values('week_start')
        if g.week.iloc[0] != 40 or g.week.iloc[-1] != 20:
            continue
        n = config.ONSET_CONSECUTIVE_WEEKS
        starts = [i for i in range(len(g)-n+1) if (g.ili_plus.iloc[i:i+n] > config.THRESHOLD).all()]
        onset = g.iloc[starts[0]] if starts else None
        peak = g.loc[g.ili_plus.idxmax()]
        records.append(dict(season=season, season_year=int(g.season_year.iloc[0]),
            onset_week_start=None if onset is None else onset.week_start.strftime('%Y-%m-%d'),
            onset_mmwr_week=None if onset is None else int(onset.week),
            onset_position=None if onset is None else int(onset.season_position),
            onset_confirmation_week=None if onset is None else g.iloc[starts[0]+n-1].week_start.strftime('%Y-%m-%d'),
            above_threshold_at_window_start=bool(g.ili_plus.iloc[0] > config.THRESHOLD),
            peak_week_start=peak.week_start.strftime('%Y-%m-%d'), peak_mmwr_week=int(peak.week),
            peak_position=int(peak.season_position),peak_value=float(peak.ili_plus),
            covid_overlap=bool(g.covid_window.any()), weeks_above_threshold=int((g.ili_plus > config.THRESHOLD).sum())))
    seasons = pd.DataFrame(records)
    seasons.to_csv(ROOT / 'results/historical_seasons.csv',index=False)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'white'})
    def save(fig,name):
        fig.savefig(FIGURES/name,dpi=180,bbox_inches='tight')
        plt.close(fig)
    blue, orange = '#176B87','#C85C24'
    fig,ax=plt.subplots(figsize=(12,4.8))
    ax.plot(df.week_start,df.ili_plus,color=blue,lw=1.5,label='Observed ILI+ (no imputation)')
    ax.axhline(config.THRESHOLD,color=orange,ls='--',label=f'Research threshold = {config.THRESHOLD:.5f}')
    ax.axvspan(pd.Timestamp(config.COVID_START),pd.Timestamp(config.COVID_END),color='#C9CED4',alpha=.5,label='Configured COVID window')
    ax.axvspan(pd.Timestamp(config.TEST_START),pd.Timestamp(config.TEST_END),color='#B5DCC8',alpha=.45,label='Test forecast origins (not used to select threshold)')
    ax.set(title='National ILI+: observed history and the fixed threshold',ylabel='ILI+ (weighted ILI% × flu-positive fraction)',xlabel='Week starting Sunday')
    ax.legend(loc='upper left',fontsize=8)
    ax.grid(axis='y',alpha=.2)
    fig.tight_layout();save(fig,'01_ili_plus_history.png')
    fig,ax=plt.subplots(figsize=(11,5.2))
    colors=plt.cm.tab10(np.linspace(0,1,len(seasons)))
    for color,(_,s) in zip(colors,seasons.iterrows()):
        g=train[train.season.eq(s.season)]
        ax.plot(g.season_position,g.ili_plus,label=s.season,color=color,lw=1.5,alpha=.85,ls=':' if s.season=='2020-2021' else '-')
    ax.axhline(config.THRESHOLD,color=orange,ls='--',lw=1)
    ax.set(title='Seasonal patterns differ in timing and height',xlabel='Weeks since MMWR week 40 (actual elapsed weeks)',ylabel='ILI+ (percentage-point scale)',xlim=(0,52))
    ax.legend(title='Pre-test seasons',bbox_to_anchor=(1.01,1),loc='upper left',fontsize=8)
    ax.grid(alpha=.15);fig.tight_layout();save(fig,'02_seasonal_overlay.png')
    fig,axes=plt.subplots(3,3,figsize=(13,9),sharex=True,sharey=True)
    for ax,(_,s) in zip(axes.flat,seasons.iterrows()):
        g=train[train.season.eq(s.season)].iloc[:16]
        ax.plot(g.season_position,g.ili_plus,color=blue,lw=1.8)
        ax.axhline(config.THRESHOLD,color=orange,ls='--')
        if pd.notna(s.onset_position):
            ax.axvline(s.onset_position,color='#7C3A88',ls=':',lw=1.4)
        label='No onset' if pd.isna(s.onset_week_start) else str(s.onset_week_start)
        if s.above_threshold_at_window_start: label += ' *'
        ax.set_title(f'{s.season}\n{label}',fontsize=10)
        ax.set_ylim(0,.15);ax.set_xlim(0,15);ax.grid(alpha=.18)
    for ax in axes[-1]:ax.set_xlabel('Weeks since week 40')
    for ax in axes[:,0]:ax.set_ylabel('ILI+ (zoom: 0–0.15)')
    fig.suptitle('Threshold check: early-season detail, pre-test seasons only',fontsize=15,y=1.01)
    fig.text(.5,-.01,'Orange: fixed threshold. Purple: first of two consecutive weeks above threshold.\n* Already above threshold at week 40; earlier onset is possible. Higher values extend beyond the zoom.',ha='center',fontsize=9)
    fig.tight_layout();save(fig,'03_threshold_onset_check.png')
    fig,ax=plt.subplots(figsize=(10,5))
    for i,(_,s) in enumerate(seasons.iterrows()):
        ax.scatter(s.peak_position,i,color='#969BA1' if s.covid_overlap else blue,s=70)
        ax.annotate(s.peak_week_start,(s.peak_position,i),xytext=(8,0),textcoords='offset points',va='center',fontsize=9)
    ax.set_yticks(range(len(seasons)),seasons.season)
    ax.invert_yaxis();ax.set_xlim(-1,35)
    ax.set(title='Observed peak timing within MMWR weeks 40–20',xlabel='Weeks since MMWR week 40',ylabel='Pre-test season')
    ax.grid(axis='x',alpha=.2)
    fig.text(.12,.025,'Gray: seasons overlapping the configured COVID window. A mathematical maximum does not establish a meaningful outbreak.\nPeaks are restricted to weeks 40–20; late spring/summer peaks outside this window are excluded.',fontsize=9)
    fig.tight_layout(rect=(0,.12,1,1));save(fig,'04_peak_timing.png')
    october=int(seasons.onset_week_start.fillna('').str.contains('-10-').sum())
    summary={'threshold':config.THRESHOLD,'pretest_seasons':len(seasons),'october_onsets':october,
             'no_onset_seasons':seasons.loc[seasons.onset_week_start.isna(),'season'].tolist(),
             'above_at_start':seasons.loc[seasons.above_threshold_at_window_start,'season'].tolist(),
             'threshold_changed':False,
             'interpretation':'Low-activity departure threshold; not validated as a hospital surge trigger. No tuning to test results.',
             'caveats':['Same fixed pre-test threshold is applied retrospectively to earlier seasons for description only.',
                        'Peak window is weeks 40-20, while overlays show the full surveillance year.',
                        'The first onset week is only confirmed after the second consecutive exceedance.',
                        'Revised historical data are not real-time data vintages.']}
    (ROOT/'results/eda_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return df,seasons,summary

if __name__=='__main__':
    run()
