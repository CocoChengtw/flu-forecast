"""
Classical forecasting models: ETS, ARIMA with Fourier terms, and Prophet.

Every model follows the shared interface in src/evaluate.py:
    model_fn(train, horizon, n_paths) -> array of shape (n_paths, horizon)

Shared choices (decided before looking at test results):
- All models work on log(ILI+ + LOG_EPS). ILI+ spans 0.0015 to 2.6, and the
  winter rise is multiplicative; the log keeps simulated paths positive and
  lets seasonal swings scale with the level. Paths are transformed back.
- Each origin refits the model on data up to that origin only.
- Model orders are chosen by AIC on data before the test fold, never on test data.

Run from the repo root (both folds, all three models):
    python -m src.classical
    python -m src.classical --models ets arima      # a subset
"""

import argparse
import time
import warnings

import numpy as np
import pandas as pd

from src import config
from src.evaluate import point_metrics, prepare_series, rolling_forecast

LOG_EPS = 0.01           # off-season ILI+ is ~0.01-0.05
PERIOD_WEEKS = 365.25 / 7  # Fourier period: handles 52- and 53-week years


def to_log(x):
    return np.log(np.asarray(x, dtype=float) + LOG_EPS)


def from_log(z):
    return np.clip(np.exp(z) - LOG_EPS, 0, None)


def rng_for(train: pd.Series) -> np.random.Generator:
    return np.random.default_rng([config.RANDOM_SEED, len(train)])


def simulate(fit, train: pd.Series, **kwargs):
    """Call fit.simulate with a seeded RNG. statsmodels renamed the argument from
    `random_state` (<= 0.14) to `rng` (0.15+), so support both."""
    import inspect  # noqa: PLC0415

    rng = rng_for(train)
    if "rng" in inspect.signature(fit.simulate).parameters:
        return fit.simulate(**kwargs, rng=rng)
    # Older statsmodels only accepts an int or np.random.RandomState here, and
    # SARIMAX in 0.14 still draws part of the simulation from the global numpy
    # RNG, so seed that too or ARIMA paths change between runs.
    seed = int(rng.integers(2**31 - 1))
    np.random.seed(seed)
    return fit.simulate(**kwargs, random_state=seed)


# ---------------------------------------------------------------------------
# ETS: additive error, damped additive trend, additive seasonality (on log scale)
# ---------------------------------------------------------------------------
def fit_ets(train: pd.Series):
    from statsmodels.tsa.exponential_smoothing.ets import ETSModel  # noqa: PLC0415

    y = pd.Series(to_log(train.values))
    model = ETSModel(y, error="add", trend="add", damped_trend=True,
                     seasonal="add", seasonal_periods=52)
    # The fit estimates 58 parameters (52 are seasonal starting values), so it needs
    # ~45,000 likelihood evaluations. scipy's default cap (maxfun=15,000) stopped
    # every fit early, unconverged; raising maxiter alone does not lift that cap.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = model.fit(disp=False, maxiter=2000, maxfun=200_000)
    if not fit.mle_retvals["converged"]:
        print(f"[ets] warning: fit did not converge at origin {train.index[-1].date()}")
    return fit


def ets(train: pd.Series, horizon: int, n_paths: int) -> np.ndarray:
    fit = fit_ets(train)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sims = simulate(fit, train, nsimulations=horizon, anchor="end",
                        repetitions=n_paths)
    return from_log(np.asarray(sims).T)


# ---------------------------------------------------------------------------
# ARIMA with Fourier terms for the yearly cycle (dynamic harmonic regression)
# ---------------------------------------------------------------------------
def fourier(index: pd.DatetimeIndex, k: int, origin: pd.Timestamp) -> np.ndarray:
    t = ((index - origin).days / 7.0).to_numpy()
    cols = []
    for j in range(1, k + 1):
        cols += [np.sin(2 * np.pi * j * t / PERIOD_WEEKS),
                 np.cos(2 * np.pi * j * t / PERIOD_WEEKS)]
    return np.column_stack(cols)


T0 = pd.Timestamp(config.TRAIN_START)


def select_arima(fold: str) -> tuple[tuple[int, int, int], int]:
    """Pick (p, d, q) and Fourier K by AIC on data strictly before the fold."""
    from statsmodels.tsa.statespace.sarimax import SARIMAX  # noqa: PLC0415

    start, _ = config.TEST_FOLDS[fold]
    s = prepare_series(cutoff=start)
    s = s[s.index < start]
    y = to_log(s.values)
    best = None
    for k in (2, 3, 4, 5):
        x = fourier(s.index, k, T0)
        for order in [(1, 0, 0), (2, 0, 0), (1, 0, 1), (2, 0, 1), (3, 0, 0)]:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                aic = SARIMAX(y, exog=x, order=order, trend="c").fit(disp=False).aic
            if best is None or aic < best[0]:
                best = (aic, order, k)
    print(f"[arima] fold {fold}: selected order={best[1]}, K={best[2]} (AIC {best[0]:.1f})")
    return best[1], best[2]


def make_arima(order: tuple[int, int, int], k: int):
    def arima(train: pd.Series, horizon: int, n_paths: int) -> np.ndarray:
        from statsmodels.tsa.statespace.sarimax import SARIMAX  # noqa: PLC0415

        y = to_log(train.values)
        future = pd.date_range(train.index[-1] + pd.Timedelta(weeks=1),
                               periods=horizon, freq="7D")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = SARIMAX(y, exog=fourier(train.index, k, T0), order=order,
                          trend="c").fit(disp=False)
            sims = simulate(fit, train, nsimulations=horizon, anchor="end",
                            repetitions=n_paths, exog=fourier(future, k, T0))
        return from_log(np.asarray(sims).reshape(horizon, n_paths).T)
    return arima


# ---------------------------------------------------------------------------
# Prophet: yearly seasonality on the log scale; paths from predictive samples
# ---------------------------------------------------------------------------
def prophet(train: pd.Series, horizon: int, n_paths: int) -> np.ndarray:
    import logging  # noqa: PLC0415

    from prophet import Prophet  # noqa: PLC0415

    logging.getLogger("cmdstanpy").disabled = True
    df = pd.DataFrame({"ds": train.index, "y": to_log(train.values)})
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                daily_seasonality=False, uncertainty_samples=n_paths)
    np.random.seed(int(rng_for(train).integers(2**31)))   # Prophet samples with global numpy RNG
    m.fit(df)
    future = pd.DataFrame({"ds": pd.date_range(train.index[-1] + pd.Timedelta(weeks=1),
                                               periods=horizon, freq="7D")})
    samples = m.predictive_samples(future)["yhat"]          # (horizon, n_paths)
    return from_log(np.asarray(samples).T)


# ---------------------------------------------------------------------------
def run(models: list[str]) -> None:
    for fold in config.TEST_FOLDS:
        for name in models:
            if name == "arima":
                fn = make_arima(*select_arima(fold))
            else:
                fn = {"ets": ets, "prophet": prophet}[name]
            t = time.time()
            fc = rolling_forecast(fn, name, fold=fold)
            print(f"  ({time.time() - t:.0f}s)")
            print(point_metrics(fc).round(4).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=["ets", "arima", "prophet"],
                        choices=["ets", "arima", "prophet"])
    run(parser.parse_args().models)
