"""FreeCAD.exe (offscreen, tools/build_fixture.sh): build a bench fixture once into bench/files
(fixtures.cache_path) so the timed runs of fixture:<name> open it instead of building it. Env: BENCH_FIXTURE
(holes1024), BENCH_OUT (directory for build.pid and build.json). Writes build.pid at once (build_fixture.sh stops
this process's leftovers by it after a timeout) and build.json at the end: path, seconds, or the traceback."""
import json
import os
import sys
import time
import traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PySide import QtCore  # noqa: E402
from fcbench import common as C, fixtures as F  # noqa: E402

with open(os.path.join(os.environ["BENCH_OUT"], "build.pid"), "w") as _f:
    _f.write(str(os.getpid()))


def main():
    name = os.environ.get("BENCH_FIXTURE", "holes1024")
    res = {"fixture": name, "path": F.cache_path(name), "existed": os.path.isfile(F.cache_path(name))}
    t = time.perf_counter()
    try:
        res["path"] = F.build(name, None)
        res["bytes"] = os.path.getsize(res["path"])
    except Exception:
        res["error"] = traceback.format_exc()
    res["seconds"] = round(time.perf_counter() - t, 1)
    with open(os.path.join(os.environ["BENCH_OUT"], "build.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    C.hard_exit(0)


QtCore.QTimer.singleShot(2500, main)
