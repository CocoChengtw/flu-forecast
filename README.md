# Seeing the Surge Coming

**AI vs. Statistical Forecasts of Flu Season, Deployed as a Live Dashboard**

Group final project for Time Series Analysis and Forecasting (UCLA Anderson, Dr. William Yu).

## Goal

Give a local health department or hospital operations team early warning of the flu season, so they can decide when to add staff and beds, push vaccination messaging, and alert providers.

We forecast weekly U.S. **ILI+** 1–4 weeks ahead and compare classical statistical models with an AI forecasting model. The best results are shown in a Streamlit dashboard with an AI assistant that explains the forecast in plain language.

### Forecast target: ILI+

**ILI+ = weighted ILI% × (% of flu tests positive / 100)**

- **ILI%** (influenza-like illness): the share of outpatient visits for fever plus cough or sore throat, from CDC's ILINet network. It measures how many people are sick, but it also counts COVID, RSV and colds.
- **% positive**: the share of clinical-lab flu tests that are positive. It is flu-specific, but it says nothing about how many people are sick.

Multiplying them estimates the share of outpatient visits that are actually flu. We switched from test positivity alone because positivity depends on who gets tested and cannot tell a mild season from a severe one. See `notes/analysis_log.md` for the full reasoning.

### Outputs

The forecasts are framed around timing decisions, not just point estimates:

1. **Threshold probability (priority):** the chance ILI+ goes above the threshold within the next 1–4 weeks.
2. **Onset week:** the first of two consecutive weeks above the threshold.
3. **Peak timing:** the chance the season peaks within the next 4 weeks.

## Data

