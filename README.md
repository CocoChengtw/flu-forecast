# Seeing the Surge Coming

**AI vs. Statistical Forecasts of Flu Season, Deployed as a Live Dashboard**

**▶ Live demo: [flu-surge-outlook.netlify.app](https://flu-surge-outlook.netlify.app)** · **Slides: [seeing-the-surge-coming.pdf](slides/seeing-the-surge-coming.pdf)**

Group final project for Time Series Analysis and Forecasting (UCLA Anderson, Dr. William Yu).

## Dashboard

The [Flu Surge Outlook](https://flu-surge-outlook.netlify.app) shows the current U.S. flu activity level, each model’s chance of a surge in the next four weeks, and recommended actions for different audiences.

How to use it:

- Use the toggle at the top to switch between the **case study** (the week of Nov 16, 2025, four weeks before that season’s surge) and the **latest week** of data.
- Click a model chip (e.g. ARIMA, Chronos, or "All 5 combined") to see that model’s forecast and surge chance; in the case study, **Show what happened next** reveals the outcome.
- Pick an audience tab under **Recommended now** for suggested actions, or click **Ask about this forecast** to ask the AI assistant a question in plain language.

## Goal

Give national or regional public-health planners early warning of high flu activity, so they can decide when to scale up staffing, supplies and public messaging.

We forecast weekly U.S. **ILI+** 1–4 weeks ahead and compare classical statistical models with an AI forecasting model. The best results are shown in a web dashboard with an AI assistant that explains the forecast in plain language.

### Forecast target: ILI+

**ILI+ = weighted ILI% × (% of flu tests positive / 100)**

- **ILI%** (influenza-like illness): the share of outpatient visits for fever plus cough or sore throat, from CDC's ILINet network. It measures how many people are sick, but it also counts COVID, RSV and colds.
- **% positive**: the share of clinical-lab flu tests that are positive. It is flu-specific, but it says nothing about how many people are sick.

Multiplying them estimates the share of outpatient visits that are actually flu. We switched from test positivity alone because positivity depends on who gets tested and cannot tell a mild season from a severe one. See `notes/analysis_log.md` for the full reasoning.

### Outputs

The forecasts are framed around timing decisions, not just point estimates:

1. **Threshold probability (priority):** the chance ILI+ goes above a threshold within the next 1–4 weeks. If ILI+ is already above it, we show "Above threshold" instead, since the probability would stay near 100% for weeks.
2. **Onset week:** the first of two consecutive weeks above the early-rise threshold.

Peak timing was dropped as out of scope.

Two thresholds, both locked from pre-test data before looking at 2025–26 results:

| Threshold | Value | Role |
|---|---|---|
| **High activity** (`HIGH_THRESHOLD`) | 0.694 | **Main output:** early warning of high flu activity |
| **Early rise** (`EARLY_RISE_THRESHOLD`) | 0.028 | Secondary: activity rising above the summer floor |

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
| Second test fold | 2024–25, trained only on data before it, to check that model rankings hold beyond one season (`config.TEST_FOLDS`). |
| Horizons | 1–4 weeks ahead |
| COVID | 2020–21 (flu nearly absent) is replaced with the same-week mean of other pre-test seasons and flagged `is_imputed`. 2021–22 is kept as observed. |
| Thresholds | **High activity:** 75th percentile of in-season ILI+ (weeks 40–20) over the 3 most recent pre-test seasons. **Early rise:** off-season (MMWR weeks 21–39) mean + 2 SD over the last 3 non-COVID pre-test seasons, adapted from CDC's ILINet baseline method. |
| Uncertainty | Every model produces 500 simulated paths per origin. All probabilities are computed from these paths the same way for every model. |

**Models**

- Classical: seasonal naive (baseline), ETS, ARIMA with Fourier terms, Prophet
- AI: Chronos (`amazon/chronos-t5-mini`, a pretrained time-series model, used zero-shot)
- The optional ChatGPT/Claude forecast comparison was not pursued.

**Metrics**

- Point forecasts (path median): MAE, RMSE
- Whole forecast distribution: CRPS and 90% interval coverage
- Threshold probabilities: Brier score. The high-activity event is the main metric; early rise and onset have only 4–6 scorable weeks per season, so models are not ranked on them.

**Wastewater (stretch goal):** a lead-time analysis of wastewater vs. influenza-A ILI+ only. The wastewater history is too short to use as a model input. Use `ili_plus_a_weekly.csv` and the `nwss_flu_a_*_filtered.csv` files for the comparison/map; original aggregates remain available for audit. The coverage screen uses each geography's prior-eight-week median site count, with a 50% cutoff. See [wastewater preparation and map guidance](notes/wastewater_stretch.md) for limitations, missing-week handling, and reproduction commands. Finding: wastewater tracks flu-A ILI+ closely (same-week correlation 0.90–0.95) but gave no consistent early warning within ±4 weeks ([details](notes/wastewater_lead_exploration.md)).

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

Plug a model into the rolling-origin framework in `src/evaluate.py` and it writes this file for you. Run both folds: `rolling_forecast(model_fn, "<model>")` and `rolling_forecast(model_fn, "<model>", fold="2024-25")`; the second fold is saved in `results/forecasts/fold_2024-25/`. Run `python -m src.diagnostics <model>` to check a model's intervals before trusting its probabilities.

## Results

Full tables: `results/metrics_summary.csv` (accuracy) and `results/probabilities/` (threshold probabilities); reasoning in `notes/analysis_log.md`.

- **ARIMA was the most consistent model:** 27–42% lower CRPS than the naive baseline in both test seasons.
- **Chronos (AI) was competitive but overconfident:** its 90% intervals held the actual value only about 60% of the time.
- **Surge probabilities are fragile:** only Prophet beat the naive baseline on the high-activity Brier score in both seasons, with just four threshold crossings per season.

## AI tools statement

We used AI tools in two ways: inside the analysis and product, and to help build them. In the analysis, Chronos (Amazon’s pretrained time-series foundation model, chronos-t5-mini, used zero-shot) was one of our five forecasting models, evaluated under the same rolling-origin design as the statistical models; it was competitive on accuracy but overconfident, with 90% intervals covering the actual value only about 60% of the time. In the product, the dashboard’s assistant uses Anthropic’s Claude to answer questions in plain language from the page’s own numbers, falling back to pre-written answers when the model is unavailable. For development, several team members used Claude Code, an AI coding assistant, to research data sources, build the dashboard, and draft documentation. All AI-assisted work went through pull-request review, automated tests and independent reruns by teammates, which also caught errors: for example, two incorrect claims in a draft were corrected after we checked them against the results.

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
│   ├── forecasts/      one CSV per model, shared format above (fold_2024-25/ for the second fold)
│   ├── probabilities/  threshold probabilities per model
│   └── figures/
├── notes/              decision log for the methods and limitations slides
├── tests/              python -m pytest tests
├── app/                Flu Surge Outlook dashboard (React page + AI assistant, deployed on Netlify), see app/README.md
├── slides/             final presentation deck (PDF)
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

Only the dashboard's AI assistant needs an API key in `.env`. Everyone else can leave it empty.

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
| C | Chronos, probability outputs |
| D | Dashboard, AI assistant, deployment |
| E | Slides, storytelling, written deliverables (incl. product description and AI-tools statement) |

## Timeline

| Date | Milestone |
|---|---|
| Sun 10/18 | Data fetched; EDA starts; evaluation framework and naive baseline done |
| Mon 10/19 | Models run in parallel (both folds); dashboard skeleton; thresholds finalized |
| Tue 10/20 noon | All model results ready |
| Tue 10/20 afternoon | Probability outputs; dashboard integrated and deployed; slides built |
| **Tue 10/20 night** | **Results frozen: no number changes after this** |
| Wed 10/21 | Final slides shared at noon; full rehearsal at night |
| **Thu 10/22 AM** | **Presentation** |
