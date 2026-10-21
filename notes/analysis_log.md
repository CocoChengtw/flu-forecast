# Analysis Log

Key decisions and the reasons behind them, for the methods and limitations slides. Exact values are in `src/config.py`.

## 1. Target: ILI+ instead of test positivity
- Positivity depends on who gets tested; it measures flu among the *tested*, not in the population.
- **ILI+ = weighted ILI% × % flu positive / 100**: ILI% gives scale, positivity gives specificity.
- Example: in 2020–21, COVID kept ILI% elevated while flu positivity was ≈ 0. ILI+ correctly shows almost no flu.
- **Limitations:** counts only people who seek care; assumes tested patients represent ILI patients; it is a relative index, not a case count.

## 2. Rejected source: computationalUncertaintyLab/iliplus
- **Stale:** ends Jan 2025, so it has no 2025–26 test season.
- **Wrong scale:** ILI+ ÷ ILI% reaches 7,406, but positivity can't exceed 100%. It seems to use positive *counts*, which grow with testing volume.
- **Data quality:** 881 duplicate rows, 4,859 missing values.
- It does use the same sources as ours (Delphi + CDC clinical labs), which supports our approach.

## 3. Evaluation setup
- **Data:** national ILI+ from 2016–17 (clinical-lab positivity in the Delphi data starts at MMWR 2016 week 40).
- **Test:** 2025–26, MMWR weeks 40–20, where flu activity is concentrated (CDC's surveillance year runs weeks 40–39). Horizons 1–4.
- **Second fold:** 2024–25 (origins 2024-09-29 to 2025-05-11), using only data before it. With one test season, all ~34 origins come from one epidemic and are highly correlated, so a ranking could hinge on one unusual season. Main results use 2025–26; 2024–25 checks whether rankings hold.
- **Rolling origin:** at every test week, each model sees only data up to that week. A leak test confirmed this.

## 4. COVID: impute only 2020–21

| Season | What happened | Handling |
|---|---|---|
| 2019–20 | Normal peak, ended early | Kept |
| **2020–21** | **Flu nearly absent** | **Imputed** |
| 2021–22 | Irregular (small, late spring wave) | Kept |
| 2022–23 | Early, large rebound | Kept |

- We impute only when flu was absent, not when a season was merely unusual. Irregular seasons are real variation that forecasts must handle.
- Imputed values are the same-week mean of **pre-test** seasons (no leakage). Raw data is never modified, and the threshold uses raw data.

## 5. Seasonal naive: fixing the uncertainty
- **Baseline:** same MMWR week last year. Hand-written because MMWR years have 52 or 53 weeks, and we need 500 paths.
- **Problem:** errors bootstrapped from *all* weeks put peak-season errors (±1.5) on October values (~0.02). The early-October 90% upper bound was 0.87, ~70× the median, which would badly inflate threshold probabilities.
- **Fix:**
  - Draw errors only from ±4 weeks of the same time of year.
  - Exclude imputed COVID weeks.
  - **Center** the noise so the path median stays at last year's value. Without centering, MAE rose 0.355 → 0.437.

| Version | Zero share | 90% coverage | Shoulder width | Peak width | MAE |
|---|---|---|---|---|---|
| All weeks (before) | 0.121 | 0.809 | 1.101 | 1.455 | 0.355 |
| Seasonal window (after) | 0.179 | 0.956 | 0.506 | 2.111 | 0.355 |

- Coverage should be **close to 0.90 with narrow intervals**, so higher is not automatically better. 0.96 is slightly conservative, which is preferable to overconfident.
- The remaining zeros fall in shoulder weeks, where actual ILI+ is ~0.01–0.05, so they are close to correct.
- **Why ±4 weeks:** a judgment call made before seeing results: about one month, matching the 4-week horizon, and enough history to resample from. Sensitivity check (`python -m src.diagnostics --naive-variants [--fold 2024-25]`):

| Window | Coverage 2025–26 | Coverage 2024–25 | Shoulder width 2025–26 |
|---|---|---|---|
| ±2 | 0.89 | 0.82 | 0.40 |
| **±4** | **0.96** | **0.85** | **0.51** |
| ±6 | 0.93 | 0.88 | 0.69 |
| ±8 | 0.90 | 0.88 | 0.78 |
| All weeks | 0.81 | 0.88 | 1.10 |

- No window is best on both folds. ±4 averages ≈ 0.90 coverage across the two folds with narrower shoulder intervals than ±6/±8, so we keep it rather than tune it on test results. Every seasonal window fixes the absurd shoulder intervals.

## 6. Thresholds (Flora; `python -m src.audit_threshold`)
Two thresholds, both locked from pre-test data before looking at 2025–26 results:

| Threshold | Value | Method | Role |
|---|---|---|---|
| **High activity** (`HIGH_THRESHOLD`) | 0.6939 | 75th percentile of in-season ILI+ (weeks 40–20), 2022–23 to 2024–25 | **Main output:** surge decisions (staffing, beds) |
| **Early rise** (`EARLY_RISE_THRESHOLD`) | 0.0282 | Mean + 2 SD of off-season ILI+ (MMWR weeks 21–39), 2023–2025, raw data | Secondary: activity rising above the summer floor |

- **Event rule:** if ILI+ is currently below a threshold, report P(any of the next 1–4 weeks is above it). If it is already above, show "Above threshold" instead of a probability, since it would stay near 100% for weeks.
- Why two: the early-rise threshold alone is exceeded in 28 of 34 test weeks, so probabilities would be ~100% most of the season. With the high-activity threshold, historical crossings fall in Dec–Jan (Nov in the early 2022–23 season), the small 2021–22 season never crosses, and 10 of 34 test weeks are above it.
- The early-rise threshold is *adapted from* CDC's ILINet baseline (CDC defines non-flu weeks using public-health-lab counts, which our data lacks). Its first 2-week crossing falls in October in 7 of 9 pre-test seasons.

## 7. Classical models (`src/classical.py`, compared by `src/compare.py`)
- All fit on **log(ILI+ + 0.01)**: ILI+ spans 0.0015–2.6 and rises multiplicatively; the log keeps paths positive. Refit at every origin on data up to it.
- **ETS:** additive error, damped trend, 52-week additive seasonality.
- **ARIMA:** dynamic harmonic regression, ARMA errors + Fourier terms (period 365.25/7, so 53-week years are handled). Order and K chosen by AIC on data **before each fold**: AR(2), K=4 (2025–26); ARMA(2,1), K=4 (2024–25).
- **Prophet:** yearly seasonality only; 500 predictive samples.

| Model | CRPS 2025–26 | CRPS 2024–25 | MAE 2025–26 | MAE 2024–25 |
|---|---|---|---|---|
| Naive | 0.253 | 0.275 | 0.355 | 0.319 |
| ETS | 0.227 | 0.181 | 0.289 | 0.248 |
| **ARIMA** | 0.184 | **0.160** | 0.234 | **0.211** |
| Prophet | **0.150** | 0.285 | **0.219** | 0.391 |

(averaged over horizons 1–4; CRPS scores the whole forecast distribution, lower is better)

- **Reproducibility:** ETS fits now converge at every origin (the default cap of 15,000 likelihood evaluations stopped them early), and simulations are seeded so reruns give identical paths on statsmodels 0.14 and 0.15 (`tests/test_classical.py`). Rerunning moved the metrics by at most 0.003 and changed no rankings.
- **ARIMA is the most consistent:** 27–42% lower CRPS than naive in both folds.
- **ETS and ARIMA are excellent 1 week ahead** (CRPS 0.07–0.10 vs. naive 0.25), but error grows with horizon. At 4 weeks they extrapolate the winter rise through the peak and overshoot afterwards (ETS 4-week median up to ~7 vs. observed ~1).
- **Prophet's rank flips:** best in 2025–26, worst in 2024–25. It forecasts a smooth seasonal average and underestimates every peak (median ~0.7 vs. observed 2.6). This is exactly why we test on two folds.

## 8. Limitations
- **One main test season:** results rest on 2025–26; the 2024–25 fold is a robustness check, not a full replication.
- **Data revisions:** we use the latest revised values, not what was known in real time. Delphi stores first-reported values (`lag`/`issues`) if we want an as-of-date evaluation later.
- **ETS seasonality** uses a fixed 52-week period, an approximation in 53-week years (ARIMA's Fourier terms do not need it).
- **Wastewater** measures influenza A only, while ILI+ counts A and B; a lead-time comparison should use flu-A ILI+ (`wili × percent_a / 100`).

## Checking any model
Run `python -m src.diagnostics naive ets chronos …` for each model:
- zero share
- 90% coverage (target ≈ 0.90)
- interval width (shoulder vs. peak)
- MAE

Run it before trusting a model's probabilities.
