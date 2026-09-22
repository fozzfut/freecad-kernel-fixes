"""Summaries shared by the in-FreeCAD driver and the report (no FreeCAD imports here)."""
import math


def median(s):
    """The median of a SORTED non-empty list: the middle value, or the mean of the two middle values for an even
    count (final review m3: the upper one, s[n//2], made the "median" of 2 reps the slower rep)."""
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def summary(xs):
    s = sorted(x for x in xs if x is not None)
    if not s:
        return None
    return {"median": median(s), "p90": s[min(len(s) - 1, int(len(s) * 0.9))],
            "min": s[0], "max": s[-1], "n": len(s)}


def ratio(base, variant):
    """Speed-up base/variant of a lower-is-better metric. 0/0 is 1.0 (both instant: the same); a zero on one side
    has no finite ratio: None, which the report shows and counts as skipped (final review m4)."""
    if base == 0 and variant == 0:
        return 1.0
    if base <= 0 or variant <= 0:
        return None
    return base / variant


def geomean(xs):
    """Geometric mean of positive finite values; the caller counts what it leaves out (report.table does)."""
    xs = [x for x in xs if x is not None and x > 0 and math.isfinite(x)]
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else float("nan")
