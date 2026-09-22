import json
import os
import subprocess
import sys
import tempfile
import unittest

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BENCH)
import report  # noqa: E402

MD5 = {"TKMesh.dll": "m0", "TKBO.dll": "b0"}


def _run(root, tag, variant, file_label, open_s, orbit_ms, errors=None, profile="fc", actions=None, env=None,
         file_md5="f0", raw=None):
    """A runs/<tag>/result.json as the driver writes it (only the fields the report reads)."""
    d = os.path.join(root, tag)
    os.makedirs(d)
    p = os.path.join(d, "result.json")
    if raw is not None:                    # a result.json cut short (a run killed while writing it)
        with open(p, "w", encoding="utf-8") as f:
            f.write(raw)
        return
    acts = {"open": {"open_s": open_s}, "orbit": {"overview": {"median": orbit_ms}}}
    acts.update(actions or {})
    r = {"variant": variant, "profile": profile, "file_label": file_label, "actions": acts,
         "errors": errors or {}, "file_md5": file_md5,
         "env": env if env is not None else {"freecad": "1.1.1", "md5": dict(MD5), "gl": {"renderer": "RTX"},
                                              "hd": None}}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(r, f)


def _md(root, series, base, variant):
    ok, bad = report.collect(root, series, (base, variant))
    return report.table(ok, bad, base, variant)


