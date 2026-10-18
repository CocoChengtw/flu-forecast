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
- **Test:** 2025–26, MMWR weeks 40–20, where flu activity is concentrated (CDC's surveillance year runs weeks 40–39). Horizons 1–4.
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

## 6. Threshold (pending, Flora)
- **Method:** mean + 2 SD of off-season ILI+ (MMWR weeks 21–39), last 3 non-COVID seasons, raw data.
- This is *adapted from* CDC's ILINet baseline: CDC defines non-flu weeks using public-health-lab counts, which our data lacks.
- **Onset week** = the first of 2 consecutive weeks above the threshold.
- **Value:** _TBD_. Sanity check: historical onsets should fall around Nov–Dec.

## Checking any model
Run `python -m src.diagnostics naive ets chronos …` for each model:
- zero share
- 90% coverage (target ≈ 0.90)
- interval width (shoulder vs. peak)
- MAE

Run it before trusting a model's probabilities.
