# r2probe.py - lane vr6-unconf ROUND 2 (review r1 R1): 038 class = an ABSOLUTE camera placement while a finite view
# animation (FixedTimeAnimation / HomeAnimation) still runs. Each member places the camera through a FreeCAD API
# right after an animation started, lets everything settle and compares the whole camera (position, orientation,
# height) with where that placement puts it at rest.
#   a* = placements that must end exactly where they put the camera (fix PASS; delivery FAIL except a04 which stock
#        already stops through startAnimation);
#   b* = identity members: changes during a running animation that this fix does not touch - rotate left (stock: the
#        end snap to the target drops it), zoom in (stock stops the turn half way), a new orientation (stock stop
#        path). CAM lines must equal the delivery's; their PASS/FAIL against the at-rest pose is information only;
#   n* = negative controls at rest (PASS both); i* = INFO (spinning).
# Output: $PROBE_OUT; 'CASE <name> PASS|FAIL|INFO ...' + 'CAM <name> ...' + 'PROBE-DONE'.
import os, time, math, traceback
SRC = "C:/dev/occt8-mig/vr6unconf/probe/vselprobe.py"
_txt = open(SRC, encoding="utf-8").read()
_txt = _txt[:_txt.index("QtCore.QTimer.singleShot(60000 * 3")]
exec(compile(_txt, SRC, "exec"))
CASES.clear()


def cam_full():
    c = view().getCameraNode()
    p = V(*c.position.getValue().getValue())
    q = tuple(c.orientation.getValue().getValue())
    h = c.height.getValue() if hasattr(c, "height") else None
    return p, q, h, c.focalDistance.getValue()


def cam_line(name, cf=None):
    p, q, h, fd = cf or cam_full()
    out(f"CAM {name} pos=({p.x:.5f},{p.y:.5f},{p.z:.5f}) q=({q[0]:.6f},{q[1]:.6f},{q[2]:.6f},{q[3]:.6f}) "
        f"fd={fd:.5f} h={h if h is None else round(h, 5)}")


def vdir(q):
    return V(*coin.SbRotation(*q).multVec(coin.SbVec3f(0, 0, -1)).getValue())


def compare(name, got, ref, dir_only=False, extra=""):
    """PASS when the orientation matches (angle < 0.01 deg; dir_only: the view direction only), the position matches
    ACROSS the view (an orthographic camera may sit anywhere along its direction; < 1e-3 of the view height) and the
    height matches (< 1e-3)."""
    p1, q1, h1, f1 = got
    p2, q2, h2, f2 = ref
    d2 = vdir(q2)
    # angles through atan2 of normalised values: acos of a float32 dot product near 1 reads 0.015 deg for two
    # IDENTICAL quaternions (|q|^2 = 1 - 3.6e-8 in float32)
    if dir_only:
        a, b = vdir(q1), d2
        a.normalize(); b.normalize()
        ang = math.degrees(math.atan2(a.cross(b).Length, a.dot(b)))
    else:
        n1 = math.sqrt(sum(x * x for x in q1)); n2 = math.sqrt(sum(x * x for x in q2))
        u1 = [x / n1 for x in q1]; u2 = [x / n2 for x in q2]
        if sum(a * b for a, b in zip(u1, u2)) < 0:
            u2 = [-x for x in u2]
        diff = math.sqrt(sum((a - b) ** 2 for a, b in zip(u1, u2)))
        summ = math.sqrt(sum((a + b) ** 2 for a, b in zip(u1, u2)))
        ang = math.degrees(4 * math.atan2(diff, summ))
    dv = p1 - p2
    across = (dv - d2 * dv.dot(d2)).Length
    scale = h2 or 100.0
    dh = 0.0 if (h1 is None or h2 is None) else abs(h1 - h2)
    ok = ang < 0.01 and across <= 1e-3 * scale and dh <= 1e-3 * scale
    out(f"CASE {name} {'PASS' if ok else 'FAIL'} dang={ang:.4g}deg across={across:.4g} dh={dh:.4g} scale={scale:.4g} {extra}")
    cam_line(name, got)
    return ok


def base_scene(tag):
    doc = new_doc(tag); set_anim(False)
    asm, L, S = scene_rails(doc)
    start_view()
    return doc, asm, L, S


def saved_view(asm, sub="S1."):
    """A camera to restore: the fit of one stopper at rest (different centre and zoom than Fit all)."""
    select([(asm, sub)]); fit_sel(); ui(); Gui.Selection.clearSelection(); ui()
    return view().getCamera(), cam_full()


def settle():
    ui(1.5)


# ---------------------------------------------------------------- a: absolute placements during an animation
@case
def a01_setcamera_during_right():
    doc, asm, L, S = base_scene("a01")
    saved, ref = saved_view(asm)
    view().viewFront(); view().fitAll(); ui(0.1)
    set_anim(True)
    view().viewRight(); ui()
    view().setCamera(saved)
    settle()
    compare("a01_setcamera_during_right", cam_full(), ref)


@case
def a02_setcamera_during_home():
    doc, asm, L, S = base_scene("a02")
    saved, ref = saved_view(asm)
    view().viewFront(); ui(0.1)
    set_anim(True)
    Gui.runCommand("Std_ViewHome", 0); ui()
    view().setCamera(saved)
    settle()
    compare("a02_setcamera_during_home", cam_full(), ref)


