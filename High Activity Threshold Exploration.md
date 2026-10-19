# High Activity Threshold Exploration

Status: exploratory proposal for team discussion. No second threshold has been adopted, and the shared config is unchanged.

## Purpose

The existing onset threshold (0.02821210456715307) describes an early rise above low off-season activity. A separate high-activity threshold could describe a higher level of influenza activity for preparedness discussions. Neither threshold establishes when hospitals should add beds or staff.

## Why consider the 75th percentile?

The proposed rule is to classify the upper quarter of historical in-season ILI+ observations as high activity. The 75th percentile is an interpretable starting point, not an industry standard for ILI+ and not a proven optimal cutoff.

The median would classify roughly half the reference weeks as high activity. A 90th-percentile rule would retain only the most extreme tenth. The 75th percentile is a practical intermediate choice worth exploring; these considerations do not establish that it is better than the 70th or 80th percentile. A higher threshold can produce fewer and later observed signals, but actual timing must be checked.

The percentile choice is a research judgment. The numeric threshold obtained after making that choice is a data calculation. Stability across reference periods is useful evidence about sensitivity, not proof of operational validity.

## Reference data and calculation

- Source: `data/processed/ili_plus_weekly.csv`, national rows, observed ILI+.
- Units: weighted ILI percentage multiplied by flu-positive fraction (`wili * pct_positive / 100`); no additional division by 100.
- Only observations before `TEST_START` (2025-09-28) are used.
- Primary reference: the three most recent complete non-COVID seasons, 2022–23, 2023–24, and 2024–25.
- In-season weeks: MMWR 40–20, matching the shared evaluation window. Each selected season has 33 weeks, for 99 observations.
- Unlike the onset calculation, which uses off-season weeks 21–39, this calculation uses in-season activity to define relatively high levels.
- Pool the 99 weekly values and calculate pandas' linearly interpolated quantile. For sorted values and zero-based rank, the interpolation location is `(n - 1) * q`; at n=99 and q=0.75, it is 73.5, halfway between the 74th and 75th sorted observations.
- Comparison reference: all available pre-test in-season observations outside the configured COVID window (264 weeks). The pandemic-truncated 2019–20 season and irregular 2021–22 season remain included under this rule, so this is a sensitivity comparison rather than a claim that all included seasons were typical.

## Calculated candidates

| Percentile | Recent three seasons, n=99 | All pre-test non-COVID weeks, n=264 | Recent-reference weeks above |
| --- | ---: | ---: | ---: |
| 70th | 0.662468 | 0.547978 | 30 |
| 75th | 0.693858 | 0.678840 | 25 |
| 80th | 0.791493 | 0.839342 | 20 |

The two 75th-percentile estimates are close (approximately 0.69 and 0.68). This supports describing 0.69 as a candidate that is relatively stable across these two reference choices, not as a validated cutoff. The full-precision values are saved in the accompanying CSV; calculations below use those values, not rounded 0.69.

## Season-level sensitivity

Number of weeks strictly above each threshold, out of 33 in each season:

| Candidate | 2022–23 | 2023–24 | 2024–25 | Total |
| --- | ---: | ---: | ---: | ---: |
| 0.5 comparison | 9 | 13 | 13 | 35 |
| 70th percentile | 9 | 9 | 12 | 30 |
| 75th percentile | 8 | 6 | 11 | 25 |
| 80th percentile | 8 | 2 | 10 | 20 |

Under the 75th-percentile candidate:

| Season | First observed week above | In-window peak week | Gap to peak |
| --- | --- | --- | ---: |
| 2022–23 | 2022-11-06 | 2022-11-20 | 2 weeks |
| 2023–24 | 2023-12-10 | 2023-12-24 | 2 weeks |
| 2024–25 | 2024-12-15 | 2025-01-26 | 6 weeks |

The 80th-percentile choice reduces 2023–24 exceedance weeks from six to two and shifts its first exceedance one week later. Therefore the candidates are not interchangeable. The 0.5 proposal identifies a broader period of elevated activity; it is not inherently incorrect.

These are retrospective descriptions using the same seasons that define the thresholds. They are not forecast accuracy results, independent validation, or demonstrated advance warning. Peak dates are only known retrospectively and are restricted to weeks 40–20. Total weeks above need not form one uninterrupted run. First exceedance here is a single observed week, not the two-consecutive-week onset rule.

## Decisions still needed

1. Agree whether high activity means a relative historical level or an operational demand threshold. These calculations support only the former.
2. Agree on the reference period and percentile before evaluating the held-out season. Do not choose the threshold to make test results look better.
3. Define the forecast event: being above the threshold within the next 1–4 weeks differs from a new upward crossing. Specify how already-above observations are handled and whether persistence is required.
4. If adopted, store the selected full-precision threshold separately from the onset threshold and record the source-data version. Historical data revisions can change quantiles.

Suggested interpretation: “An exploratory high-activity level defined relative to historical in-season ILI+.” Avoid presenting it as an official CDC ILI+ category or a validated hospital-capacity trigger. CDC's published activity-level methodology concerns ILI and uses a different calculation: https://www.cdc.gov/fluview/overview/.

## Reproduce

From the repository root, run:

```sh
python -m src.explore_high_activity_threshold
```

The script reads the shared data and date settings, selects complete recent seasons, checks for missing ILI+ and duplicate weeks in the analysis data, and writes:

- `results/high_activity_candidates.csv`: quantiles, reference sample sizes, and exceedance counts.
- `results/high_activity_season_diagnostics.csv`: season-level counts, first exceedance dates, peak dates, and descriptive gaps.

It does not use test-period values or update shared settings. The tables in this document reflect the checked-in data at the time of this exploration; rerun and update the document if the source data changes.
