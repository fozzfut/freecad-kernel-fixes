"""Tables of one variant's matrix series (run_matrix.sh): per file, profile and metric the median over the reps,
min-max over the reps, n, and a "шумная" mark when max/min > 1.5; then one row per run (cpu load, peak memory) and the
environment the runs recorded. Only the COUNTED runs of the series are used - report.collect: tag
<series>-<variant>-<label>-<profile>-r<k> (series "baseline", the default, is the stock series of 22.09 whose tags have
no series prefix) and a result.json with an empty errors object (ruling of 22.09); the others are listed with the
reason, a result.json that cannot be read by its path.

    python tools/baseline.py <runs_dir> <variant> [series] > part.md
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import report  # noqa: E402
from fcbench import stats  # noqa: E402

LABELS = ["vr6cur", "vr6", "oring", "s1000", "s5000", "holes"]
# report.METRICS (what later comparisons use) plus the parts that say where the time goes
EXTRA = [
    ("open", ("second_frame_ms",)), ("open", ("mem", "peak_ws_mb")),
    ("orbit", ("overview", "p90")), ("orbit", ("closeup", "p90")),
    ("hover", ("heavy", "max")), ("hover", ("heavy_triangles",)),
    ("edit_body", ("recompute", "median")), ("edit_body", ("idle", "median")), ("edit_body", ("frame", "median")),
    ("edit_body", ("hd_refine_after", "wait_s")),
    ("edit_cut", ("recompute", "median")), ("edit_cut", ("idle", "median")), ("edit_cut", ("frame", "median")),
    ("edit_cut", ("hd_refine_after", "wait_s")),
    ("fillet_holes", ("recompute", "median")), ("fillet_holes", ("idle", "median")),
    ("fillet_holes", ("frame", "median")), ("fillet_holes", ("hd_refine_after", "wait_s")),
]


def unit(path):
    last = path[-1] if path[-1] not in ("median", "p90", "max", "min", "wait_s") else path[-2]
    if path[-1] == "wait_s" or last.endswith("_s"):
        return "с"
    if last.endswith("_mb"):
        return "МБ"
    if last == "heavy_triangles":
        return "шт"
    return "мс"


def fmt(x):
    return "%d" % round(x) if abs(x) >= 10000 else "%.4g" % x


ACTIONS = ["open", "orbit", "hover", "select", "edit_body", "edit_cut", "fillet_holes", "save"]


def order(runs):
    """report.METRICS and EXTRA, grouped by action in the order the driver runs them."""
    ms = report.METRICS + EXTRA
    return sorted(ms, key=lambda m: (ACTIONS.index(m[0]), ms.index(m)))


def main():
    root, variant = sys.argv[1], sys.argv[2]
    series = sys.argv[3] if len(sys.argv) > 3 else report.LEGACY_SERIES
    # the counted runs of the series and the others with the reason (report.collect: one rule for both tools; a
    # result.json that cannot be read is named and listed, final review I6)
    ok, uncounted = report.collect(root, series, (variant,))
    bad = [(b["tag"], "ошибки: " + ", ".join(b["errors"]) if b["kind"] == "ошибки" else b["reason"],
            b["file_label"], b["profile"]) for b in uncounted]
    out = []
    noisy = []
    heads = {"fc": "### Профиль fc — FreeCAD без дополнений (по нему судятся патчи ядра)",
             "hd": "### Профиль hd — FreeCAD + HybridDesign (что владелец чувствует в работе)"}
    for prof in ("fc", "hd"):
        out.extend([heads[prof], "", "| файл | метрика | медиана | мин–макс по повторам | n | |", "|---|---|---|---|---|---|"])
        for fl in LABELS + sorted({r["file_label"] for r in ok} - set(LABELS)):
            rs = [r for r in ok if r["file_label"] == fl and r["profile"] == prof]
            if not rs:
                skipped = [t for t, why, bfl, bprof in bad if bfl == fl and bprof == prof]
                if skipped:
                    whys = sorted({why for t, why, _, _ in bad if t in skipped})
                    out.append("| %s | — | не измерено: %d из %d прогонов — %s | | 0 | |" % (
                        fl, len(skipped), len(skipped), ", ".join(whys)))
                continue
            for action, path in order(rs):
                xs = [report._get(r["actions"].get(action, {}), path) for r in rs]
                xs = [x for x in xs if x is not None]
                s = stats.summary(xs)
                if not s:
                    continue
                name = action + "." + ".".join(path)
                mark = ""
                if s["n"] > 1 and s["min"] > 0 and s["max"] / s["min"] > 1.5:
                    mark = "шумная (%.1f×)" % (s["max"] / s["min"])
                    noisy.append((fl, prof, name, s["max"] / s["min"],
                                  [r.get("cpu_load_pct") for r in rs]))
                out.append("| %s | %s | %s %s | %s–%s | %d | %s |" % (
                    fl, name, fmt(s["median"]), unit(path), fmt(s["min"]), fmt(s["max"]), s["n"], mark))
        out.append("")
    out.append("")
    out.append("Прогоны серии (зачётные):")
    out.append("")
    out.append("| прогон | загрузка машины, % | пиковый рабочий набор за прогон, МБ | воркеры HD | HD доводка open, с |")
    out.append("|---|---|---|---|---|")
    for r in ok:
        o = r["actions"].get("open", {})
        out.append("| %s | %s | %s | %s | %s |" % (
            r["tag"], r.get("cpu_load_pct"), (r.get("mem_end") or {}).get("peak_ws_mb"),
            o.get("hd_workers", "-"), o.get("hd_refine_s", "-")))
    loads = [r.get("cpu_load_pct") for r in ok if r.get("cpu_load_pct") is not None]
    out.append("")
    if loads:
        out.append("Загрузка машины по зачётным прогонам: %.1f–%.1f %% (медиана %.1f %%)." % (
            min(loads), max(loads), stats.summary(loads)["median"]))
    if bad:
        out.append("")
        out.append("Незачётные прогоны (в медианы не вошли):")
        out.append("")
        for tag, why, _, _ in bad:
            out.append("- %s — %s" % (tag, why))
    envs = {}
    for r in ok:
        e = r.get("env", {})
        key = json.dumps({"freecad": e.get("freecad"), "md5": e.get("md5"), "gl": e.get("gl"),
                          "hd": (e.get("hd") or {}).get("commit") if r["profile"] == "hd" else None},
                         sort_keys=True)
        envs.setdefault(key, []).append(r["tag"])
    out.append("")
    out.append("Окружение (как записали прогоны, `env` в result.json):")
    out.append("")
    for key, tags in envs.items():
        out.append("- %d прогонов: `%s`" % (len(tags), key))
    print("\n".join(out))
    name = "baseline-%s.json" % variant if series == report.LEGACY_SERIES else "baseline-%s-%s.json" % (series, variant)
    with open(os.path.join(root, name), "w", encoding="utf-8") as f:
        json.dump({"noisy": noisy, "ok": [r["tag"] for r in ok], "bad": [b[:2] for b in bad]}, f, indent=1)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
