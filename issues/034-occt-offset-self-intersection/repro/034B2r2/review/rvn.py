# rvn.py - Review offset-B2 r2: class members NOT tested by the implementer (r1c fam3, r2 more.txt) nor by review r1.
# References only from primitives + Booleans (erosion by half-planes / stadium subtraction); partial folds: no
# closed-form reference -> result must be an ERROR or pass the error-raising distance control.
# Env FC_OUT, RV_SET.
#HELPERS

def variants3(k):
    return (("a", k), ("n", k.toNurbs()), ("w", rot(k)))

# ---------------------------------------------------------------- W: acute wedge prism, filleted vertical edges
# apex angle alpha; the corner of the rim offsets lies (d - r) / tan(alpha/2) beyond the stock section end.
if want("wedge"):
    for (alpha, B, H, r, ts) in ((45., 16., 10., 1., (1.5, 3.0)), (30., 16., 10., 1., (1.5, 3.0)), (20., 16., 6., 1., (1.5, 3.0))):
        h = (B / 2) / math.tan(math.radians(alpha / 2))
        P = [(0., 0.), (B, 0.), (B / 2, h)]
        s0 = prism_xy(P, 0., H)
        k = s0.makeFillet(r, vert_edges_at(s0, P))
        say("# wedge alpha=%g h=%.3f H=%g faces=%d vol=%.5f" % (alpha, h, H, len(k.Faces), k.Volume))
        for t in ts:
            need = (t - r) / math.tan(math.radians(alpha / 2))
            ref_off = prism_xy(conv_erode(P, t), t, H - t) if 2 * t < H else None
            cav = prism_xy(conv_erode(P, t), t, H + 1)
            for vn, s in (variants3(k) if ref_off is not None else ()):
                run("wedge%g_r%g_d%g_%s_off" % (alpha, r, t, vn), lambda: s.makeOffsetShape(-t, 1e-7, join=0), rot(ref_off) if vn == "w" else ref_off)
            for vn, s in variants3(k):
                refT = (rot(k) if vn == "w" else k).cut(rot(cav) if vn == "w" else cav)
                run("wedge%g_r%g_t%g_%s_thktop_need%.2f" % (alpha, r, t, vn, need), lambda: s.makeThickness([topface(s, vn)], -t, 1e-7, False, False, 0, 0), refT)

# ---------------------------------------------------------------- W2: extreme acute wedges, short height: corner far beyond "set size + |d|"
if want("wedge2"):
    for (alpha, B, H, r, ts) in ((10., 8., 4., 1., (2.5, 3.0)), (14., 8., 5., 1., (3.0,))):
        h = (B / 2) / math.tan(math.radians(alpha / 2))
        P = [(0., 0.), (B, 0.), (B / 2, h)]
        s0 = prism_xy(P, 0., H)
        k = s0.makeFillet(r, vert_edges_at(s0, P))
        say("# wedge2 alpha=%g h=%.3f H=%g faces=%d vol=%.5f" % (alpha, h, H, len(k.Faces), k.Volume))
        for t in ts:
            need = (t - r) / math.tan(math.radians(alpha / 2)); reach = math.sqrt(H * H + (2 * r * math.cos(math.radians(alpha / 2))) ** 2) + t
            cav = prism_xy(conv_erode(P, t), t, H + 1)
            for vn, s in (("a", k), ("w", rot(k))):
                refT = (rot(k) if vn == "w" else k).cut(rot(cav) if vn == "w" else cav)
                run("wedge%g_r%g_t%g_%s_thktop_need%.1f_reach%.1f" % (alpha, r, t, vn, need, reach), lambda: s.makeThickness([topface(s, vn)], -t, 1e-7, False, False, 0, 0), refT)

# ---------------------------------------------------------------- X: regular hexagon prism, filleted vertical edges; top / top+side removed
if want("hex"):
    R, H, r = 10., 10., 1.
    P = [(R * math.cos(math.radians(60 * i)), R * math.sin(math.radians(60 * i))) for i in range(6)]
    s0 = prism_xy(P, 0., H)
    k = s0.makeFillet(r, vert_edges_at(s0, P))
    say("# hex faces=%d vol=%.5f" % (len(k.Faces), k.Volume))
    # side 0 = P0->P1, outward normal at angle 30 deg
    sn = V(math.cos(math.radians(30)), math.sin(math.radians(30)), 0)
    for t in (1.5, 3.0):
        ref_off = prism_xy(conv_erode(P, t), t, H - t)
        for vn, s in variants3(k):
            run("hex_r1_d%g_%s_off" % (t, vn), lambda: s.makeOffsetShape(-t, 1e-7, join=0), rot(ref_off) if vn == "w" else ref_off)
        cav = prism_xy(conv_erode(P, t), t, H + 1)
        cav2 = prism_xy(conv_erode(P, t, opened=(0,)), t, H + 1)
        for vn, s in variants3(k):
            kk = rot(k) if vn == "w" else k
            refT = kk.cut(rot(cav) if vn == "w" else cav)
            run("hex_r1_t%g_%s_thktop" % (t, vn), lambda: s.makeThickness([topface(s, vn)], -t, 1e-7, False, False, 0, 0), refT)
            nax = sn if vn != "w" else App.Placement(ROT).Rotation.multVec(sn)
            side = max([f for f in s.Faces if f.Surface.__class__.__name__ in ("Plane", "BSplineSurface") and f.Area > 20], key=lambda f: f.CenterOfMass.dot(nax))
            refT2 = kk.cut(rot(cav2) if vn == "w" else cav2)
            run("hex_r1_t%g_%s_thk_TOP+SIDE" % (t, vn), lambda: s.makeThickness([topface(s, vn), side], -t, 1e-7, False, False, 0, 0), refT2)

