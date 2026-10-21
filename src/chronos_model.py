"""
Chronos (amazon/chronos-t5-mini): a pretrained time-series foundation model, used
zero-shot (no fine-tuning) inside the shared rolling-origin framework.

- Context: the same COVID-imputed ILI+ series every model gets, up to the origin.
  Chronos keeps only the last 512 weeks, which covers all our history.
- Paths: Chronos generates sample paths directly (default sampling: temperature 1,
  top-k 50, top-p 1). We ask for 500, the same as every model.
- Reproducibility: the model is loaded once per process and torch's global RNG is
  reseeded at every origin with RANDOM_SEED + len(train), so each origin's paths
  are the same whatever order or subset of origins is run. Runs on CPU, where
  sampling is deterministic.
- Chronos can return small negative values near zero; they are clipped to 0 like
  the naive baseline (ILI+ can't be negative).

Run from the repo root (about 6 s per origin on an M1 CPU, ~8 min for both folds):
    python -m src.chronos_model
    python -m src.chronos_model --smoke    # one origin only, nothing saved
"""

import argparse
from functools import lru_cache

import numpy as np
import pandas as pd
import torch

from src import config
from src.evaluate import get_origins, point_metrics, prepare_series, rolling_forecast

MODEL_ID = "amazon/chronos-t5-mini"


@lru_cache(maxsize=1)
def load_pipeline():
    """Load the Chronos pipeline once per process (downloaded to the HF cache on first use)."""
    from chronos import ChronosPipeline  # noqa: PLC0415  (slow import, only when needed)

    return ChronosPipeline.from_pretrained(MODEL_ID, device_map="cpu", dtype=torch.float32)


def sample_paths(train: pd.Series, horizon: int, n_paths: int) -> np.ndarray:
    """Raw Chronos samples (before clipping), shape (n_paths, horizon)."""
    if train.isna().any():
        raise ValueError(f"chronos: missing values in context ending {train.index[-1].date()}")

    torch.manual_seed(config.RANDOM_SEED + len(train))
    context = torch.tensor(train.values, dtype=torch.float32)
    samples = load_pipeline().predict(context, prediction_length=horizon, num_samples=n_paths)
    paths = samples[0].numpy().astype(float)

    if not np.isfinite(paths).all():
        raise ValueError(f"chronos: non-finite forecast at origin {train.index[-1].date()}")
    return paths


def chronos_forecast(train: pd.Series, horizon: int, n_paths: int) -> np.ndarray:
    """Chronos sample paths, shape (n_paths, horizon). The model_fn for rolling_forecast."""
    return np.clip(sample_paths(train, horizon, n_paths), 0, None)   # ILI+ can't be negative


def smoke_test(fold: str = config.MAIN_FOLD) -> None:
    """Forecast the first origin of a fold and print a few checks (nothing saved)."""
    start, end = config.TEST_FOLDS[fold]
    s = prepare_series(cutoff=start)
    origin = get_origins(s, start, end)[0]
    train = s.loc[:origin].copy()
    train.attrs["epiweek"] = s.attrs["epiweek"].loc[:origin]

    raw = sample_paths(train, max(config.HORIZONS), config.N_PATHS)
    paths = np.clip(raw, 0, None)
    print(f"origin {origin.date()}  last train week {train.index[-1].date()}  "
          f"context {len(train)} weeks")
    print(f"shape {paths.shape}  NaN {np.isnan(paths).sum()}  "
          f"negative before clip {(raw < 0).mean():.3%}")
    print("median by horizon:", np.round(np.median(paths, axis=0), 4))
    print("observed:         ", np.round(s.loc[origin:].iloc[1:max(config.HORIZONS) + 1].values, 4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--smoke", action="store_true", help="one origin, nothing saved")
    args = parser.parse_args()

    if args.smoke:
        smoke_test()
    else:
        for fold in config.TEST_FOLDS:
            fc = rolling_forecast(chronos_forecast, "chronos", fold=fold)
            print(point_metrics(fc).to_string(index=False))
