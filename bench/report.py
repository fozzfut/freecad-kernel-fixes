"""Compare two variants of one run series: per file, profile and metric the median over the variant's COUNTED runs,
n (runs with that metric), the ratio base/variant, and the geometric mean of the ratios; then the "same thing" guard
and the runs that did not count.

    python report.py <runs_dir> <series> <base_variant> <variant> [out.md]

Which runs count (final review C1, rulings of 22.09): only runs of the series - tags
<series>-<variant>-<label>-<fc|hd>-r<k> (run_matrix.sh), or <variant>-<label>-<fc|hd>-r<k> for the series "baseline"
(the stock baseline of 22.09, reports/BASELINE.md, made before tags had a series prefix) - whose result.json has an
empty errors object and a non-empty actions object. Debug runs (smoke-*, fix*-*, t3-*), other series and runs with
errors never enter a median; the uncounted runs of the two variants are listed with the reason.

A metric present on one side and missing on the other is a row "нет данных у <variant>" with the error lines of that
side's uncounted runs (ruling: a failed action after a patch must not look like a clean table); the geometric mean
says how many metrics it left out and why.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fcbench import stats  # noqa: E402

# (action, path in the action dict) -> metric name. Lower is better for all of them.
METRICS = [
    ("open", ("open_s",)), ("open", ("idle_s",)), ("open", ("hd_refine_s",)), ("open", ("first_frame_ms",)),
    ("orbit", ("overview", "median")), ("orbit", ("closeup", "median")),
    ("hover", ("all", "median")), ("hover", ("all", "max")), ("hover", ("heavy", "median")),
    ("select", ("select", "median")),
    ("edit_body", ("edit", "median")), ("edit_cut", ("edit", "median")),
    ("fillet_holes", ("edit", "median")),
    ("save", ("save_s",)),
]

LEGACY_SERIES = "baseline"      # the stock series of 22.09: tags without a series prefix
NAME = r"[A-Za-z0-9_]+"          # series, variant and file label (run_matrix.sh refuses anything else)
HEAVY_MIN_N = 5                  # final review I4: hover.heavy on fewer points is flagged
BYTES_TOL = 0.02                 # save.bytes of one variant spread 1.1 % over 3 reps (oring, stock baseline)


def tag_re(series, variant):
    """Tags of one variant's runs in a series; groups: label, profile, rep."""
    pre = "" if series == LEGACY_SERIES else re.escape(series) + "-"
    return re.compile(r"^%s%s-(%s)-(fc|hd)-r(\d+)$" % (pre, re.escape(variant), NAME))


def _last_line(text):
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    return (lines[-1] if lines else "")[:200].replace("|", "/")


def collect(root, series, variants):
    """(counted runs, uncounted runs) of the variants in the series. An uncounted run is a dict tag, variant,
    file_label, profile, kind (SKIP-lowmem | нет result.json | не читается | ошибки | нет действий | чужой вариант)
    and reason (one line for the report)."""
    ok, bad = [], []
    pats = [(v, tag_re(series, v)) for v in variants]
    for tag in sorted(os.listdir(root)):
        hit = next(((v, m) for v, m in ((v, p.match(tag)) for v, p in pats) if m), None)
        if not hit or not os.path.isdir(os.path.join(root, tag)):
            continue
        v, m = hit
        entry = {"tag": tag, "variant": v, "file_label": m.group(1), "profile": m.group(2)}
        p = os.path.join(root, tag, "result.json")
        if not os.path.isfile(p):
            kind = "SKIP-lowmem" if os.path.isfile(os.path.join(root, tag, "SKIP-lowmem")) else "нет result.json"
            bad.append(dict(entry, kind=kind, reason=kind))
            continue
        try:
            with open(p, encoding="utf-8") as f:
                r = json.load(f)
            if not isinstance(r, dict):
                raise ValueError("not a JSON object")
        except (OSError, ValueError) as e:
            bad.append(dict(entry, kind="не читается", reason="result.json не читается (%s): %s" % (p, e)))
            continue
        errs = r.get("errors") or {}
        if r.get("variant") != v or r.get("file_label") != m.group(1) or r.get("profile") != m.group(2):
            bad.append(dict(entry, kind="чужой вариант", reason="result.json говорит %s/%s/%s, тег - %s/%s/%s" % (
                r.get("variant"), r.get("file_label"), r.get("profile"), v, m.group(1), m.group(2))))
        elif errs:
            bad.append(dict(entry, kind="ошибки", errors=sorted(errs),
                            reason="; ".join("errors.%s: %s" % (k, _last_line(errs[k])) for k in sorted(errs))))
        elif not r.get("actions"):
            bad.append(dict(entry, kind="нет действий", reason="нет действий"))
        else:
            r["tag"] = tag
            ok.append(r)
    return ok, bad


