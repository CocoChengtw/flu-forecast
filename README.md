# Seeing the Surge Coming

**LLM vs. Statistical Forecasts of Flu Season, Deployed as a Live Dashboard**

Group final project for Time Series Analysis and Forecasting (UCLA Anderson, Dr. William Yu).

## Goal

Forecast weekly U.S. influenza test positivity 1–4 weeks ahead and compare:

- **Classical models**: seasonal naive, ETS, ARIMA, Prophet
- **AI forecasting models**: a time-series foundation model (e.g. Chronos) and, optionally, a general-purpose LLM

Then deploy the best approach as an interactive Streamlit dashboard with an AI assistant that explains the forecast. We also test whether wastewater virus levels give an early warning before test positivity rises.

## Data

| File | Source | Notes |
|---|---|---|
| `data/raw/flunet_us.csv` | Our World in Data, Influenza Data Explorer (WHO FluNet) | Weekly share of positive flu tests, all countries |
| `data/raw/nwss_flu_a.csv` | CDC NWSS via Data.gov ([dataset](https://catalog.data.gov/dataset/cdc-wastewater-data-for-influenza-a)) | Influenza A wastewater samples by site. **Not in the repo (141 MB).** |
| `data/processed/flu_positivity_us_weekly.csv` | Output of `src/clean.py` | U.S. only, one row per week |
| `data/processed/nwss_flu_a_weekly.csv` | Output of `src/clean.py` | National weekly summary of wastewater levels |

You do **not** need the raw wastewater file to work on the project. Use the processed files.

To rebuild the processed files yourself, download the raw wastewater CSV from
`https://data.cdc.gov/api/views/ymmh-divb/rows.csv?accessType=DOWNLOAD`,
save it as `data/raw/nwss_flu_a.csv`, then run `python src/clean.py`.

## Repo structure

```
flu-forecast/
├── data/
│   ├── raw/            original downloads, never edit by hand
│   └── processed/      cleaned weekly series
├── src/                shared code (cleaning, models, evaluation)
├── notebooks/          personal exploration notebooks
├── app/                Streamlit dashboard
├── requirements.txt
├── .env.example
└── README.md
```

## First-time setup

Use **Python 3.11** (Prophet is most reliable on 3.11).

```bash
git clone https://github.com/<OWNER>/flu-forecast.git
cd flu-forecast
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
nbstripout --install
cp .env.example .env
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.

Only the person running AI forecasts needs to put an API key in `.env`. Everyone else can leave it empty.

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

- Name notebooks with your name: `notebooks/01_eda_<name>.ipynb`
- Move reusable functions into `src/` so we don't each write our own version
- Never commit `.env` or API keys
- Keep `main` runnable
- All models use the same forecast origins, horizons, and test period so the comparison is fair

## Timeline (due Oct 26)

| Dates | Work |
|---|---|
| Oct 17–18 | Data, cleaning, EDA, fix train/test split |
| Oct 19–21 | Classical models + AI forecasts, rolling-origin evaluation |
| Oct 21–22 | Streamlit dashboard + AI assistant |
| Oct 23 | Ensemble, wastewater lead-time analysis |
| Oct 24–25 | Slides (max 10), product write-up, code cleanup, AI-tools statement |
| Oct 26 | Submit on Bruin Learn |
