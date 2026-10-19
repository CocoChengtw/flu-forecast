# B: Evaluation Framework & Classical Models (Coco)

Reasons behind these decisions are in `notes/analysis_log.md`.

### Oct 18
- `fetch_ili_plus.py`: ILI+ via the Delphi API, national + HHS Region 9 (data starts 2016–17).
- `config.py`: shared settings (test period, COVID window, horizons, 500 paths, seed).
- `evaluate.py`: rolling-origin framework + COVID imputation; leak test passed.
- `naive.py`: seasonal naive baseline; uncertainty fixed (coverage 0.81 → 0.96, shoulder width 1.10 → 0.51, MAE unchanged at 0.355).
- `diagnostics.py`: zero share, coverage, interval width, MAE for any model.
- Added a second test fold (2024–25) to `config.TEST_FOLDS`; `rolling_forecast(..., fold=...)`. Naive MAE 0.355 (2025–26) / 0.319 (2024–25).
- Seasonal-window sensitivity (±2/4/6/8/all weeks) on both folds; kept ±4.