def load_runs(root, series, variants):
    """The counted runs only (collect()[0])."""
    return collect(root, series, variants)[0]


def _get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d if isinstance(d, (int, float)) and not isinstance(d, bool) else None


def _num(x):
    return "%.0f" % x if abs(x) >= 1e5 else "%g" % x


def _why_missing(bad, v, fl, prof):
    rs = [b for b in bad if b["variant"] == v and b["file_label"] == fl and b["profile"] == prof]
    if not rs:
        return "в зачётных прогонах метрики нет"
    return "; ".join("%s %s" % (b["tag"], b["reason"]) for b in rs)[:600].replace("|", "/")


def table(ok, bad, base, variant):
    keys = sorted({(r["file_label"], r["profile"]) for r in ok} | {(b["file_label"], b["profile"]) for b in bad})
    lines = ["| файл | профиль | метрика | %s | n | %s | n | × | заметка |" % (base, variant),
             "|---|---|---|---|---|---|---|---|---|"]
    ratios, skipped = [], {}
    for fl, prof in keys:
        side = {v: [r for r in ok if r["variant"] == v and r["file_label"] == fl and r["profile"] == prof]
                for v in (base, variant)}
        if not side[base] and not side[variant]:
            lines.append("| %s | %s | — | — | 0 | — | 0 | — | нет данных ни у %s, ни у %s |"
                         % (fl, prof, base, variant))
            continue
        for action, path in METRICS:
            name = action + "." + ".".join(path)
            vals, ns = {}, {}
            for v in (base, variant):
                s = stats.summary([_get(r["actions"].get(action, {}), path) for r in side[v]])
                vals[v], ns[v] = (s["median"], s["n"]) if s else (None, 0)
            if vals[base] is None and vals[variant] is None:
                continue
            cell = {v: _num(vals[v]) if vals[v] is not None else "—" for v in (base, variant)}
            row = "| %s | %s | %s | %s | %d | %s | %d | " % (fl, prof, name, cell[base], ns[base], cell[variant],
                                                           ns[variant])
            if vals[base] is None or vals[variant] is None:
                miss = base if vals[base] is None else variant
                skipped["нет данных у одной стороны"] = skipped.get("нет данных у одной стороны", 0) + 1
                lines.append(row + "— | нет данных у %s: %s |" % (miss, _why_missing(bad, miss, fl, prof)))
                continue
            ratio = stats.ratio(vals[base], vals[variant])
            if ratio is None:
                skipped["ноль на одной стороне"] = skipped.get("ноль на одной стороне", 0) + 1
                lines.append(row + "— | ноль на одной стороне: отношения нет |")
                continue
            ratios.append(ratio)
            notes = []
            if ratio < 1.0:
                notes.append("медленнее: регрессия")
            if (action, path) == ("hover", ("heavy", "median")):
                few = ["%s n=%s" % (r["tag"], (r["actions"]["hover"].get("heavy") or {}).get("n"))
                       for v in (base, variant) for r in side[v]
                       if ((r["actions"].get("hover") or {}).get("heavy") or {}).get("n", 0) < HEAVY_MIN_N]
                if few:
                    notes.append("мало точек на тяжёлой детали (n < %d): %s" % (HEAVY_MIN_N, ", ".join(few)))
            lines.append(row + "%.2f× | %s |" % (ratio, "; ".join(notes)))
    lines.append("")
    total = len(ratios) + sum(skipped.values())
    why = ", ".join("%s — %d" % kv for kv in sorted(skipped.items()))
    if ratios:
        lines.append("геосреднее ускорения по %d метрикам: %.2f× (пропущено %d из %d%s)" % (
            len(ratios), stats.geomean(ratios), total - len(ratios), total, (": " + why) if why else ""))
    else:
        lines.append("геосреднее: нет ни одной метрики с данными у обеих сторон (пропущено %d%s)" % (
            total, (": " + why) if why else ""))
    lines.extend(guard(ok, base, variant))
    lines.extend(_uncounted_lines(bad))
    return "\n".join(lines)


