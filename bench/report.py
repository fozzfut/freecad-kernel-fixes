"""Aggregate bench/runs/*/result.json into a markdown table: per file, profile and metric the median over
runs of each variant, the ratio base/variant and the geometric mean of the ratios.

    python report.py <runs_dir> <base_variant> <variant> [out.md]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fcbench import stats  # noqa: E402

# (action, path in the action dict) -> metric name. Lower is better for all of them.
METRICS = [
    ("open", ("open_s",)), ("open", ("idle_s",)), ("open", ("first_frame_ms",)),
    ("orbit", ("overview", "median")), ("orbit", ("closeup", "median")),
    ("hover", ("all", "median")), ("hover", ("all", "max")), ("hover", ("heavy", "median")),
    ("select", ("select", "median")),
    ("edit_body", ("edit", "median")), ("edit_cut", ("edit", "median")),
    ("fillet_holes", ("edit", "median")),
    ("save", ("save_s",)),
]


def load_runs(root):
    runs = []
    for tag in sorted(os.listdir(root)):
        p = os.path.join(root, tag, "result.json")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                r = json.load(f)
            r["tag"] = tag
            runs.append(r)
    return runs


def _get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d if isinstance(d, (int, float)) else None


def table(runs, base, variant):
    keys = sorted({(r["file_label"], r["profile"]) for r in runs})
    lines = ["| файл | профиль | метрика | %s | %s | × |" % (base, variant), "|---|---|---|---|---|---|"]
    ratios = []
    for fl, prof in keys:
        for action, path in METRICS:
            vals = {}
            for v in (base, variant):
                xs = [_get(r["actions"].get(action, {}), path) for r in runs
                      if r["variant"] == v and r["file_label"] == fl and r["profile"] == prof]
                s = stats.summary([x for x in xs if x is not None])
                vals[v] = s["median"] if s else None
            if vals[base] is None or vals[variant] is None:
                continue
            ratio = vals[base] / vals[variant] if vals[variant] > 0 else float("inf")
            ratios.append(ratio)
            name = action + "." + ".".join(path)
            lines.append("| %s | %s | %s | %g | %g | %.1f× |" % (fl, prof, name, vals[base], vals[variant], ratio))
    lines.append("")
    lines.append("геосреднее ускорения по %d метрикам: %.2f×" % (len(ratios), stats.geomean(ratios)))
    return "\n".join(lines)


def main():
    root, base, variant = sys.argv[1], sys.argv[2], sys.argv[3]
    md = table(load_runs(root), base, variant)
    if len(sys.argv) > 4:
        out = sys.argv[4]
        if os.path.dirname(out):
            os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(md + "\n")
    # A pipe on Windows defaults to the ANSI code page (cp1251 here), which has no "×": print UTF-8.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
