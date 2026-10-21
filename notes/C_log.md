# C: Chronos & Probability Outputs (Christina)

Shared decisions are in `notes/analysis_log.md`; this log covers the Chronos model and the probability outputs.

### Oct 19

**Chronos (`src/chronos_model.py`)**
- Model: `amazon/chronos-t5-mini` (20M parameters), `chronos-forecasting` 2.3.2, torch 2.14, transformers 5.20, CPU. Zero-shot: no fine-tuning, no hyperparameter tuning.
- Plugged into `rolling_forecast()` unchanged; outputs `results/forecasts/chronos.csv` and `results/forecasts/fold_2024-25/chronos.csv` in the shared format.
- Context: the same COVID-imputed series every model gets, up to the origin (~420–470 weeks; Chronos keeps the last 512).
- Paths: 500 samples per origin drawn by Chronos itself (default sampling: temperature 1, top-k 50, top-p 1). Unlike naive, there is no bootstrap: the spread comes from the model's predictive distribution.
- Reproducibility: model loaded once per process; torch seed = `RANDOM_SEED + len(train)` at every origin, so each origin's paths don't depend on which other origins are run. Same inputs gave identical paths in tests.
- Negative samples are clipped to 0 (same as naive).
- Run: `python -m src.chronos_model` (both folds, ~6 s per origin on an M1 CPU), `python -m src.chronos_model --smoke` (one origin, nothing saved).

**Probabilities (`src/probabilities.py`)**
- Computed from the paths the same way for every model; works on any file in the shared format.
- **Threshold crossing** (high = main, early rise = secondary): if observed ILI+ at the origin is ≤ threshold, P = share of paths with any of weeks 1–4 above it. If already above: status "above", no probability, not scored (event rule in `analysis_log.md` §6).
- **Onset** (early-rise threshold, 2 consecutive weeks, counted from MMWR week 40): if onset hasn't happened by the origin, P(the 2-week rule is met by the end of the 4-week window). A run may start at the observed origin week (origin above + week 1 above = onset at the origin). After onset: status "passed", not scored.
- **Peak timing: not computed.** "The season peaks in the next 4 weeks" depends on what happens after the 4-week horizon, so it can't be read from 4-week paths or scored with them. Final decision: see "Final probability outputs" below.
- **Brier score** per model and event, over the origins with a reported probability. Which origins are scored depends only on observed data, so every model is scored on the same origins (checked in code).
- Run: `python -m src.probabilities naive chronos [--fold 2024-25]`; saves `results/probabilities/<model>.csv` (fold 2024-25 in a subfolder).

**Tests:** `python -m pytest tests`

### Oct 19 (evening): runs completed, results

**What was run (all completed, no errors, no retries needed)**
- `python -m src.chronos_model`: both folds, 34 origins (2025-26) and 33 (2024-25), 500 paths each, ~3 min total on CPU. Files: `results/forecasts/chronos.csv`, `results/forecasts/fold_2024-25/chronos.csv`.
- `python -m src.diagnostics naive chronos [--fold 2024-25]`
- `python -m src.probabilities naive chronos [--fold 2024-25]`: files in `results/probabilities/`.
- `python -m pytest tests`: 17 passed, 0 skipped (the saved-file schema checks now run for both folds: same columns, same origins as naive, full origin x path x horizon grid).
- Methodology unchanged from the morning entry: zero-shot, default sampling, same origins and context as naive.

**Point accuracy (path median vs raw ILI+)**

| Fold | Horizon | MAE Chronos | MAE naive | RMSE Chronos | RMSE naive |
|---|---|---|---|---|---|
| 2025-26 | 1 | 0.136 | 0.355 | 0.291 | 0.606 |
| | 2 | 0.201 | 0.355 | 0.458 | 0.606 |
| | 3 | 0.265 | 0.356 | 0.541 | 0.606 |
| | 4 | 0.296 | 0.356 | 0.553 | 0.606 |
| 2024-25 | 1 | 0.126 | 0.320 | 0.215 | 0.586 |
| | 2 | 0.213 | 0.320 | 0.373 | 0.586 |
| | 3 | 0.263 | 0.319 | 0.466 | 0.586 |
| | 4 | 0.303 | 0.318 | 0.500 | 0.586 |

Chronos beats naive at every horizon in both folds; the gap shrinks with horizon (MAE about -60% at h=1, -5 to -17% at h=4). Naive's error is flat across horizons by construction (same week last year doesn't depend on h).

**Intervals (`src.diagnostics`): Chronos is badly overconfident**

| Fold | Model | 90% coverage | Coverage peak / shoulder | Median width shoulder / peak | Zero share |
|---|---|---|---|---|---|
| 2025-26 | Chronos | **0.60** | 0.37 / 0.84 | 0.037 / 0.283 | 0.00 |
| | naive | 0.96 | 0.91 / 1.00 | 0.506 / 2.111 | 0.18 |
| 2024-25 | Chronos | **0.61** | 0.30 / 0.90 | 0.063 / 0.279 | 0.00 |
| | naive | 0.85 | 0.69 / 1.00 | 0.581 / 1.460 | 0.18 |

