# B: Evaluation Framework & Classical Models (Coco)

Reasons behind these decisions are in `notes/analysis_log.md`.

### Oct 18
- `fetch_ili_plus.py`: ILI+ via the Delphi API, national + HHS Region 9, from 2015–16.
- `config.py`: shared settings (test period, COVID window, horizons, 500 paths, seed).
- `evaluate.py`: rolling-origin framework + COVID imputation; leak test passed.
- `naive.py`: seasonal naive baseline; uncertainty fixed (coverage 0.81 → 0.96, shoulder width 1.10 → 0.51, MAE unchanged at 0.355).
- `diagnostics.py`: zero share, coverage, interval width, MAE for any model.
