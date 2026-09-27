# okprobe.py - lane vr6-unconf, item (a): "task dialog still open after OK" right after closing a sketch
# (STUMBLES.md, run_asm.log step s40, no HD, seen once in 7 runs). Repeats the user path of s40 - PartDesign_Body,
# PartDesign_NewSketch on an origin plane / on a face, geometry, the task panel's own OK - many times and in variants,
# with the fcui driver's own ok() check (press(), ui(), ui(10)), and records for every close: which button box was
# clicked, whether the dialog / edit mode was still there at the fcui check, and when it really went away.
# Output: $PROBE_OUT ('ITER ...' lines, 'SUMMARY ...', 'PROBE-DONE').
import os, sys, time, json, traceback
sys.path.insert(0, "C:/dev/tools/fcui")
from fcui import *
import fcui

OUT = os.environ.get("PROBE_OUT", "C:/dev/occt8-mig/vr6unconf/runs/ok.txt")
N = int(os.environ.get("OK_N", "25"))
VARIANTS = [v for v in os.environ.get("OK_VARIANTS", "circle_yz,rect_yz,face,after_pattern,circle_xy_keepsel").split(",") if v]
fh = open(OUT, "w", encoding="utf-8")
init(os.path.join(os.path.dirname(OUT), "okprobe_driver.log"), hard_timeout_s=560)
T0 = time.time()
STATS = {}


def out(*a):
    fh.write(" ".join(str(x) for x in a) + "\n"); fh.flush()


def bb_chain(w):
    names = []
    while w is not None and len(names) < 6:
        names.append(type(w).__name__ + (":" + w.objectName() if w.objectName() else ""))
        w = w.parentWidget()
    return "/".join(names)


def visible_boxes():
    mw = Gui.getMainWindow()
    res = []
    for bb in mw.findChildren(QtWidgets.QDialogButtonBox):
        if bb.isVisible():
            btns = [b.text().replace("&", "") for b in bb.buttons() if b.isVisible()]
            res.append((bb, btns))
    return res


def instrumented_ok(tag):
    """fcui.ok() step by step, plus the facts behind a failure."""
    boxes = visible_boxes()
    clicked = None
    for bb, btns in boxes:
        for r in ("Ok", "Close"):
            b = bb.button(getattr(QtWidgets.QDialogButtonBox, r))
            if b is not None and b.isVisible() and b.isEnabled():
                clicked = (bb_chain(bb), r, btns)
                break
        if clicked:
            break
    t_click = time.time()
    r = press()
    ui()
    open1 = bool(Gui.Control.activeDialog())
    open2 = None
    if open1:
        ui(10)
        open2 = bool(Gui.Control.activeDialog())
    inedit = bool(Gui.ActiveDocument and Gui.ActiveDocument.getInEdit())
    t_gone = None
    if open2:
        # how long until it really goes (the fcui check would have filed the stumble here)
        end = time.time() + 3.0
        while time.time() < end:
            QtWidgets.QApplication.processEvents(); time.sleep(0.005)
            if not Gui.Control.activeDialog():
                t_gone = time.time() - t_click
                break
    return {"pressed": r, "clicked": clicked, "n_visible_boxes": len(boxes), "open_after_ui": open1,
            "stumble": bool(open2), "in_edit_after": inedit, "gone_after_s": t_gone}


def new_doc():
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
    ui()
    cmd("Std_New")
    return App.ActiveDocument


def sketch_circle(sk, x, y, d):
    p = V(x, y, 0)
    gi = sk.addGeometry(Part.Circle(V(p.x, p.y, 0), V(0, 0, 1), d / 2), False)
    sk.addConstraint([Sketcher.Constraint("Diameter", gi, d),
                      Sketcher.Constraint("DistanceX", -1, 1, gi, 3, p.x),
                      Sketcher.Constraint("DistanceY", -1, 1, gi, 3, p.y)])


def close_and_check(sk, variant, i):
    sk.Document.recompute(); ui()
    try:
        sk.solve()
    except Exception:
        pass
    res = instrumented_ok(variant)
    res.update({"variant": variant, "i": i, "t": round(time.time() - T0, 2)})
    out("ITER", json.dumps(res, ensure_ascii=False))
    s = STATS.setdefault(variant, [0, 0, 0])
    s[0] += 1
    s[1] += int(res["stumble"])
    s[2] += int(res["in_edit_after"])
    if res["stumble"]:
        Gui.Control.closeDialog(); ui()
    return res


def pad_of(sk, length):
    new = cmd("PartDesign_Pad", sk)
    pad = one(new, "PartDesign::Pad", "okprobe")
    ok("okprobe")
    if pad is not None:
        pad.Length = length
        recompute("okprobe")
    return pad