| File | Source | Notes |
|---|---|---|
| `data/processed/ili_plus_weekly.csv` | CDC FluView (ILINet + clinical labs) via the [Delphi Epidata API](https://cmu-delphi.github.io/delphi-epidata/) | **Main dataset.** Weekly, national (`nat`) and HHS Region 9 (`hhs9`), from the 2016–17 season. Built by `src/fetch_ili_plus.py`. |
| `data/processed/nwss_flu_a_weekly.csv` | CDC NWSS ([dataset](https://catalog.data.gov/dataset/cdc-wastewater-data-for-influenza-a)) | Influenza A wastewater, national weekly summary. Used only for the stretch lead-time analysis. |
| `data/processed/flu_positivity_us_weekly.csv` | WHO FluNet via Our World in Data | Original target (U.S. test positivity, 2009–). Kept for reference, not used by the models. |
| `data/raw/` | | Original downloads. Never edit by hand. The raw wastewater file (141 MB) is not in the repo. |

All weeks follow CDC's **MMWR** week numbering: weeks run Sunday to Saturday, and `week_start` is the Sunday.

To refresh the ILI+ data (no API key needed):

```bash
python src/fetch_ili_plus.py
```

If the API is down, download the same series manually from CDC FluView Interactive.

To rebuild the wastewater files, download the raw CSV from
`https://data.cdc.gov/api/views/ymmh-divb/rows.csv?accessType=DOWNLOAD`,
save it as `data/raw/nwss_flu_a.csv`, then run `python src/clean.py`.

## Methods

All shared settings (dates, horizons, threshold, number of paths, random seed) live in **`src/config.py`**. Import them from there; never hard-code them.

| Decision | Choice |
|---|---|
| Training data | 2016–17 season onward (the first season with clinical-lab positivity in the Delphi data) |
| Test period | 2025–26 season, MMWR weeks 40–20. Every week is a forecast origin, and each model sees only data up to that week. |
| Horizons | 1–4 weeks ahead |
| COVID | 2020–21 (flu nearly absent) is replaced with the same-week mean of other pre-test seasons and flagged `is_imputed`. 2021–22 is kept as observed. |
| Threshold | Off-season (MMWR weeks 21–39) mean + 2 SD over the last 3 non-COVID pre-test seasons, adapted from CDC's ILINet baseline method. A second, higher "high-activity" threshold is under discussion. |
| Uncertainty | Every model produces 500 simulated paths per origin. All probabilities are computed from these paths the same way for every model. |

**Models**

- Classical: seasonal naive (baseline), ETS, ARIMA with Fourier terms, Prophet
- AI: Chronos (a time-series foundation model)
- Optional: a small ChatGPT/Claude comparison on 3–5 origins

**Metrics**

- Point forecasts (path median): MAE, RMSE
- Threshold probabilities: Brier score
- Timing: error in onset week and peak week, in weeks

**Wastewater (stretch goal):** a lead-time analysis of wastewater vs. ILI+ only. The wastewater history (about 3 seasons) is too short to use as a model input.

### Shared forecast output format

Every model saves `results/forecasts/<model>.csv` with these columns:

| Column | Description |
|---|---|
| `model` | e.g. `naive`, `ets`, `chronos` |
| `origin` | forecast week (Sunday start) |
| `horizon` | 1–4 |
| `target_week` | week being forecast |
| `path_id` | simulated path, 0–499 |
| `value` | forecast ILI+ |

Plug a model into the rolling-origin framework in `src/evaluate.py` and it writes this file for you. Run `python -m src.diagnostics <model>` to check a model's intervals before trusting its probabilities.

## Repo structure

```
flu-forecast/
├── data/
│   ├── raw/            original downloads, never edit by hand
│   └── processed/      cleaned weekly series (ILI+, wastewater)
├── src/
│   ├── config.py           shared settings for everyone
│   ├── fetch_ili_plus.py   downloads ILI+ data
│   ├── clean.py            cleans FluNet and wastewater raw files
│   ├── evaluate.py         rolling-origin framework and point metrics
│   └── ...                 models, probabilities, diagnostics
├── notebooks/          exploration notebooks
├── results/
│   ├── forecasts/      one CSV per model, shared format above
│   └── figures/
├── notes/              decision log for the methods and limitations slides
├── app/                Streamlit dashboard
├── forecasting_project_handbook.md   course concepts, from the lecture decks
├── requirements.txt
├── .env.example
└── README.md
```

## First-time setup

Use **Python 3.11** (Prophet is most reliable on 3.11).

```bash
git clone https://github.com/CocoChengtw/flu-forecast.git
cd flu-forecast
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
nbstripout --install
cp .env.example .env
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.

Only the AI assistant and the optional LLM comparison need an API key in `.env`. Everyone else can leave it empty.

## Daily workflow

```bash
git checkout main
git pull
git checkout -b <your-name>/<task>
```

Work, then:

```bash
git add .
git commit -m "Short description of the change"
git push -u origin <your-name>/<task>
```

Then open a Pull Request on GitHub to merge into `main`.

## Team rules

- Name notebooks with your name or role: `notebooks/01_eda_<name>.ipynb`
- Move reusable functions into `src/` so we don't each write our own version
- Take dates, thresholds and settings from `src/config.py`
- Every model uses the shared forecast format and the same origins, horizons and test period, so the comparison is fair
- Never commit `.env` or API keys
- Keep `main` runnable
- Record key decisions and their reasons in `notes/analysis_log.md`
- If you're blocked for more than half a day, post in the group chat right away

## Roles

| Role | Responsibility |
|---|---|
| A | Data, EDA, threshold calculation, wastewater (stretch) |
| B | Evaluation framework, preprocessing, classical models |
| C | Chronos, probability outputs, optional LLM comparison |
| D | Streamlit dashboard, AI assistant, deployment |
| E | Slides, storytelling, written deliverables (incl. product description and AI-tools statement) |

## Timeline

| Date | Milestone |
|---|---|
| Sun 10/18 | Data fetched; EDA starts; evaluation framework and naive baseline done |
| Mon 10/19 | Models run in parallel; dashboard skeleton; threshold finalized |
| Tue 10/20 noon | All model results ready |
| Tue 10/20 afternoon | Probability outputs; dashboard integrated and deployed; slides built |
| **Tue 10/20 night** | **Results frozen: no number changes after this** |
| Wed 10/21 | Final slides shared at noon; full rehearsal at night |
| **Thu 10/22 AM** | **Presentation** |