def _vals(rs, fn):
    out = []
    for r in rs:
        try:
            x = fn(r)
        except (AttributeError, KeyError, TypeError):
            x = None
        out.append(x)
    return out


def _distinct(xs):
    return sorted({str(x) for x in xs})


def _one(xs):
    """The values as text: one value, or the distinct values joined by ' | ' (a GL renderer string has '/' in it)."""
    return " | ".join(_distinct(xs))


def guard(ok, base, variant):
    """Final review I2: "faster" must still be "the same". Per file and profile the counted runs of both variants
    are checked: the opened file (file_md5), HD's commit (hd profile), FreeCAD version and GPU; validity flags that
    turn False; the heavy part and its triangles, the triangles of all parts the hover grid hit; open.objects;
    save.bytes (tolerance BYTES_TOL). Kernel DLL md5s are EXPECTED to differ between stock and a patch: listed, not
    a warning (a difference inside one variant is one)."""
    warn, info = [], []
    keys = sorted({(r["file_label"], r["profile"]) for r in ok})
    for fl, prof in keys:
        side = {v: [r for r in ok if r["variant"] == v and r["file_label"] == fl and r["profile"] == prof]
                for v in (base, variant)}
        if not side[base] or not side[variant]:
            continue
        where = "%s %s" % (fl, prof)
        both = side[base] + [r for r in side[variant] if r not in side[base]]

        def w(msg):
            warn.append("- ВНИМАНИЕ %s: %s" % (where, msg))

        nomd5 = [r["tag"] for r in both if not r.get("file_md5")]
        if nomd5:
            w("md5 открытого файла не записан: %s" % ", ".join(nomd5))
        else:
            md5s = {v: _distinct(r["file_md5"] for r in side[v]) for v in (base, variant)}
            fm = {v: " | ".join(md5s[v]) for v in (base, variant)}
            if md5s[base] != md5s[variant] or len(md5s[base]) > 1 or len(md5s[variant]) > 1:
                w("другой файл: md5 открытого файла %s %s, %s %s" % (base, fm[base], variant, fm[variant]))
        checks = [("версия FreeCAD", lambda r: r["env"]["freecad"]),
                  ("GPU", lambda r: (r["env"].get("gl") or {}).get("renderer"))]
        if prof == "hd":
            checks.insert(0, ("другой коммит HD", lambda r: (r["env"].get("hd") or {}).get("commit")))
        for what, fn in checks:
            dv = {v: _distinct(_vals(side[v], fn)) for v in (base, variant)}
            vv = {v: " | ".join(dv[v]) for v in (base, variant)}
            if dv[base] != dv[variant] or len(dv[base]) > 1 or len(dv[variant]) > 1:
                w("%s: %s %s, %s %s" % (what, base, vv[base], variant, vv[variant]))
        dll = {}
        for v in (base, variant):
            for r in side[v]:
                for n, h in ((r.get("env") or {}).get("md5") or {}).items():
                    dll.setdefault(n, {}).setdefault(v, set()).add(h)
        differ = []
        for n in sorted(dll):
            for v in (base, variant):
                if len(dll[n].get(v, ())) > 1:
                    w("%s внутри варианта %s разный: %s" % (n, v, "/".join(sorted(dll[n][v]))))
            if dll[n].get(base) != dll[n].get(variant):
                differ.append("%s %s %s, %s %s" % (n, base, "/".join(sorted(dll[n].get(base, {"-"}))), variant,
                                                   "/".join(sorted(dll[n].get(variant, {"-"})))))
        if differ:
            info.append("- %s: DLL различаются (ожидаемо у патча): %s" % (where, "; ".join(differ)))
        for action, key in (("edit_cut", "cut_valid"), ("fillet_holes", "valid")):
            vb = _vals(side[base], lambda r: r["actions"][action][key])
            vv = _vals(side[variant], lambda r: r["actions"][action][key])
            falses = [r["tag"] for r, x in zip(side[variant], vv) if x is False]
            if falses and True in vb:
                w("%s.%s стало False: %s" % (action, key, ", ".join(falses)))
            elif falses or False in vb:
                w("%s.%s False в обоих вариантах: %s" % (action, key, ", ".join(
                    [r["tag"] for r, x in zip(side[base], vb) if x is False] + falses)))
        exact = [("hover.heavy_object", lambda r: r["actions"]["hover"]["heavy_object"]),
                 ("hover.heavy_triangles", lambda r: r["actions"]["hover"]["heavy_triangles"]),
                 ("hover.hit_parts triangles", lambda r: sum(p["triangles"] or 0
                                                             for p in r["actions"]["hover"]["hit_parts"])),
                 ("open.objects", lambda r: r["actions"]["open"]["objects"])]
        for what, fn in exact:
            vb, vv = _vals(side[base], fn), _vals(side[variant], fn)
            if all(x is None for x in vb + vv):
                continue
            b1, v1 = _one(vb), _one(vv)
            if b1 != v1:
                w("%s: %s %s, %s %s" % (what, base, b1, variant, v1))
        sb = stats.summary([x for x in _vals(side[base], lambda r: r["actions"]["save"]["bytes"])
                            if isinstance(x, (int, float))])
        sv = stats.summary([x for x in _vals(side[variant], lambda r: r["actions"]["save"]["bytes"])
                            if isinstance(x, (int, float))])
        if sb and sv and sb["median"] > 0:
            d = (sv["median"] - sb["median"]) / sb["median"]
            if abs(d) > BYTES_TOL:
                w("save.bytes: %s %s, %s %s (%+.1f %%, допуск %d %%)" % (
                    base, _num(sb["median"]), variant, _num(sv["median"]), d * 100.0, BYTES_TOL * 100))
    out = ["", "Проверка «то же самое» (быстрее — но то же ли самое):", ""]
    out.extend(warn + info)
    out.append("")
    out.append("Итог проверки: %d предупреждений" % len(warn) if warn else "Итог проверки: всё то же")
    return out


def _uncounted_lines(bad):
    if not bad:
        return []
    return ["", "Незачётные прогоны (в медианы не вошли):", "",
            "| прогон | вариант | файл | профиль | почему |", "|---|---|---|---|---|"] + [
        "| %s | %s | %s | %s | %s |" % (b["tag"], b["variant"], b["file_label"], b["profile"],
                                       b["reason"].replace("|", "/")) for b in bad]


def main():
    if len(sys.argv) not in (5, 6):
        sys.stderr.write("usage: report.py <runs_dir> <series> <base_variant> <variant> [out.md]\n"
                         "  series \"%s\" = the stock baseline of 22.09 (tags without a series prefix)\n"
                         % LEGACY_SERIES)
        sys.exit(2)
    root, series, base, variant = sys.argv[1:5]
    ok, bad = collect(root, series, (base, variant))
    md = "Серия %s: %s → %s\n\n" % (series, base, variant) + table(ok, bad, base, variant)
    if len(sys.argv) > 5:
        out = sys.argv[5]
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
