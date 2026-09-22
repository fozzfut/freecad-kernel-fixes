import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fcbench import stats  # noqa: E402


class StatsTest(unittest.TestCase):
    def test_summary_odd(self):
        s = stats.summary([5.0, 1.0, 3.0])
        self.assertEqual(s["median"], 3.0)
        self.assertEqual(s["min"], 1.0)
        self.assertEqual(s["max"], 5.0)
        self.assertEqual(s["n"], 3)

    def test_summary_even_is_true_median(self):
        # final review m3: with 2 reps the upper median s[n//2] was the slower rep; the median of an even count is the
        # mean of the two middle values
        self.assertEqual(stats.summary([50.0, 54.0])["median"], 52.0)
        self.assertEqual(stats.summary([4.0, 1.0, 3.0, 2.0])["median"], 2.5)

    def test_summary_p90(self):
        s = stats.summary(list(range(1, 11)))
        self.assertEqual(s["p90"], 10)
        self.assertEqual(s["median"], 5.5)

    def test_summary_empty(self):
        self.assertIsNone(stats.summary([]))

    def test_geomean(self):
        self.assertAlmostEqual(stats.geomean([1.0, 100.0]), 10.0)
        self.assertAlmostEqual(stats.geomean([10.0]), 10.0)

    def test_ratio_zero_cases(self):
        # final review m4: 0/0 is "the same" (1.0); a zero on one side has no finite speed-up ratio (None), and the
        # report counts it as skipped instead of letting geomean drop it silently
        self.assertEqual(stats.ratio(0.0, 0.0), 1.0)
        self.assertEqual(stats.ratio(10.0, 5.0), 2.0)
        self.assertIsNone(stats.ratio(0.0, 5.0))
        self.assertIsNone(stats.ratio(5.0, 0.0))


if __name__ == "__main__":
    unittest.main()