@case
def a03_setcamera_same_orientation_during_translation():
    """Translation-only animation (setCameraOrientation to the current orientation with moveToCenter) and a restore
    with the SAME orientation: no orientation change marks this placement - only the API call does."""
    doc, asm, L, S = base_scene("a03")
    view().viewRight(); ui()
    saved, ref = saved_view(asm, "S2.")
    select([(asm, "L1.")]); fit_sel(); ui(); Gui.Selection.clearSelection(); ui()
    set_anim(True)
    view().setCameraOrientation(view().getCameraNode().orientation.getValue().getValue(), True); ui()
    view().setCamera(saved)
    settle()
    compare("a03_setcamera_same_orientation_during_translation", cam_full(), ref)


@case
def a04_viewposition_during_right():
    doc, asm, L, S = base_scene("a04")
    saved, ref = saved_view(asm)
    p, q, h, fd = ref
    pl = Placement(p, Rotation(*q))
    view().viewFront(); view().fitAll(); ui(0.1)
    set_anim(True)
    view().viewRight(); ui()
    view().viewPosition(pl, 0, 150)
    settle()
    got = cam_full()
    # viewPosition places position + orientation (the height stays): compare those two only
    compare("a04_viewposition_during_right", (got[0], got[1], None, got[3]), (p, q, None, fd))


@case
def a05_viewdefaultorientation_during_right():
    doc, asm, L, S = base_scene("a05")
    view().viewDefaultOrientation("Front", 300.0); settle()
    ref = cam_full()
    view().viewIsometric(); view().fitAll(); ui(0.1)
    set_anim(True)
    view().viewRight(); ui()
    view().viewDefaultOrientation("Front", 300.0)
    settle()
    compare("a05_viewdefaultorientation_during_right", cam_full(), ref)


@case
def a06_setviewdirection_during_right():
    doc, asm, L, S = base_scene("a06")
    set_anim(True)
    view().viewRight(); ui()
    p0 = cam_full()[0]
    view().setViewDirection((1.0, 1.0, -1.0))
    after_call = cam_full()
    settle()
    got = cam_full()
    compare("a06_setviewdirection_during_right", got, (p0, after_call[1], after_call[2], after_call[3]), dir_only=True)


# ---------------------------------------------------------------- b: identity (stock combines / stock stops)
@case
def b01_rotateleft_during_right():
    doc, asm, L, S = base_scene("b01")
    view().viewRight(); ui(); view().viewRotateLeft(); ui()
    ref = cam_full()
    start_view()
    set_anim(True)
    view().viewRight(); ui()
    view().viewRotateLeft()
    settle()
    compare("b01_rotateleft_during_right", cam_full(), ref, extra="IDENTITY-MEMBER (judged fix == delivery)")


@case
def b02_zoomin_during_right():
    doc, asm, L, S = base_scene("b02")
    view().viewRight(); ui(); view().zoomIn(); ui()
    ref = cam_full()
    start_view()
    set_anim(True)
    view().viewRight(); ui()
    view().zoomIn()
    settle()
    compare("b02_zoomin_during_right", cam_full(), ref, extra="IDENTITY-MEMBER (judged fix == delivery)")


@case
def b03_top_during_right():
    doc, asm, L, S = base_scene("b03")
    view().viewTop(); ui()
    ref = cam_full()
    start_view()
    set_anim(True)
    view().viewRight(); ui()
    view().viewTop()
    settle()
    compare("b03_top_during_right", cam_full(), ref, extra="IDENTITY-MEMBER (judged fix == delivery)")


# ---------------------------------------------------------------- n: negative controls (no running animation)
@case
def n01_setcamera_at_rest():
    doc, asm, L, S = base_scene("n01")
    saved, ref = saved_view(asm)
    view().viewFront(); view().fitAll(); ui(0.1)
    set_anim(True)
    view().setCamera(saved)
    settle()
    compare("n01_setcamera_at_rest", cam_full(), ref)


@case
def n02_setviewdirection_at_rest():
    doc, asm, L, S = base_scene("n02")
    view().viewRight(); ui()
    p0 = cam_full()[0]
    view().setViewDirection((1.0, 1.0, -1.0))
    after_call = cam_full()
    settle()
    compare("n02_setviewdirection_at_rest", cam_full(), (p0, after_call[1], after_call[2], after_call[3]), dir_only=True)


# ---------------------------------------------------------------- i: info
@case
def i01_setcamera_while_spinning():
    doc, asm, L, S = base_scene("i01")
    saved, ref = saved_view(asm)
    set_anim(True)
    view().startAnimating(0.0, 0.0, 1.0, 1.0); ui(0.3)
    view().setCamera(saved)
    ui(0.6)
    got = cam_full()
    view().stopAnimating(); ui()
    p1, q1, h1, f1 = got
    dot = min(1.0, abs(sum(a * b for a, b in zip(q1, ref[1]))))
    out(f"CASE i01_setcamera_while_spinning INFO dang={math.degrees(2 * math.acos(dot)):.4g}deg "
        f"(0 = the restore stopped the spin, as setCameraOrientation does; >0 = spinning went on)")


def main2():
    main()


QtCore.QTimer.singleShot(60000 * 3, lambda: (out("HARD TIMEOUT"), fh.close(), os._exit(3)))
QtCore.QTimer.singleShot(1500, main2)
