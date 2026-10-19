import unittest
import numpy as np
import pandas as pd
from src.explore_wastewater_lead import lag_correlations


class LeadTests(unittest.TestCase):
    def test_positive_lag_means_wastewater_earlier(self):
        x = pd.Series(np.random.default_rng(437).normal(size=60),
                      index=pd.date_range('2024-01-07', periods=60, freq='W-SUN'))
        frame = pd.DataFrame({'wastewater': x, 'ili_plus_a': x.shift(2)})
        for difference in [False, True]:
            rows = lag_correlations(frame, difference)
            self.assertEqual(max(rows, key=lambda r:r[1])[0], 2)
            self.assertEqual(len({r[2] for r in rows}), 1)
        frame.iloc[20, 0] = np.nan
        frame.iloc[25, 1] = np.nan
        rows = lag_correlations(frame)
        self.assertEqual(max(rows, key=lambda r:r[1])[0], 2)
        self.assertEqual(len({r[2] for r in rows}), 1)


if __name__ == '__main__':
    unittest.main()
