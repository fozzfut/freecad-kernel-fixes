"""FreeCAD-side helpers of the action benchmark.

Renderer, mem_mb, pump and sel_target are copied from C:/dev/hybriddesign-render/phase1/scripts/rc_common.py
(measured there: the viewer's own GL render action makes frames reproducible; hover goes through
SoHandleEventAction inside this process, no OS input). New here: CPU load, idle wait, environment record, hard exit.
"""
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


def hard_exit(code=0):
    """End this process at once (TerminateProcess): no Python teardown and no DLL detach code. os._exit runs the
    detach code, and with HD loaded that aborted after the result was written (smoke-hd: exit 127, "Abnormal program
    termination" last in fc.log), so the exit code said nothing about the run."""
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
        "mem": mem_mb(),
    }
