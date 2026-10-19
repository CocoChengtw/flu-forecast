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
Two thresholds, both fixed from pre-test data only:

| Threshold | Value | Method | Meaning |
|---|---|---|---|
| **Onset** | 0.0282 | Mean + 2 SD of off-season ILI+ (MMWR weeks 21–39), 2023–2025, raw data | Activity rising above the summer floor: early warning |
| **High activity** | 0.6939 | 75th percentile of in-season ILI+ (weeks 40–20), 3 most recent pre-test seasons | Surge decisions (staffing, beds) |

- The onset threshold is *adapted from* CDC's ILINet baseline: CDC defines non-flu weeks using public-health-lab counts, which our data lacks.
- **Onset week** = the first of 2 consecutive weeks above the onset threshold. It captures the early rise, so historical onsets are mostly in October (7 of 9 pre-test seasons).
- On its own, the onset threshold is exceeded in 28 of 34 test weeks, so crossing probabilities would be ~100% most of the season. Hence the second threshold: historical high-activity starts fall in Dec–Jan (Nov in the early 2022–23 season), the small 2021–22 season never crosses, and 10 of 34 test weeks are above it.

## 7. Limitations
- **One main test season:** results rest on 2025–26; the 2024–25 fold is a robustness check, not a full replication.
- **Data revisions:** we use the latest revised values, not what was known in real time. Delphi stores first-reported values (`lag`/`issues`) if we want an as-of-date evaluation later.
- **Wastewater** measures influenza A only, while ILI+ counts A and B; a lead-time comparison should use flu-A ILI+ (`wili × percent_a / 100`).

## Checking any model
Run `python -m src.diagnostics naive ets chronos …` for each model:
- zero share
- 90% coverage (target ≈ 0.90)
- interval width (shoulder vs. peak)
- MAE

Run it before trusting a model's probabilities.
