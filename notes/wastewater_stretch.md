# Wastewater stretch: reporting coverage and influenza-A comparison

The follow-up [lead-time exploration](wastewater_lead_exploration.md) compares seasonal timing and ±4-week correlations using these prepared inputs.

## Purpose and decisions

The review comments identify two valid comparability problems: incomplete reporting can distort weekly medians, and influenza-A wastewater should be compared with an influenza-A clinical proxy. This update prepares those inputs; it does not establish a wastewater lead time or change the forecasting target or thresholds.

### Reporting coverage

Use the median site count of the preceding eight calendar weeks, separately for the national aggregate and each state/territory. Retain the current week if its count is at least 50% of that reference. Require at least four prior weeks with positive reporting counts; otherwise label it `insufficient_history`. Missing calendar weeks contribute zero to the reference. The current and future weeks do not enter their own reference.

This follows the proposed 50% screen but makes “typical” explicit and local. A single national cutoff would exclude small states; a full-history median would mix early network rollout with today's coverage. Eight weeks is a project judgment, not a CDC standard. A long sustained reporting decline can eventually lower this rolling reference, and passing it does not prove population representativeness or stable site composition. Small states can pass with few sites: always display `n_sites` and do not interpret this as a minimum-sample reliability certification.

Original aggregate files remain intact. Use the following files for the stretch chart/map:

- `data/processed/nwss_flu_a_weekly_filtered.csv`
- `data/processed/nwss_flu_a_state_weekly_filtered.csv`

The corresponding `*_coverage.csv` files retain all original rows plus `typical_n_sites`, `site_count_ratio`, and `coverage_status`. They document excluded rows. A week with no reported row is missing, not zero viral activity.

**Map integration:** choose one explicit calendar week. For that week, join the filtered data to the full geography list and show excluded or absent states as “insufficient/no data.” Never fall back to each state's last available week: that would mix dates and hide the coverage problem. A recent week passing the filter is still provisional. Do not label the site-standardized values as official CDC activity categories.

**Lead-time integration:** retain a regular Sunday calendar when joining wastewater and national `ili_plus_a`; exclude missing pairs separately at each lag. Do not drop missing weeks and shift by row position, which would treat separated weeks as adjacent. Correlation between seasonal curves alone is not evidence of usable real-time advance warning; reporting delays, retrospective revisions, and full-history site standardization remain limitations.

### Influenza-A ILI+

Delphi defines `percent_a` as the percentage of specimens positive for influenza A (not A's share among positive tests). Therefore:

`ili_plus_a = wili * percent_a / 100`

The new `data/processed/ili_plus_a_weekly.csv` contains national and HHS Region 9 series. It does not replace `ili_plus_weekly.csv`. The augmentation mode reuses its stored `wili`, checks the newly obtained total positivity against the stored total positivity, and rejects missing, duplicate, revised, or invalid clinical values rather than silently mixing them. Matching total positivity is a consistency check, not proof of identical historical release vintages.

Influenza-A alignment improves target comparability, but wastewater is not the same population measurement as outpatient visits and may include nonhuman influenza-A contributions. The existing 0.0282/0.6939 thresholds were calibrated for total ILI+, not this new series, and must not be transferred automatically.

## Results on the current snapshot

- National coverage: 261 of 266 rows retained; four initial weeks lack reference history and one week has low reporting.
- October 11, 2026: 82 sites versus a prior-eight-week median of 953.5 (8.6%); excluded. October 4 passes at 762/1003.5 (75.9%).
- State coverage: 9,432 of 9,807 rows retained; 228 insufficient-history and 147 low-count rows.
- On October 11, only 26 states/territories have rows; three pass and 23 fail. Other geographies have no current row and must also appear as unavailable on a map.
- Influenza-A ILI+: 523 weeks per region, October 2, 2016 through October 4, 2026 (1,046 rows total).
- The existing total-ILI+ and unfiltered wastewater files are unchanged.

## Reproduce

```sh
python src/clean.py --coverage-only
python src/fetch_ili_plus.py --flu-a-only
python -m unittest discover -s tests -p 'test_wastewater_stretch.py'
```

The coverage-only command uses checked-in aggregates and requires no 141 MB raw download. A full `python src/clean.py` rebuild also produces coverage outputs when the raw source is available. A saved Delphi response can be used with `--clinical-json PATH` for offline reproduction. A full fetch produces both total and A-only ILI+; use `--flu-a-only` to leave the shared total target unchanged.

Validation used the checked-in aggregates and a Delphi clinical response retrieved October 19, 2026. The raw site-level cleaning pipeline was not rerun. Focused tests cover cutoff equality, geography-specific references, calendar gaps, no future dependence, type-A units, and missing/revised/invalid positivity rejection.

Sources:

- [Delphi clinical API: percent_a definition](https://cmu-delphi.github.io/delphi-epidata/api/fluview_clinical.html)
- [CDC national wastewater data and reporting limitations](https://www.cdc.gov/wastewater/respiratory-viruses/national.html)
