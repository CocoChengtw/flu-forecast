"""Boundary checks for reporting coverage and type-A target alignment."""
import unittest

import numpy as np
import pandas as pd

from src.clean import filter_reporting_coverage
from src.fetch_ili_plus import build_flu_a


class WastewaterTests(unittest.TestCase):
    def frame(self, counts):
        return pd.DataFrame({'week_start': pd.date_range('2024-01-07', periods=len(counts), freq='W-SUN'),
                             'n_sites': counts})

    def test_threshold_and_warmup(self):
        _, audit = filter_reporting_coverage(self.frame([100]*8 + [50, 49]))
        self.assertTrue(audit.coverage_status.iloc[:4].eq('insufficient_history').all())
        self.assertEqual(audit.coverage_status.iloc[8], 'pass')
        self.assertEqual(audit.coverage_status.iloc[9], 'low_site_count')

    def test_future_counts_do_not_change_past(self):
        f = self.frame([100]*8 + [10, 20])
        _, before = filter_reporting_coverage(f)
        f.loc[9, 'n_sites'] = 10000
        _, after = filter_reporting_coverage(f)
        pd.testing.assert_frame_equal(before.iloc[:9], after.iloc[:9])

    def test_local_reference_and_gap(self):
        large = self.frame([100]*8 + [40]).assign(state='CA')
        small = self.frame([4]*8 + [3]).assign(state='VT')
        _, audit = filter_reporting_coverage(pd.concat([large, small]), ('state',))
        last = audit.groupby('state').tail(1).set_index('state')
        self.assertEqual(last.loc['CA', 'coverage_status'], 'low_site_count')
        self.assertEqual(last.loc['VT', 'coverage_status'], 'pass')
        # A long reporting gap must not reuse arbitrarily old rows as recent history.
        gap = pd.concat([self.frame([100]*8), pd.DataFrame({'week_start': [pd.Timestamp('2024-09-01')], 'n_sites': [100]})])
        _, audit = filter_reporting_coverage(gap)
        self.assertEqual(audit.iloc[-1].coverage_status, 'insufficient_history')

    def test_flu_a_units_and_revision_guard(self):
        existing = pd.DataFrame({'region':['nat'], 'epiweek':[202401], 'week_start':['2023-12-31'],
                                 'wili':[4.0], 'pct_positive':[20.0], 'ili_plus':[0.8]})
        lab = pd.DataFrame({'region':['nat'], 'epiweek':[202401], 'percent_positive':[20.0], 'percent_a':[15.0]})
        output = build_flu_a(existing, lab)
        self.assertAlmostEqual(output.ili_plus_a.iloc[0], 0.6)
        self.assertEqual(existing.ili_plus.iloc[0], 0.8)
        lab.loc[0, 'percent_positive'] = 21
        with self.assertRaisesRegex(ValueError, 'revised'):
            build_flu_a(existing, lab)

    def test_missing_and_impossible_type_a(self):
        existing = pd.DataFrame({'region':['nat'], 'epiweek':[202401], 'week_start':['2023-12-31'],
                                 'wili':[4.0], 'pct_positive':[20.0]})
        for a in [np.nan, 21, -1]:
            lab = pd.DataFrame({'region':['nat'], 'epiweek':[202401], 'percent_positive':[20.0], 'percent_a':[a]})
            with self.assertRaises(ValueError):
                build_flu_a(existing, lab)


if __name__ == '__main__':
    unittest.main()
