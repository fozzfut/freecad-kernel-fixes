"""FreeCAD-side helpers of the action benchmark.

Renderer, mem_mb, pump and sel_target are copied from C:/dev/hybriddesign-render/phase1/scripts/rc_common.py
(measured there: the viewer's own GL render action makes frames reproducible; hover goes through
SoHandleEventAction inside this process, no OS input). New here: CPU load, idle wait, environment record, hard exit,
the wait for HybridDesign's stage-2 refinement and the stop of child processes (HD's mesh worker) at the end.
"""
import contextlib
import ctypes
import ctypes.wintypes
import hashlib
import math
import os
import sys
import time

import FreeCAD as App
import numpy as np
from pivy import coin
from PySide import QtWidgets

GL = ctypes.WinDLL("opengl32")
GL.glGetString.restype = ctypes.c_char_p


class _PMC(ctypes.Structure):
    _fields_ = [("cb", ctypes.wintypes.DWORD), ("PageFaultCount", ctypes.wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t)]


_K32 = ctypes.WinDLL("kernel32")
_K32.GetCurrentProcess.restype = ctypes.wintypes.HANDLE
_PSAPI = ctypes.WinDLL("psapi")
_PSAPI.GetProcessMemoryInfo.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(_PMC), ctypes.wintypes.DWORD]