def v_circle_yz(i):
    """s40 of run_asm.log: new Body, sketch on its YZ plane, one circle with 3 constraints, OK."""
    b = body_new("okprobe", f"Stopper {i}")
    sk = new_sketch("okprobe", origin_feature(b, "YZ_Plane"))
    sketch_circle(sk, 7.2, 7.5, 4.6)
    close_and_check(sk, "circle_yz", i)


def v_rect_yz(i):
    """current scenario_vr6.py s40: plate rectangle on YZ."""
    b = body_new("okprobe", f"Plate {i}")
    sk = new_sketch("okprobe", origin_feature(b, "YZ_Plane"))
    rect(sk, 0.5, 1.0, 13.9, 14.0)
    close_and_check(sk, "rect_yz", i)


def v_face(i):
    """sketch on a face of a Pad, then OK (s40 later sketches)."""
    b = body_new("okprobe", f"Faced {i}")
    sk = new_sketch("okprobe", origin_feature(b, "YZ_Plane"))
    rect(sk, 0.5, 1.0, 13.9, 14.0)
    close_sketch(sk, "okprobe")
    pad = pad_of(sk, 1.9)
    if pad is None:
        return
    face = face_by(pad, V(1, 0, 0), V(1.9, 0, 0))
    sk2 = new_sketch("okprobe", (pad, face))
    p = to_local(sk2, V(1.9, 7.2, 7.5))
    sketch_circle(sk2, p.x, p.y, 4.6)
    close_and_check(sk2, "face", i)


def v_after_pattern(i):
    """s30 then s40 of run_asm.log: two Revolutions + a LinearPattern of both (heavier recompute), then the
    stopper body and its sketch."""
    b = body_new("okprobe", f"Rollers {i}")
    revs = []
    for k, x0 in enumerate((3.0, 13.0)):
        sk = new_sketch("okprobe", origin_feature(b, "XY_Plane"))
        polyline(sk, [(x0, 0), (x0 + 6, 0), (x0 + 6, 3), (x0, 3)])
        close_sketch(sk, "okprobe")
        new = cmd("PartDesign_Revolution", sk)
        rv = one(new, "PartDesign::Revolution", "okprobe")
        ok("okprobe")
        if rv is None:
            return
        rv.ReferenceAxis = (sk, ["H_Axis"])
        recompute("okprobe")
        revs.append(rv)
    new = cmd("PartDesign_LinearPattern", *revs)
    lp = one(new, "PartDesign::LinearPattern", "okprobe")
    ok("okprobe")
    if lp is not None:
        lp.Occurrences = 12
        lp.Length = 220
        recompute("okprobe")
    b2 = body_new("okprobe", f"Stopper after pattern {i}")
    sk = new_sketch("okprobe", origin_feature(b2, "YZ_Plane"))
    sketch_circle(sk, 7.2, 7.5, 4.6)
    close_and_check(sk, "after_pattern", i)


def v_circle_xy_keepsel(i):
    """like circle_yz but the plane stays selected and the tree has focus as after a tree click."""
    b = body_new("okprobe", f"KeepSel {i}")
    pl = origin_feature(b, "XY_Plane")
    sk = new_sketch("okprobe", pl)
    select((b, pl.Name + "."))
    sketch_circle(sk, 5, 5, 3)
    close_and_check(sk, "circle_xy_keepsel", i)


FUN = {"circle_yz": v_circle_yz, "rect_yz": v_rect_yz, "face": v_face, "after_pattern": v_after_pattern,
       "circle_xy_keepsel": v_circle_xy_keepsel}


@step
def s_all():
    Gui.activateWorkbench("PartDesignWorkbench"); ui()
    for v in VARIANTS:
        new_doc()                            # one document per variant, bodies accumulate as in the scenario
        n = N if v != "after_pattern" else max(5, N // 3)
        for i in range(n):
            try:
                FUN[v](i)
            except Exception:
                out("ITER-ERROR", v, i, traceback.format_exc().replace("\n", " | ")[-700:])
                try:
                    if Gui.Control.activeDialog():
                        Gui.Control.closeDialog()
                except Exception:
                    pass
        try:
            App.ActiveDocument.recompute()
        except Exception:
            pass
    for v, (n, st, ie) in STATS.items():
        out("SUMMARY", v, "closes", n, "stumbles", st, "in_edit_after", ie)
    out("FCUI-STUMBLES", len(fcui.STUMBLES), json.dumps(fcui.STUMBLES, ensure_ascii=False)[:1500])
    out("PROBE-DONE", f"{time.time() - T0:.1f}s")
    fh.flush()
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)


run([s_all])
