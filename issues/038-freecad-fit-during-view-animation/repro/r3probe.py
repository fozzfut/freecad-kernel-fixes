# r3probe.py - lane vr6-unconf ROUND 3 (review r2 R1 + m2 + m3). Class: a camera motion that places the camera by
# itself (FixedTimeAnimation/HomeAnimation relative steps, Coin seek absolute steps) must not go on after another
# placement or motion takes over: whichever comes later wins.
#   review cases (rv2probe.py / rv2probe_b.py, exec'd unchanged): d01 Std_RecallWorkingView during Right, d02
#     Std_ViewRestoreCamera during Right (fix PASS, delivery FAIL), n11 recall at rest (PASS both = negative control),
#     d01s stop-first control, d03-d06, d07/d08 INFO, e01/e02 identity;
#   s* = seek members (m2): s01 Right started during a seek, s02 seek started during Right, s03 fit during a seek,
#     s04 setCamera during a seek, s05 recall during a seek, s07 view.stopAnimating during a seek (declared change);
#     s06 seek at rest = negative control (PASS both);
#   l* = m3 order: l01 setViewDirection refused by the orientation lock during Right must not stop the turn (stock
#     semantics: PASS delivery + fix3, FAIL on r2 fix2); l02 same for viewDefaultOrientation.
import os
R2 = "C:/dev/occt8-mig/vr6unconf-r2/probe/rv2probe.py"
_t = open(R2, encoding="utf-8").read()
_t = _t[:_t.index("def main2():")]
exec(compile(_t, R2, "exec"))
RB = "C:/dev/occt8-mig/vr6unconf-r2/probe/rv2probe_b.py"
_b = open(RB, encoding="utf-8").read()
_b = _b[_b.index("@case\ndef d01s"):_b.index("def main2():")]
exec(compile(_b, RB, "exec"))

P = (175.0, 0.0, 7.5)          # seek target (a point on the rails scene, as d07/d08)


def seek(p=P):
    view().getViewer().seekToPoint(p)


def on_axis(name, cf, p=P, extra=""):
    """PASS when the seek target lies on the final line of sight (< 1e-3 of the view height) and the camera is still."""
    pos, q, h, fd = cf
    d = vdir(q); d.normalize()
    v = V(*p) - pos
    off = (v - d * v.dot(d)).Length
    ui(0.5)
    still = cam_full()
    moved = (still[0] - pos).Length + sum(abs(a - b) for a, b in zip(still[1], q))
    scale = h or 100.0
    ok = off <= 1e-3 * scale and moved < 1e-6
    out(f"CASE {name} {'PASS' if ok else 'FAIL'} off-axis={off:.4g} scale={scale:.4g} moved-after={moved:.3g} {extra}")
    cam_line(name, cf)
    return ok


def right_ref():
    set_anim(False); view().viewRight(); ui()
    r = cam_full()
    return r


@case
def s01_right_started_during_seek():
    doc, asm, L, S = base_scene("s01")
    ref = right_ref(); start_view()
    set_anim(True)
    seek(); ui()
    view().viewRight(); ui(2.0)
    got = cam_full()
    compare("s01_right_started_during_seek", (got[0], got[1], None, got[3]), (got[0], ref[1], None, ref[3]),
            extra="(orientation only; the turn starts where the seek was stopped)")


@case
def s02_seek_started_during_right():
    doc, asm, L, S = base_scene("s02")
    set_anim(True)
    view().viewFront(); ui(1.0); view().fitAll(); ui(0.1)
    view().viewRight(); ui()
    seek(); ui(2.0)
    on_axis("s02_seek_started_during_right", cam_full())


@case
def s03_fit_during_seek():
    doc, asm, L, S = base_scene("s03")
    set_anim(True)
    seek(); ui(2.0); view().fitAll(); settle()
    ref = cam_full()
    set_anim(False); start_view(); set_anim(True)
    seek(); ui()
    view().fitAll(); settle()
    compare("s03_fit_during_seek", cam_full(), ref, extra="(ref = seek to its end, then Fit all)")


@case
def s04_setcamera_during_seek():
    doc, asm, L, S = base_scene("s04")
    saved, ref = saved_view(asm)
    set_anim(False); start_view(); set_anim(True)
    seek(); ui()
    view().setCamera(saved)
    settle()
    compare("s04_setcamera_during_seek", cam_full(), ref)


@case
def s05_recall_working_view_during_seek():
    doc, asm, L, S = base_scene("s05")
    saved, ref = saved_view(asm)
    Gui.runCommand("Std_StoreWorkingView", 0); ui()
    set_anim(False); start_view(); set_anim(True)
    seek(); ui()
    Gui.runCommand("Std_RecallWorkingView", 0)
    settle()
    compare("s05_recall_working_view_during_seek", cam_full(), ref)


@case
def s06_seek_at_rest():
    doc, asm, L, S = base_scene("s06")
    set_anim(True)
    seek(); ui(2.0)
    on_axis("s06_seek_at_rest", cam_full())


@case
def s07_stopanimating_during_seek():
    doc, asm, L, S = base_scene("s07")
    set_anim(True)
    seek(); ui()
    view().stopAnimating()
    b = cam_full()
    ui(1.0)
    a = cam_full()
    moved = (a[0] - b[0]).Length + sum(abs(x - y) for x, y in zip(a[1], b[1]))
    out(f"CASE s07_stopanimating_during_seek {'PASS' if moved < 1e-6 else 'FAIL'} moved-after-stop={moved:.4g} "
        f"(declared change: view.stopAnimating also ends a seek)")


@case
def l01_setviewdirection_locked_during_right():
    doc, asm, L, S = base_scene("l01")
    ref = right_ref()
    view().viewFront(); view().fitAll(); ui(0.1)
    set_anim(True)
    view().viewRight(); ui()
    ns = view().getViewer().getNavigationStyle()
    ns.setOrientationLocked(True)
    view().setViewDirection((0.0, 0.0, -1.0))
    ns.setOrientationLocked(False)
    settle()
    got = cam_full()
    compare("l01_setviewdirection_locked_during_right", (got[0], got[1], None, got[3]), (got[0], ref[1], None, ref[3]),
            extra="(refused placement: the turn goes on to Right)")


@case
def l02_viewdefaultorientation_locked_during_right():
    doc, asm, L, S = base_scene("l02")
    ref = right_ref()
    view().viewFront(); view().fitAll(); ui(0.1)
    set_anim(True)
    view().viewRight(); ui()
    ns = view().getViewer().getNavigationStyle()
    ns.setOrientationLocked(True)
    view().viewDefaultOrientation("Top", 100.0)
    ns.setOrientationLocked(False)
    settle()
    got = cam_full()
    compare("l02_viewdefaultorientation_locked_during_right", (got[0], got[1], None, got[3]),
            (got[0], ref[1], None, ref[3]), extra="(refused placement: the turn goes on to Right)")


def main3():
    main()


QtCore.QTimer.singleShot(60000 * 4, lambda: (out("HARD TIMEOUT"), fh.close(), os._exit(3)))
QtCore.QTimer.singleShot(1500, main3)
