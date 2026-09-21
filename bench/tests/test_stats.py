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

    def test_summary_p90(self):
        s = stats.summary(list(range(1, 11)))
        self.assertEqual(s["p90"], 10)
        self.assertEqual(s["median"], 6)

    def test_summary_empty(self):
        self.assertIsNone(stats.summary([]))

    def test_geomean(self):
        self.assertAlmostEqual(stats.geomean([1.0, 100.0]), 10.0)
        self.assertAlmostEqual(stats.geomean([10.0]), 10.0)


if __name__ == "__main__":
    unittest.main()
