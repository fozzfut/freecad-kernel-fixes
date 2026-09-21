"""Summaries shared by the in-FreeCAD driver and the report (no FreeCAD imports here)."""
import math


def summary(xs):
    s = sorted(x for x in xs if x is not None)
    if not s:
        return None
    return {"median": s[len(s) // 2], "p90": s[min(len(s) - 1, int(len(s) * 0.9))],
            "min": s[0], "max": s[-1], "n": len(s)}


def geomean(xs):
    xs = [x for x in xs if x and x > 0]
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else float("nan")
