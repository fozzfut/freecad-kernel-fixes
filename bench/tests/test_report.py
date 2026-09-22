import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import report  # noqa: E402


def _run(root, tag, variant, file_label, open_s, orbit_ms, errors=None):
    d = os.path.join(root, tag)
    os.makedirs(d)
    r = {"variant": variant, "profile": "fc", "file_label": file_label,
         "actions": {"open": {"open_s": open_s}, "orbit": {"overview": {"median": orbit_ms}}}}
    if errors is not None:
        r["errors"] = errors
    with open(os.path.join(d, "result.json"), "w") as f:
        json.dump(r, f)


class ReportTest(unittest.TestCase):
    def test_ratio_and_geomean(self):
        with tempfile.TemporaryDirectory() as root:
            _run(root, "a1", "stock", "vr6", 50.0, 40.0)
            _run(root, "a2", "stock", "vr6", 54.0, 44.0)
            _run(root, "b1", "p012", "vr6", 5.0, 4.0)
            _run(root, "b2", "p012", "vr6", 5.4, 4.4)
            runs = report.load_runs(root)
            self.assertEqual(len(runs), 4)
            md = report.table(runs, "stock", "p012")
            # median rule s[len(s)//2]: [50, 54] -> 54, [5.0, 5.4] -> 5.4, so 10.0x; orbit 44 / 4.4 = 10.0x
            self.assertIn("| vr6 | fc | open.open_s | 54 | 5.4 | 10.0× |", md)
            self.assertIn("| vr6 | fc | orbit.overview.median | 44 | 4.4 | 10.0× |", md)
            self.assertIn("геосреднее ускорения по 2 метрикам: 10.00×", md)

    def test_run_errors_are_listed(self):
        # A metric the run could not take (errors.hover_heavy: the grid hit no part) and a failed action must be
        # visible under the table, not only inside result.json; a traceback is shown by its last line.
        with tempfile.TemporaryDirectory() as root:
            _run(root, "a1", "stock", "vr6", 50.0, 40.0, errors={})
            _run(root, "b1", "p012", "vr6", 5.0, 4.0,
                 errors={"hover_heavy": "the 144-point hover grid hit no part: there is no heavy part to time",
                         "save": "Traceback (most recent call last):\n  File x\nOSError: disk | full\n"})
            _run(root, "c1", "other", "vr6", 1.0, 1.0, errors={"open_hd_refine": "not ours"})
            md = report.table(report.load_runs(root), "stock", "p012")
            self.assertIn("| b1 | p012 | vr6 | fc | hover_heavy: the 144-point hover grid hit no part: there is no "
                          "heavy part to time |", md)
            self.assertIn("| b1 | p012 | vr6 | fc | save: OSError: disk / full |", md)
            self.assertNotIn("| a1 |", md)
            self.assertNotIn("not ours", md)

    def test_cli_pipe_and_new_out_dir(self):
        # Callers capture stdout through a pipe, which on this Windows machine is cp1251 (no "×"),
        # and write into bench/reports/, which does not exist before the first report.
        with tempfile.TemporaryDirectory() as root:
            _run(root, "a1", "stock", "vr6", 50.0, 40.0)
            _run(root, "b1", "p012", "vr6", 5.0, 4.0)
            out = os.path.join(root, "reports", "t.md")
            env = dict(os.environ, PYTHONIOENCODING="cp1251")
            script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "report.py")
            p = subprocess.run([sys.executable, script, root, "stock", "p012", out],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
            self.assertIn("| vr6 | fc | open.open_s | 50 | 5 | 10.0× |", p.stdout.decode("utf-8"))
            with open(out, encoding="utf-8") as f:
                self.assertIn("геосреднее ускорения по 2 метрикам: 10.00×", f.read())


if __name__ == "__main__":
    unittest.main()