class ReportTest(unittest.TestCase):
    def test_ratio_and_geomean(self):
        with tempfile.TemporaryDirectory() as root:
            _run(root, "s1-stock-vr6-fc-r1", "stock", "vr6", 50.0, 40.0)
            _run(root, "s1-stock-vr6-fc-r2", "stock", "vr6", 54.0, 44.0)
            _run(root, "s1-p012-vr6-fc-r1", "p012", "vr6", 5.0, 4.0)
            _run(root, "s1-p012-vr6-fc-r2", "p012", "vr6", 5.4, 4.4)
            ok, bad = report.collect(root, "s1", ("stock", "p012"))
            self.assertEqual(len(ok), 4)
            self.assertEqual(bad, [])
            md = report.table(ok, bad, "stock", "p012")
            # true median (final review m3): [50, 54] -> 52, [5.0, 5.4] -> 5.2, so 10.00x; n = reps per side
            self.assertIn("| vr6 | fc | open.open_s | 52 | 2 | 5.2 | 2 | 10.00× |  |", md)
            self.assertIn("| vr6 | fc | orbit.overview.median | 42 | 2 | 4.2 | 2 | 10.00× |  |", md)
            self.assertIn("геосреднее ускорения по 2 метрикам: 10.00× (пропущено 0 из 2)", md)

    def test_series_debug_and_errored_runs_stay_out_of_the_medians(self):
        # final review C1: every runs/*/result.json went into the medians - debug runs (smoke-*, t3-*), runs of an
        # earlier series and runs with errors
        with tempfile.TemporaryDirectory() as root:
            _run(root, "s1-stock-vr6-fc-r1", "stock", "vr6", 50.0, 40.0)
            _run(root, "s1-stock-vr6-fc-r2", "stock", "vr6", 999.0, 999.0,
                 errors={"save": "Traceback (most recent call last):\nOSError: disk | full\n"})
            _run(root, "smoke-fc", "stock", "vr6", 1.0, 1.0)
            _run(root, "t3-holes", "stock", "vr6", 1.0, 1.0)
            _run(root, "s2-stock-vr6-fc-r1", "stock", "vr6", 1.0, 1.0)
            _run(root, "stock-vr6-fc-r1", "stock", "vr6", 1.0, 1.0)          # the unprefixed baseline series
            _run(root, "s1-p012-vr6-fc-r1", "p012", "vr6", 5.0, 4.0)
            ok, bad = report.collect(root, "s1", ("stock", "p012"))
            self.assertEqual(sorted(r["tag"] for r in ok), ["s1-p012-vr6-fc-r1", "s1-stock-vr6-fc-r1"])
            self.assertEqual([b["tag"] for b in bad], ["s1-stock-vr6-fc-r2"])
            md = report.table(ok, bad, "stock", "p012")
            self.assertIn("| vr6 | fc | open.open_s | 50 | 1 | 5 | 1 | 10.00× |  |", md)
            self.assertIn("| s1-stock-vr6-fc-r2 | stock | vr6 | fc | errors.save: OSError: disk / full |", md)
            # the baseline series of 22.09 has no series prefix in its tags; it is addressed as series "baseline"
            ok, bad = report.collect(root, "baseline", ("stock",))
            self.assertEqual([r["tag"] for r in ok], ["stock-vr6-fc-r1"])

    def test_metric_missing_on_one_side_is_a_row_with_the_error(self):
        # final review C2 / ruling: a metric present on one side and missing on the other is an explicit row
        # "нет данных у <variant>" with that run's error line, and the geomean says how many metrics it skipped
        with tempfile.TemporaryDirectory() as root:
            _run(root, "s1-stock-vr6-fc-r1", "stock", "vr6", 50.0, 40.0, actions={"save": {"save_s": 2.0}})
            _run(root, "s1-p012-vr6-fc-r1", "p012", "vr6", 5.0, 4.0,
                 errors={"edit_cut": "Traceback (most recent call last):\n  File x\nRuntimeError: BOP failed\n"})
            _run(root, "s1-stock-oring-fc-r1", "stock", "oring", 1.0, 4.0, actions={"save": {"save_s": 0.02}})
            _run(root, "s1-p012-oring-fc-r1", "p012", "oring", 0.5, 2.0)     # counted, but save was not run
            ok, bad = report.collect(root, "s1", ("stock", "p012"))
            md = report.table(ok, bad, "stock", "p012")
            self.assertIn("| vr6 | fc | open.open_s | 50 | 1 | — | 0 | — | нет данных у p012: s1-p012-vr6-fc-r1 "
                          "errors.edit_cut: RuntimeError: BOP failed |", md)
            self.assertIn("| vr6 | fc | save.save_s | 2 | 1 | — | 0 | — | нет данных у p012:", md)
            self.assertIn("| oring | fc | save.save_s | 0.02 | 1 | — | 0 | — | нет данных у p012: в зачётных "
                          "прогонах метрики нет |", md)
            self.assertIn("| oring | fc | open.open_s | 1 | 1 | 0.5 | 1 | 2.00× |  |", md)
            self.assertIn("геосреднее ускорения по 2 метрикам: 2.00× (пропущено 4 из 6: нет данных у одной "
                          "стороны — 4)", md)

    def test_both_sides_without_counted_runs(self):
        with tempfile.TemporaryDirectory() as root:
            _run(root, "s1-stock-vr6-fc-r1", "stock", "vr6", 50.0, 40.0, errors={"hover_heavy": "grid hit no part"})
            os.makedirs(os.path.join(root, "s1-p012-vr6-fc-r1"))
            open(os.path.join(root, "s1-p012-vr6-fc-r1", "SKIP-lowmem"), "w").close()
            ok, bad = report.collect(root, "s1", ("stock", "p012"))
            md = report.table(ok, bad, "stock", "p012")
            self.assertIn("| vr6 | fc | — | — | 0 | — | 0 | — | нет данных ни у stock, ни у p012 |", md)
            self.assertIn("| s1-p012-vr6-fc-r1 | p012 | vr6 | fc | SKIP-lowmem |", md)
            self.assertIn("геосреднее: нет ни одной метрики с данными у обеих сторон", md)

    def test_ratio_two_decimals_and_regression_mark(self):
        # final review I1: "%.1f" printed 0.96 and 1.04 both as 1.0x
        with tempfile.TemporaryDirectory() as root:
            _run(root, "s1-stock-vr6-fc-r1", "stock", "vr6", 104.0, 100.0)
            _run(root, "s1-p012-vr6-fc-r1", "p012", "vr6", 100.0, 104.0)
            md = _md(root, "s1", "stock", "p012")
            self.assertIn("| vr6 | fc | open.open_s | 104 | 1 | 100 | 1 | 1.04× |  |", md)
            self.assertIn("| vr6 | fc | orbit.overview.median | 100 | 1 | 104 | 1 | 0.96× | медленнее: регрессия |", md)

    def test_zero_values(self):
        # final review m4: 0/0 is 1.00x and counts; a zero on one side is shown and counted as skipped
        with tempfile.TemporaryDirectory() as root:
            _run(root, "s1-stock-oring-hd-r1", "stock", "oring", 0.0, 0.0, profile="hd")
            _run(root, "s1-p012-oring-hd-r1", "p012", "oring", 0.0, 5.0, profile="hd")
            md = _md(root, "s1", "stock", "p012")
            self.assertIn("| oring | hd | open.open_s | 0 | 1 | 0 | 1 | 1.00× |  |", md)
            self.assertIn("| oring | hd | orbit.overview.median | 0 | 1 | 5 | 1 | — | ноль на одной стороне: "
                          "отношения нет |", md)
            self.assertIn("геосреднее ускорения по 1 метрикам: 1.00× (пропущено 1 из 2: ноль на одной стороне — 1)", md)

    def test_heavy_hover_with_few_points_is_flagged(self):
        # final review I4: hover.heavy rested on 1-2 grid points and the report never showed it
        with tempfile.TemporaryDirectory() as root:
            _run(root, "s1-stock-vr6-fc-r1", "stock", "vr6", 50.0, 40.0,
                 actions={"hover": {"heavy": {"median": 120.0, "n": 2}, "heavy_triangles": 64878}})
            _run(root, "s1-p012-vr6-fc-r1", "p012", "vr6", 5.0, 4.0,
                 actions={"hover": {"heavy": {"median": 12.0, "n": 11}, "heavy_triangles": 64878}})
            md = _md(root, "s1", "stock", "p012")
            self.assertIn("| vr6 | fc | hover.heavy.median | 120 | 1 | 12 | 1 | 10.00× | мало точек на тяжёлой детали "
                          "(n < 5): s1-stock-vr6-fc-r1 n=2 |", md)

    def test_same_thing_guard(self):
        # final review I2: validity, triangle counts, saved bytes, the opened file and HD's commit are compared;
        # DLL md5s are expected to differ between stock and a patch - listed, not a warning
        with tempfile.TemporaryDirectory() as root:
            env_b = {"freecad": "1.1.1", "md5": dict(MD5), "gl": {"renderer": "RTX"}, "hd": {"commit": "aaa"}}
            env_v = {"freecad": "1.1.1", "md5": dict(MD5, **{"TKMesh.dll": "m1"}), "gl": {"renderer": "RTX"},
                     "hd": {"commit": "bbb"}}
            _run(root, "s1-stock-vr6-hd-r1", "stock", "vr6", 50.0, 40.0, profile="hd", env=env_b,
                 actions={"edit_cut": {"edit": {"median": 2000.0}, "cut_valid": True},
                          "hover": {"heavy_triangles": 64878, "heavy_object": "F13"},
                          "save": {"save_s": 2.0, "bytes": 3148728}})
            _run(root, "s1-p012-vr6-hd-r1", "p012", "vr6", 5.0, 4.0, profile="hd", env=env_v, file_md5="f1",
                 actions={"edit_cut": {"edit": {"median": 200.0}, "cut_valid": False},
                          "hover": {"heavy_triangles": 60000, "heavy_object": "F13"},
                          "save": {"save_s": 0.2, "bytes": 2000000}})
            _run(root, "s1-stock-oring-fc-r1", "stock", "oring", 1.0, 4.0,
                 actions={"save": {"save_s": 0.02, "bytes": 28395}})
            _run(root, "s1-p012-oring-fc-r1", "p012", "oring", 0.5, 2.0,
                 actions={"save": {"save_s": 0.02, "bytes": 28093}})             # 1.1 %: the spread of one variant
            md = _md(root, "s1", "stock", "p012")
            self.assertIn("ВНИМАНИЕ vr6 hd: другой файл: md5 открытого файла stock f0, p012 f1", md)
            self.assertIn("ВНИМАНИЕ vr6 hd: другой коммит HD: stock aaa, p012 bbb", md)
            self.assertIn("ВНИМАНИЕ vr6 hd: edit_cut.cut_valid стало False: s1-p012-vr6-hd-r1", md)
            self.assertIn("ВНИМАНИЕ vr6 hd: hover.heavy_triangles: stock 64878, p012 60000", md)
            self.assertIn("ВНИМАНИЕ vr6 hd: save.bytes: stock 3148728, p012 2000000 (-36.5 %, допуск 2 %)", md)
            self.assertIn("vr6 hd: DLL различаются (ожидаемо у патча): TKMesh.dll stock m0, p012 m1", md)
            self.assertNotIn("ВНИМАНИЕ vr6 hd: DLL", md)
            self.assertNotIn("ВНИМАНИЕ oring", md)
            self.assertIn("Итог проверки: 5 предупреждений", md)

    def test_guard_same_gpu_with_slashes_is_no_warning(self):
        # the real GL renderer string has "/" in it (runs/stock-*: "NVIDIA GeForce RTX 3050 Laptop GPU/PCIe/SSE2")
        with tempfile.TemporaryDirectory() as root:
            env = {"freecad": "1.1.1", "md5": dict(MD5), "gl": {"renderer": "RTX 3050 Laptop GPU/PCIe/SSE2"}, "hd": None}
            _run(root, "s1-stock-vr6-fc-r1", "stock", "vr6", 50.0, 40.0, env=env)
            _run(root, "s1-p012-vr6-fc-r1", "p012", "vr6", 5.0, 4.0, env=dict(env))
            md = _md(root, "s1", "stock", "p012")
            self.assertIn("Итог проверки: всё то же", md)
            env2 = dict(env, gl={"renderer": "Intel UHD/PCIe"})
            _run(root, "s1-p012-vr6-fc-r2", "p012", "vr6", 5.0, 4.0, env=env2)
            md = _md(root, "s1", "stock", "p012")
            self.assertIn("ВНИМАНИЕ vr6 fc: GPU: stock RTX 3050 Laptop GPU/PCIe/SSE2, p012 Intel UHD/PCIe | "
                          "RTX 3050 Laptop GPU/PCIe/SSE2", md)

    def test_guard_says_when_the_file_md5_was_not_recorded(self):
        with tempfile.TemporaryDirectory() as root:
            _run(root, "s1-stock-vr6-fc-r1", "stock", "vr6", 50.0, 40.0, file_md5=None)
            _run(root, "s1-p012-vr6-fc-r1", "p012", "vr6", 5.0, 4.0)
            md = _md(root, "s1", "stock", "p012")
            self.assertIn("ВНИМАНИЕ vr6 fc: md5 открытого файла не записан: s1-stock-vr6-fc-r1", md)

    def test_unreadable_result_json_is_a_failed_run_named_by_its_file(self):
        # final review I6: a result.json cut short crashed the loaders without naming the file
        with tempfile.TemporaryDirectory() as root:
            _run(root, "s1-stock-vr6-fc-r1", "stock", "vr6", 50.0, 40.0)
            _run(root, "s1-p012-vr6-fc-r1", "p012", "vr6", 0, 0, raw='{"variant": "p012", "act')
            ok, bad = report.collect(root, "s1", ("stock", "p012"))
            self.assertEqual([b["tag"] for b in bad], ["s1-p012-vr6-fc-r1"])
            md = report.table(ok, bad, "stock", "p012")
            self.assertIn("result.json не читается (%s" % os.path.join(root, "s1-p012-vr6-fc-r1", "result.json"), md)

    def test_cli_pipe_and_new_out_dir(self):
        # Callers capture stdout through a pipe, which on this Windows machine is cp1251 (no "×"),
        # and write into bench/reports/, which does not exist before the first report.
        with tempfile.TemporaryDirectory() as root:
            _run(root, "s1-stock-vr6-fc-r1", "stock", "vr6", 50.0, 40.0)
            _run(root, "s1-p012-vr6-fc-r1", "p012", "vr6", 5.0, 4.0)
            out = os.path.join(root, "reports", "t.md")
            env = dict(os.environ, PYTHONIOENCODING="cp1251")
            p = subprocess.run([sys.executable, os.path.join(BENCH, "report.py"), root, "s1", "stock", "p012", out],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=60)
            self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
            self.assertIn("| vr6 | fc | open.open_s | 50 | 1 | 5 | 1 | 10.00× |  |", p.stdout.decode("utf-8"))
            with open(out, encoding="utf-8") as f:
                self.assertIn("геосреднее ускорения по 2 метрикам: 10.00×", f.read())

    def test_baseline_tables_name_an_unreadable_file(self):
        with tempfile.TemporaryDirectory() as root:
            _run(root, "stock-vr6-fc-r1", "stock", "vr6", 50.0, 40.0)
            _run(root, "stock-vr6-fc-r2", "stock", "vr6", 0, 0, raw="{")
            p = subprocess.run([sys.executable, os.path.join(BENCH, "tools", "baseline.py"), root, "stock"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
            text = p.stdout.decode("utf-8")
            self.assertIn("| vr6 | open.open_s | 50 с | 50–50 | 1 |", text)
            self.assertIn("- stock-vr6-fc-r2 — result.json не читается (%s" % os.path.join(
                root, "stock-vr6-fc-r2", "result.json"), text)


if __name__ == "__main__":
    unittest.main()