- Chronos misses on both sides at the peak (2025-26: 29% of actuals below q05, 34% above q95), so it's not just a biased median; the bands are too narrow. Coverage is lowest at h=1 (0.53 / 0.58).
- Per the team rule ("check intervals before trusting probabilities"), **Chronos probabilities should be presented as overconfident**, not as calibrated.

**Brier scores (scored origins only; BSS = 1 - Brier_chronos / Brier_naive, > 0 means Chronos is better)**

| Fold | Event | n origins | Event rate | Brier Chronos | Brier naive | BSS vs naive |
|---|---|---|---|---|---|---|
| 2025-26 | **high** (main) | 24 | 0.17 | 0.049 | 0.072 | **+0.32** |
| | early_rise | 6 | 0.67 | 0.246 | 0.215 | -0.15 |
| | onset | 6 | 0.67 | 0.218 | 0.172 | -0.27 |
| 2024-25 | **high** (main) | 22 | 0.18 | 0.146 | 0.049 | **-1.99** |
| | early_rise | 4 | 1.00 | 0.273 | 0.056 | -3.86 |
| | onset | 5 | 0.80 | 0.250 | 0.144 | -0.74 |

- High threshold, 2025-26: Chronos wins because it stays at 0% through the Feb-Mar decline, where naive gave 12-79% (last year's peak was later). It was still late on the rise: 6% on 11-16 when a crossing followed.
- High threshold, 2024-25: Chronos gave ~0% (0.000-0.020) on 11-17, 11-24 and 12-01, all followed by a crossing; those three origins are almost its whole Brier score. Naive gave 69-81%.
- Pattern: near-0/1 probabilities from narrow intervals. That pays off when the series is smooth and is penalized hard at the turn of the season, when early warning matters most.
- Early-rise and onset rest on 4-6 origins (event rate 0.67-1.0); not interpretable as a model comparison.

**Limitations (still open)**
- Overconfident Chronos intervals; not fixed, since fixing them (e.g. sampling temperature, recalibration, a larger Chronos) would change the method and needs a team decision, ideally tuned on pre-test seasons only.
- Small samples: ~4 positive high-threshold outcomes per fold, and consecutive origins share 3 of 4 target weeks, so outcomes are autocorrelated. The BSS sign flips between folds; no significance claim.
- Zero-shot with fixed weights (handbook §13.3 "Method III"), while naive rebuilds its error pool every origin (closer to "Method IV"). Same information at each origin, so the comparison is fair, but worth stating.
- Pooled MAE/RMSE are dominated by peak weeks (ILI+ ranges ~0.01 to >1).
- Revised (not real-time) ILI+, as in `analysis_log.md` §7.
- Thresholds are fixed constants from `config.py`, used unchanged in both folds. They were locked from 2022-23 to 2024-25 data (high) and the 2023-2025 off-seasons (early rise), so for the **2024-25 fold** they are not strictly pre-fold: they include that season (and the following summer). Models never see the thresholds and both are scored against the same ones, so the comparison is fair; only the threshold itself carries fold information. Kept as agreed; worth one line on the limitations slide.
- **For team discussion (shared files not edited):** README line 28 lists "Peak timing: the chance the season peaks within the next 4 weeks" as an output, README line 84 lists onset-week and peak-week error as metrics, and the `N_PATHS` comment in `config.py` mentions "peak" probabilities. None of these exist in the code, and peak timing is now out of scope (below).

### Oct 19: final probability outputs (verified)

Team decision: final outputs are exactly three events, using only the existing definitions in `src/config.py` and `notes/analysis_log.md` §6. No peak-timing prediction, no new thresholds.

| Event | Threshold | Rule | Not scored when |
|---|---|---|---|
| High activity crossing (main) | `HIGH_THRESHOLD` = 0.6939 | P(any of weeks 1-4 > threshold), if ILI+ at origin ≤ threshold | ILI+ at origin above it ("Above threshold") |
| Early rise crossing | `EARLY_RISE_THRESHOLD` = `THRESHOLD` = 0.0282 | same | same |
| Onset | `EARLY_RISE_THRESHOLD`, `ONSET_CONSECUTIVE_WEEKS` = 2 | P(first run of 2 consecutive weeks above the threshold, counted from MMWR week 40, is confirmed within the 4-week window) | onset already confirmed by the origin |

- "Above" is strict (`>`) everywhere, matching `eda.py` and `audit_threshold.py`, which use the same onset rule (first 2 consecutive weeks above `THRESHOLD`, from week 40 of each season).
- Onset wording: the shared docs define the onset *week*; the onset *probability* applies the §6 event rule to it (report while pending, stop once it has happened).
- Both folds run through the same functions with the same constants; only the forecast file changes.
- **Independent check:** a separate loop-based re-implementation of these rules (not sharing code with `src/probabilities.py`) reproduced every saved probability, outcome and threshold for both models in both folds: 0 mismatches. Scored origins: 2025-26 high 24, early rise 6, onset 6; 2024-25 high 22, early rise 4, onset 5. (The `threshold` column in the CSVs is written to 15 significant digits; the calculation uses the full `config` value.)
- Forecasts and probability files were not re-run or changed by this check (checksums identical before and after).