# ---------------------------------------------------------------- T: T-shaped housing, convex vertical edges filleted, reflex sharp
if want("tee"):
    H, r = 10., 1.
    P = [(12., 0.), (18., 0.), (18., 10.), (30., 10.), (30., 16.), (0., 16.), (0., 10.), (12., 10.)]
    conv = [(12., 0.), (18., 0.), (30., 10.), (30., 16.), (0., 16.), (0., 10.)]
    s0 = prism_xy(P, 0., H)
    k = s0.makeFillet(r, vert_edges_at(s0, conv))
    say("# tee faces=%d vol=%.5f" % (len(k.Faces), k.Volume))
    for t in (1.5, 2.5):
        ref_off = poly_erode_prism(P, t, t, H - t)
        for vn, s in variants3(k):
            run("tee_r1_d%g_%s_off" % (t, vn), lambda: s.makeOffsetShape(-t, 1e-7, join=0), rot(ref_off) if vn == "w" else ref_off)
        cav = poly_erode_prism(P, t, t, H + 1)
        for vn, s in variants3(k):
            kk = rot(k) if vn == "w" else k
            run("tee_r1_t%g_%s_thktop" % (t, vn), lambda: s.makeThickness([topface(s, vn)], -t, 1e-7, False, False, 0, 0), kk.cut(rot(cav) if vn == "w" else cav))
    # control below the radius (no vanishing): must stay as A2
    run("CTL_tee_r1_t0.5_a_thktop_NOVANISH", lambda: k.makeThickness([topface(k, "a")], -0.5, 1e-7, False, False, 0, 0), None)

# ---------------------------------------------------------------- E: elliptic cylinder, PARTIAL fold (b^2/a < d < a^2/b): error or control-clean
if want("ell"):
    a, b, H = 10., 4., 8.
    el = Part.Ellipse(V(0, 0, 0), a, b)
    f = Part.Face(Part.Wire(el.toShape()))
    k = f.extrude(V(0, 0, H))
    say("# ellipse min radius %.3f max %.3f faces %s" % (b * b / a, a * a / b, [x.Surface.__class__.__name__ for x in k.Faces]))
    for vn, s in (("a", k), ("n", k.toNurbs())):
        for d in (1.0, 2.0, 3.0):
            tag = "CTL" if d < b * b / a else "PARTIAL"
            rr = run("ell_%s_d%g_%s_off" % (tag, d, vn), lambda: s.makeOffsetShape(-d, 1e-7, join=0), None)
            say("   ", oracle_offset(rr, s, d))
            top = max(s.Faces, key=lambda x: x.CenterOfMass.z)
            rr = run("ell_%s_t%g_%s_thktop" % (tag, d, vn), lambda: s.makeThickness([top], -d, 1e-7, False, False, 0, 0), None)
            say("   ", oracle_thick(rr, s, d))

# ---------------------------------------------------------------- V: variable-radius fillet 1->3 crossing d=2 on a TOP edge + vertical r1 (partial fold + vanishing mixed)
if want("vmix"):
    L, W, H = 20., 14., 10.
    b = box(0, 0, 0, L, W, H)
    k = b.makeFillet(1.0, [e for e in b.Edges if e.BoundBox.ZLength > 1e-3 and e.BoundBox.XLength < 1e-7 and e.BoundBox.YLength < 1e-7])
    say("# vmix faces=%d" % len(k.Faces))
    for d in (1.5,):
        top = max(k.Faces, key=lambda x: x.CenterOfMass.z)
        # remove the bottom: walls AND the top keep thickness, vertical blends vanish
        bot = min(k.Faces, key=lambda x: x.CenterOfMass.z)
        ref = k.cut(box(d, d, -1, L - d, W - d, H - d))
        for vn, s in variants3(k):
            zax = V(0, 0, 1) if vn != "w" else App.Placement(ROT).Rotation.multVec(V(0, 0, 1))
            bb = min(s.Faces, key=lambda x: x.CenterOfMass.dot(zax))
            run("vbox_r1_t%g_%s_thkBOTTOM" % (d, vn), lambda: s.makeThickness([bb], -d, 1e-7, False, False, 0, 0), rot(ref) if vn == "w" else ref)
        # join=Intersection on the offset (review r1: ERR; still no vanishing path)
        run("vbox_r1_d%g_n_off_JOIN_INT" % d, lambda: k.toNurbs().makeOffsetShape(-d, 1e-7, join=2), box(d, d, d, L - d, W - d, H - d))

# ---------------------------------------------------------------- NEG: grader must flag a shifted reference on a new member
if want("neg"):
    P = [(R * math.cos(math.radians(60 * i)), R * math.sin(math.radians(60 * i))) for R in (10.,) for i in range(6)]
    s0 = prism_xy(P, 0., 10.)
    k = s0.makeFillet(1.0, vert_edges_at(s0, P))
    cav = prism_xy(conv_erode(P, 1.5 + 1e-3), 1.5, 11.)
    run("NEG_hex_t1.5_ref_eroded_by_1.501", lambda: k.makeThickness([topface(k, "a")], -1.5, 1e-7, False, False, 0, 0), k.cut(cav))
say("RV-DONE")
out.close()