def mem_mb():
    c = _PMC()
    c.cb = ctypes.sizeof(c)
    _PSAPI.GetProcessMemoryInfo(_K32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return {"ws_mb": round(c.WorkingSetSize / 2 ** 20, 1), "private_mb": round(c.PrivateUsage / 2 ** 20, 1),
            "peak_ws_mb": round(c.PeakWorkingSetSize / 2 ** 20, 1)}


def pump(n=3):
    for _ in range(n):
        QtWidgets.QApplication.processEvents()


class Renderer(object):
    """Draws the active 3D view's own scene graph offscreen. size=None: the viewer's viewport size."""

    def __init__(self, view, size=None):
        self.view = view
        self.rm = view.getViewer().getSoRenderManager()
        vp = self.rm.getViewportRegion().getViewportSizePixels().getValue()
        self.viewer_size = (int(vp[0]), int(vp[1]))
        self.W, self.H = size or self.viewer_size
        self.region = coin.SbViewportRegion(self.W, self.H)
        self.gl = {}
        self.cb = coin.SoCallback()
        self.cb.setCallback(self._cb)
        self.cb.ref()
        self.r = coin.SoOffscreenRenderer(self.region)
        self.r.setBackgroundColor(coin.SbColor(1, 1, 1))
        # The viewer's own GL render action (Gui::SoBoxSelectionRenderAction, transparency type as configured).
        # Measured in probe6: with Coin's plain SoGLRenderAction the frame is not reproducible (clearing a highlight
        # left 12919 px different from the base) and sub-element highlights do not draw; with the viewer's action
        # clearing gives the base back exactly and edge highlights draw.
        self.action = self.rm.getGLRenderAction()
        self.r.setGLRenderAction(self.action)

    def _cb(self, ud, action):
        if not self.gl and action.isOfType(coin.SoGLRenderAction.getClassTypeId()):
            for k, e in (("vendor", 0x1F00), ("renderer", 0x1F01), ("version", 0x1F02)):
                v = GL.glGetString(e)
                self.gl[k] = v.decode() if v else None

    def camera(self):
        return self.rm.getCamera()

    def scene(self):
        return self.rm.getSceneGraph()

    def fit_iso(self):
        """Isometric fit placed directly on the camera. view.viewIsometric() starts an animated camera move (owner's
        navigation animations) that later processEvents() calls carry on, which left every frame blank (probe4)."""
        try:
            self.view.setAnimationEnabled(False)
        except Exception:
            pass
        for _ in range(20):
            pump(2)
            time.sleep(0.02)
        cam = self.camera()
        with self.view_fit_scope():
            ba = coin.SoGetBoundingBoxAction(self.region)
            ba.apply(self.scene())
            box = ba.getBoundingBox()
            centre = box.getCenter()
            cam.position.setValue(centre + coin.SbVec3f(1.0, -1.0, 1.0) * 1000.0)
            cam.pointAt(centre, coin.SbVec3f(0, 0, 1))
            cam.viewAll(self.scene(), self.region)
        self.autoclip()
        pump(5)
        self.cam_state = self.camera_state()

    @contextlib.contextmanager
    def view_fit_scope(self):
        """The model's box as FreeCAD's View Fit sees it (View3DInventorViewer::viewAll, FreeCAD 1.1.1: every
        SoSkipBoundingGroup of the scene set to EXCLUDE_BBOX for the box and the camera's viewAll, then back to
        INCLUDE_BBOX). Not a copy of rc_common: added in Task 2 fix round 3. HybridDesign's layout grid
        (HD_LayoutGrid, gui/grid.py) is such a group; it sizes itself from the view volume while drawing, so with
        a plain box the fit and the orbit centre took the grid in and the model shrank on screen after each frame
        (fixture:pad, hd profile: 2 of 144 hover points on the pad against 34 in fc, runs/smoke-hd and
        runs/fix3-bbox-hd). Autoclip keeps the plain box: FreeCAD sets the clipping planes from it with the grid
        in (gui/grid.py, measured by HD)."""
        sa = coin.SoSearchAction()
        sa.setType(coin.SoType.fromName("SoSkipBoundingGroup"))
        sa.setInterest(coin.SoSearchAction.ALL)
        sa.apply(self.scene())
        paths = sa.getPaths()
        groups = [paths[i].getTail() for i in range(paths.getLength())]
        for g in groups:
            g.set("mode EXCLUDE_BBOX")
        try:
            yield len(groups)
        finally:
            for g in groups:
                g.set("mode INCLUDE_BBOX")

    def camera_state(self):
        cam = self.camera()
        return (tuple(round(v, 4) for v in cam.position.getValue().getValue()),
                tuple(round(v, 5) for v in cam.orientation.getValue().getValue()))

    def autoclip(self):
        ba = coin.SoGetBoundingBoxAction(self.region)
        ba.apply(self.scene())
        box = ba.getBoundingBox()
        if box.isEmpty():
            return
        cam = self.camera()
        lo, hi = box.getMin().getValue(), box.getMax().getValue()
        pos = cam.position.getValue().getValue()
        d = cam.orientation.getValue().multVec(coin.SbVec3f(0, 0, -1)).getValue()
        depths = [(x - pos[0]) * d[0] + (y - pos[1]) * d[1] + (z - pos[2]) * d[2]
                  for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
        near, far = min(depths), max(depths)
        cam.nearDistance = near - abs(near) * 0.001 - 1.0
        cam.farDistance = far + abs(far) * 0.001 + 1.0

    def frame(self, clip=True):
        """One frame: autoclip (bounding box action, as the viewer does) + render + read back. Returns ms."""
        t = time.perf_counter()
        if clip:
            self.autoclip()
        wrap = coin.SoSeparator()
        wrap.ref()
        wrap.addChild(self.cb)
        wrap.addChild(self.scene())
        self.r.render(wrap)
        self.r.getBuffer()      # glReadPixels: waits for the GPU
        wrap.unref()
        return (time.perf_counter() - t) * 1000.0

    def image(self, clip=False):
        self.frame(clip)
        return np.frombuffer(self.r.getBuffer(), dtype=np.uint8).reshape(self.H, self.W, 3)[::-1].copy()

    def orbit(self, steps=72, warm=12):
        cam = self.camera()
        with self.view_fit_scope():
            ba = coin.SoGetBoundingBoxAction(self.region)
            ba.apply(self.scene())
            centre = ba.getBoundingBox().getCenter()
        pos0 = cam.position.getValue()
        rot0 = cam.orientation.getValue()
        offset = pos0 - centre
        times = []
        for k in range(warm + steps):
            rot = coin.SbRotation(coin.SbVec3f(0, 0, 1), 2.0 * math.pi * (k + 1) / steps)
            cam.position.setValue(centre + rot.multVec(offset))
            cam.orientation.setValue(rot0 * rot)
            ms = self.frame()
            if k >= warm:
                times.append(ms)
        cam.position.setValue(pos0)
        cam.orientation.setValue(rot0)
        s = sorted(times)
        return {"median_ms": round(s[len(s) // 2], 2), "p90_ms": round(s[int(len(s) * 0.9)], 2),
                "min_ms": round(s[0], 2), "max_ms": round(s[-1], 2), "steps": steps}

    def hover(self, x, y):
        """A mouse move over viewer pixel (x, y) delivered to the scene graph as Coin's SoLocation2Event through
        SoHandleEventAction - inside this process, no OS input. (x, y) are in the coordinates view.getObjectInfo
        takes, which are Coin's (origin bottom-left): measured in probe5, the flipped position highlighted nothing
        and the unflipped one highlighted the picked Link face."""
        ev = coin.SoLocation2Event()
        ev.setPosition(coin.SbVec2s(int(x), int(y)))
        ev.setTime(coin.SbTime.getTimeOfDay())
        ha = coin.SoHandleEventAction(self.rm.getViewportRegion())
        ha.setEvent(ev)
        ha.setPickRadius(5)
        ha.apply(self.scene())
        return ha.isHandled()


def sel_target(doc, info):
    """(object, subname) for Gui.Selection from a getObjectInfo() dict, full path from the top object."""
    parent = info.get("ParentObject")
    sub = info.get("SubName")
    if parent is not None and sub:
        obj = parent if not isinstance(parent, str) else doc.getObject(parent)
        return obj, sub
    return doc.getObject(info["Object"]), info.get("Component", "")


class _FT(ctypes.Structure):
    _fields_ = [("lo", ctypes.wintypes.DWORD), ("hi", ctypes.wintypes.DWORD)]


def _systimes():
    idle, kern, user = _FT(), _FT(), _FT()
    ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user))
    f = lambda t: (t.hi << 32) | t.lo  # noqa: E731
    return f(idle), f(kern) + f(user)


class CpuLoad(object):
    """Machine-wide CPU busy % between start() and stop() (the machine is shared: record, don't assume)."""

    def start(self):
        self.a = _systimes()
        return self

    def stop(self):
        i0, t0 = self.a
        i1, t1 = _systimes()
        dt = t1 - t0
        return round(100.0 * (1.0 - (i1 - i0) / dt), 1) if dt > 0 else None


def wait_idle(quiet_ms=200, slice_ms=2.0, max_s=600):
    """Pump the event loop until it has been quiet for quiet_ms: every processEvents() call in that window took
    under slice_ms. Returns seconds spent. A heavy job posted to the loop (meshing, HD refinement) keeps it busy."""
    t0 = time.perf_counter()
    quiet_since = None
    while time.perf_counter() - t0 < max_s:
        a = time.perf_counter()
        QtWidgets.QApplication.processEvents()
        took = (time.perf_counter() - a) * 1000.0
        now = time.perf_counter()
        if took < slice_ms:
            quiet_since = quiet_since or now
            if (now - quiet_since) * 1000.0 >= quiet_ms:
                return quiet_since - t0
        else:
            quiet_since = None
        time.sleep(0.001)
    return time.perf_counter() - t0


def _hd_progressive():
    return sys.modules.get("hybriddesign.gui.progressive")


def hd_refinement(doc_name, max_s=300.0):
    """Wait until HybridDesign's stage-2 refinement queue of this document is empty; None when HD is not loaded.

    HD opens a heavy file in two stages (hybriddesign/gui/progressive.py): a part whose mesh at the file's own
    quality is expensive is drawn coarse first, then re-meshed at that quality by a FreeCAD.exe HD starts itself
    (gui/mesh_process.py) and swapped in a slice per frame. Between the slices the event loop only runs HD's 60 ms
    polls, so wait_idle() returns at the coarse picture while the worker is still meshing. The queue is empty when no
    pass is running (no live job, no mesh waiting to be put in) and no part is left that HD would still refine: each
    lowered part is refined, dropped, hidden (HD refines it when it is shown) or has had its MAX_ATTEMPTS passes (HD
    reports it as 'stuck'). The wait is bounded by max_s: nothing is cut short in HD, the run only says it did not
    get there. An empty queue with parts still coarse is not the file's picture either: state 'stuck'. Measured in
    fix round 1 (runs/fix1-probes/prev-attempt-fix1-vr6-hd.result.json): the machine's FreeCAD guard suspended both
    of HD's workers, HD gave up on them after 90 s each, and all 13 lowered parts of VR6 stayed coarse while the
    queue was empty.

    Returns {"state": done | no-session (nothing was lowered) | stuck | timeout | error, "empty_at": perf_counter()
    when the queue was seen empty (None at a timeout or an error), "wait_s", "worker_pids": the worker processes HD
    started for this document while it was waited for, "hd_finished_at": HD's own end-of-pass mark (perf_counter(),
    this process), "pending" (what was still owed at a timeout), "coarse" (the shown parts left coarse, when stuck)
    and "report" (HD's report, per part)}."""
    prog = _hd_progressive()
    if prog is None:
        return None
    t0 = time.perf_counter()
    pids, state, detail, owed, coarse = [], "no-session", None, [], []
    while True:
        try:
            s = prog.session(doc_name)
            if s is None:
                break
            job = getattr(s, "job", None)
            pid = getattr(job, "pid", None) if job is not None else None
            if pid and pid not in pids:
                pids.append(pid)
            running = (job is not None and not getattr(job, "finished", False)) or bool(getattr(s, "fillers", None))
            tries = getattr(prog, "MAX_ATTEMPTS", 2)
            owed = [p.name for p in s.parts.values() if not getattr(p, "refined", False)
                    and not getattr(p, "dropped", False) and not s.hidden(p.name)
                    and getattr(p, "attempts", 0) < tries]
            if not running and not owed:
                coarse = [p.name for p in s.parts.values() if not getattr(p, "refined", False)
                          and not getattr(p, "dropped", False) and not s.hidden(p.name)]
                state = "stuck" if coarse else "done"
                break
        except Exception as exc:          # HD's internals moved on: say so instead of hanging or guessing
            state, detail = "error", repr(exc)
            break
        if time.perf_counter() - t0 > max_s:
            state = "timeout"
            break
        QtWidgets.QApplication.processEvents()
        time.sleep(0.005)
    now = time.perf_counter()
    rec = {"state": state, "empty_at": now if state in ("done", "no-session", "stuck") else None,
           "wait_s": round(now - t0, 3), "worker_pids": pids, "hd_finished_at": None}
    if detail:
        rec["error"] = detail
    if state == "timeout":
        rec["pending"] = owed
    if state == "stuck":
        rec["coarse"] = coarse
    s = prog.session(doc_name)
    if s is not None:
        rec["hd_finished_at"] = getattr(s, "finished_at", None)
        try:
            rec["report"] = s.report()
        except Exception as exc:
            rec["report_error"] = repr(exc)
    return rec


class _PE32(ctypes.Structure):
    _fields_ = [("dwSize", ctypes.wintypes.DWORD), ("cntUsage", ctypes.wintypes.DWORD),
                ("th32ProcessID", ctypes.wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                ("th32ModuleID", ctypes.wintypes.DWORD), ("cntThreads", ctypes.wintypes.DWORD),
                ("th32ParentProcessID", ctypes.wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", ctypes.wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]


_H, _DW = ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD
_K32.OpenProcess.restype = _H
_K32.OpenProcess.argtypes = [_DW, ctypes.wintypes.BOOL, _DW]
_K32.CloseHandle.argtypes = [_H]
_K32.GetProcessTimes.argtypes = [_H] + [ctypes.POINTER(_FT)] * 4
_K32.CreateToolhelp32Snapshot.restype = _H
_K32.CreateToolhelp32Snapshot.argtypes = [_DW, _DW]
_K32.Process32FirstW.argtypes = [_H, ctypes.POINTER(_PE32)]
_K32.Process32NextW.argtypes = [_H, ctypes.POINTER(_PE32)]


def _created(pid):
    """Creation time of a process (FILETIME as an int), None when it cannot be asked."""
    h = _K32.OpenProcess(0x1000, False, int(pid))          # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        c, e, k, u = _FT(), _FT(), _FT(), _FT()
        if not _K32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u)):
            return None
        return (c.hi << 32) | c.lo
    finally:
        _K32.CloseHandle(h)


def children():
    """[(pid, exe)] of the live processes this process started. A child made before this process is not ours
    (its parent id was reused), so creation times are compared as well."""
    me, born = os.getpid(), _created(os.getpid())
    snap = _K32.CreateToolhelp32Snapshot(0x2, 0)          # TH32CS_SNAPPROCESS
    out = []
    try:
        e = _PE32()
        e.dwSize = ctypes.sizeof(e)
        ok = _K32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            if e.th32ParentProcessID == me:
                c = _created(e.th32ProcessID)
                if c is not None and born is not None and c >= born:
                    out.append((int(e.th32ProcessID), e.szExeFile))
            ok = _K32.Process32NextW(snap, ctypes.byref(e))
    finally:
        _K32.CloseHandle(snap)
    return out


def end_children(wait_s=10.0):
    """Stop what this run started before the process ends, wait until it is gone, and say what that was.

    hard_exit ends only this process, and HD's mesh worker (a FreeCAD.exe HD starts itself, gui/mesh_process.py)
    would outlive it and the run's slots. HD's own cancel is asked first (MeshJob._finish kills its worker and waits
    for it); a FreeCAD child still alive after that is terminated here and waited for (up to wait_s). Other children
    are only listed. Returns {"hd_cancelled": [documents whose pass was still running], "children": [{pid, exe,
    terminated, exited}]}."""
    cancelled = []
    prog = _hd_progressive()
    if prog is not None:
        for name, s in list(prog.sessions().items()):
            job = getattr(s, "job", None)
            if job is not None and not getattr(job, "finished", False):
                try:
                    s.cancel("the bench run is over")
                    cancelled.append(name)
                except Exception:
                    pass
    _K32.TerminateProcess.argtypes = [_H, ctypes.wintypes.UINT]
    _K32.WaitForSingleObject.argtypes = [_H, _DW]
    _K32.WaitForSingleObject.restype = _DW
    out = []
    for pid, exe in children():
        row = {"pid": pid, "exe": exe, "terminated": False, "exited": None}
        if exe.lower().startswith("freecad"):
            h = _K32.OpenProcess(0x0001 | 0x1000 | 0x00100000, False, pid)  # TERMINATE | QUERY_LIMITED | SYNCHRONIZE
            if h:
                try:
                    row["terminated"] = bool(_K32.TerminateProcess(h, 1))
                    row["exited"] = _K32.WaitForSingleObject(h, int(wait_s * 1000)) == 0   # WAIT_OBJECT_0
                finally:
                    _K32.CloseHandle(h)
        out.append(row)
    return {"hd_cancelled": cancelled, "children": out}


def hard_exit(code=0):
    """End this process at once (TerminateProcess): no Python teardown and no DLL detach code. os._exit runs the
    detach code, and with HD loaded that aborted after the result was written (exit 127, "Abnormal program
    termination" last in fc.log: runs/smoke-hd-before, the brief's code), so the exit code said nothing about the
    run."""
    _K32.TerminateProcess.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.UINT]
    _K32.TerminateProcess(_K32.GetCurrentProcess(), code)
    os._exit(code)


def _md5(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except OSError:
        return None


def environment():
    bindir = os.path.dirname(sys.executable)
    libdir = os.path.join(os.path.dirname(bindir), "lib")
    return {
        "freecad": ".".join(App.Version()[:3]) + " " + App.Version()[3],
        "exe": sys.executable,
        "md5": {n: _md5(os.path.join(bindir, n)) for n in ("TKMesh.dll", "TKTopAlgo.dll", "TKBO.dll",
                                                          "TKFillet.dll", "FreeCADGui.dll")}
               | {n: _md5(os.path.join(libdir, n)) for n in ("Part.pyd", "PartGui.pyd")},
        "hd_loaded": "hybriddesign" in sys.modules,
        "hd": hd_version(),
        "pid": os.getpid(),
        "mem": mem_mb(),
    }


def hd_version():
    """Which HybridDesign the hd profile ran: its repository and commit, read from the .git files (the repository
    is read-only for the bench, so no git command runs in it). The installed HD changes as work is merged into it
    (a merge landed during the fix round of 22.09.2026), and hd rows are only comparable on the same commit."""
    mod = sys.modules.get("hybriddesign")
    if mod is None or not getattr(mod, "__file__", None):
        return None
    repo = os.path.dirname(os.path.dirname(os.path.abspath(mod.__file__)))
    out = {"path": repo, "ref": None, "commit": None}
    git = os.path.join(repo, ".git")
    try:
        with open(os.path.join(git, "HEAD"), encoding="utf-8") as f:
            head = f.read().strip()
        if not head.startswith("ref: "):
            out["commit"] = head
            return out
        out["ref"] = head[5:]
        loose = os.path.join(git, *out["ref"].split("/"))
        if os.path.isfile(loose):
            with open(loose, encoding="utf-8") as f:
                out["commit"] = f.read().strip()
        else:
            with open(os.path.join(git, "packed-refs"), encoding="utf-8") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) == 2 and parts[1] == out["ref"]:
                        out["commit"] = parts[0]
    except OSError:
        pass
    return out
