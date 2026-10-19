"""
Shared project settings. Every script imports from here so the whole team
uses the same definitions:

    from src.config import TEST_START, TEST_END, N_PATHS

Dates are the Sunday that starts each CDC MMWR week (the week convention used
by ILINet and in data/processed/ili_plus_weekly.csv). "Week 40" means MMWR week 40.
"""

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

# Geography to forecast. "nat" = United States. "hhs9" (HHS Region 9, incl.
# California) is also in the data file but is a stretch goal.
REGION = "nat"

# First available week in the shared data: MMWR 2016 week 40 (2016-17 season).
TRAIN_START = "2016-10-02"

# ---------------------------------------------------------------------------
# Train / test split
# ---------------------------------------------------------------------------
# CDC's surveillance year runs from MMWR week 40 to week 39 of the next year.
# Flu activity is concentrated in weeks 40-20, so like other flu forecasting
# work we use weeks 40-20 of the most recent complete season (2025-26) as the
# test period. Every week in it is used as a forecast origin. Only data up to
# the origin is given to the model.

# MMWR 2025 week 40: first week of the 2025-26 season.
TEST_START = "2025-09-28"

# MMWR 2026 week 20: last week of the 2025-26 season. With a 4-week horizon,
# the last forecasts target 2026 week 24, which is already observed.
TEST_END = "2026-05-17"

# Test folds for robustness. The main results use 2025-26; 2024-25 is a second
# fold (trained only on data before it) to check that model rankings are not
# an artifact of a single season. Each fold: (first origin, last origin).
TEST_FOLDS = {
    "2025-26": (TEST_START, TEST_END),
    "2024-25": ("2024-09-29", "2025-05-11"),   # MMWR 2024 week 40 to 2025 week 20
}
MAIN_FOLD = "2025-26"

# ---------------------------------------------------------------------------
# COVID-19 disruption
# ---------------------------------------------------------------------------
# Distancing and masking almost eliminated flu during the 2020-21 season.
# Left as is, this flat year distorts the seasonality models learn. We replace
# ILI+ in this window with the same-week mean of non-COVID seasons and keep an
# `is_imputed` flag. The window covers the full 2020-21 surveillance year:
# from MMWR 2020 week 27 (after the cut-short 2019-20 season) through
# MMWR 2021 week 39 (just before the 2021-22 season starts). The 2021-22 season
# is kept as observed: it was irregular, but it really happened.

COVID_START = "2020-06-28"   # MMWR 2020 week 27
COVID_END = "2021-09-26"     # MMWR 2021 week 39

# ---------------------------------------------------------------------------
# Threshold (season onset)
# ---------------------------------------------------------------------------
# Adapted from CDC's ILINet baseline: the mean % of ILI visits during
# non-influenza weeks of the 3 most recent seasons, plus 2 SD. CDC defines
# non-influenza weeks with public-health-lab positive counts, which our data
# doesn't include, so we simplify: off-season = MMWR weeks 21-39 (June to
# September), when flu activity is minimal. Computed from the raw
# (non-imputed) ILI+, using the last 3 non-COVID seasons.

OFFSEASON_WEEKS = range(21, 40)   # MMWR weeks 21..39 inclusive
THRESHOLD_N_SEASONS = 3
THRESHOLD_N_SD = 2
# Fixed before TEST_START: pooled raw MMWR weeks 21-39 in 2023, 2024, 2025
# (offseasons of 2022-23, 2023-24, 2024-25); n=57; sample SD (ddof=1).
# mean=0.013459370553024562, SD=0.007376367007064253.
# Units match wili * pct_positive / 100 in the shared CSV; do NOT divide again.
# Research threshold, not an official CDC ILI+ baseline. Historical onsets
# often occur in October; value has not been tuned to force Nov-Dec onsets.
# Reproduce and inspect caveats: python -m src.audit_threshold
THRESHOLD = 0.02821210456715307

# Onset week = first of this many consecutive weeks above THRESHOLD.
ONSET_CONSECUTIVE_WEEKS = 2

# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------

# Forecast 1-4 weeks ahead: far enough to plan staffing, short enough to be useful.
HORIZONS = [1, 2, 3, 4]

# Simulated paths per origin. Probabilities (threshold crossing, onset, peak)
# are computed from these. 500 keeps them stable to about +/-2 percentage points.
N_PATHS = 500

# Fixed seed so every run produces the same paths.
RANDOM_SEED = 437
