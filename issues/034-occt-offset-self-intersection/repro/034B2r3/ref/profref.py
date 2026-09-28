# profref.py - issue 034 B2 r3 test-side EXACT references for prisms over a graph profile (NOT kernel code).
#
# The solid is P x [0, Lp]: P = {(x, z): 0 <= x <= L, 0 <= z <= h(x)}, the top profile a clamped cubic B-spline
# c(t) = (x(t), z(t)) with x(t) increasing (evaluated here with scipy, independently of OCCT).
#
#   inward offset by r (erosion):  (P ⊖ B_r) x [r, Lp - r], area of P ⊖ B_r = ∫_{r}^{L-r} (g(x) - r) dx,
#       g(x) = min over t with |x(t) - x| <= r of  z(t) - sqrt(r^2 - (x(t) - x)^2)       (disc under the graph)
#   outward offset by r (dilation, ball): dist((p,y), P x [0,Lp])^2 = dist(p,P)^2 + dist(y,[0,Lp])^2, so
#       V = Lp * A(r) + 2 * ∫_0^r A(sqrt(r^2 - s^2)) ds,  A(s) = area of P ⊕ B_s = ∫_{-s}^{L+s} (U_s(x) - D_s(x)) dx,
#       U_s(x) = max over the top curve AND the two side segments of (z' + sqrt(s^2 - (x - x')^2)),
#       D_s(x) = -sqrt(s^2 - dist_x(x, [0, L])^2)   (the section of P ⊕ B_s at x is one interval: all contain z = 0).
# Kinks of g / U (where the arg-min jumps: the self-intersection points of the offset curve) are located by
# bisection and the integrals are Gauss-Legendre on the smooth pieces.
#
# usage: profref.py wave <amp> <per> <np> <L=40> <Lp=20> <r> in|out
#        profref.py ridge <h> <sharp> <n> <W=30> <Lp=40> <r> in|out     (the ridge profile runs along y)
import sys, math
import numpy as np
from scipy.interpolate import BSpline
from scipy.optimize import minimize_scalar


def clamped_cubic(px, pz):
    n = len(px)
    nk = n - 2
    kn = [0.0] * 3 + [float(i) for i in range(nk)] + [float(nk - 1)] * 3
    t = np.array(kn)
    return BSpline(t, np.array(px), 3), BSpline(t, np.array(pz), 3), float(nk - 1)


def make_profile(argv):
    fam = argv[0]
    if fam == "wave":
        amp, per, npole, L, Lp = float(argv[1]), float(argv[2]), int(argv[3]), float(argv[4]), float(argv[5])
        px = [L * i / (npole - 1) for i in range(npole)]
        pz = [10.0 + amp * math.cos(2 * math.pi * x / per) for x in px]
        rest = argv[6:]
    elif fam == "ridge":
        h, sh, n, L, Lp = float(argv[1]), float(argv[2]), int(argv[3]), float(argv[4]), float(argv[5])
        px = [L * j / (n - 1) for j in range(n)]
        pz = [10.0 + h * math.exp(-sh * ((y - L / 2) / (L / 2)) ** 2) for y in px]
        rest = argv[6:]
    else:
        raise SystemExit("unknown family")
    bx, bz, tmax = clamped_cubic(px, pz)
    return bx, bz, tmax, L, Lp, float(rest[0]), rest[1]


class Prof:
    def __init__(self, bx, bz, tmax, L):
        self.bx, self.bz, self.tmax, self.L = bx, bz, tmax, L
        self.T = np.linspace(0.0, tmax, 200001)
        self.X = bx(self.T)
        self.Z = bz(self.T)
        assert np.all(np.diff(self.X) > 0), "x(t) must increase"

    def t_of_x(self, x):
        i = np.searchsorted(self.X, x)
        i = min(max(i, 1), len(self.X) - 1)
        t = self.T[i - 1] + (self.T[i] - self.T[i - 1]) * (x - self.X[i - 1]) / (self.X[i] - self.X[i - 1])
        for _ in range(30):
            f = float(self.bx(t)) - x
            d = float(self.bx(t, 1))
            t -= f / d
            if abs(f) < 1e-15:
                break
        return min(max(t, 0.0), self.tmax)

    # erosion: g(x) and the arg-min t
    def g(self, x, r):
        ta, tb = self.t_of_x(max(x - r, 0.0)), self.t_of_x(min(x + r, self.L))
        m = (self.T >= ta) & (self.T <= tb)
        Ts = self.T[m]
        v = self.Z[m] - np.sqrt(np.maximum(r * r - (self.X[m] - x) ** 2, 0.0))
        best = None
        order = np.argsort(v)[:3]
        f = lambda t: float(self.bz(t)) - math.sqrt(max(r * r - (float(self.bx(t)) - x) ** 2, 0.0))
        for k in order:
            k0, k1 = max(k - 2, 0), min(k + 2, len(Ts) - 1)
            res = minimize_scalar(f, bounds=(Ts[k0], Ts[k1]), method="bounded", options={"xatol": 1e-13})
            cand = (res.fun, res.x)
            if best is None or cand[0] < best[0]:
                best = cand
        # the ends of the admissible range
        for t in (ta, tb):
            c = (f(t), t)
            if c[0] < best[0]:
                best = c
        return best

    # dilation upper envelope U_s(x) and the arg-max (curve parameter, or -1/-2 for the side segments)
    def U(self, x, s):
        cands = []
        # side segments x' = 0 (z' in [0, z(0)]) and x' = L: the top end point dominates (z' max)
        lo, hi = max(x - s, 0.0), min(x + s, self.L)
        if hi < lo:
            return (-math.inf, None)
        ta, tb = self.t_of_x(lo), self.t_of_x(hi)
        m = (self.T >= ta) & (self.T <= tb)
        Ts = self.T[m]
        if len(Ts) == 0:
            Ts = np.array([ta, tb])
        v = self.bz(Ts) + np.sqrt(np.maximum(s * s - (self.bx(Ts) - x) ** 2, 0.0))
        f = lambda t: -(float(self.bz(t)) + math.sqrt(max(s * s - (float(self.bx(t)) - x) ** 2, 0.0)))
        best = None
        for k in np.argsort(-v)[:3]:
            k0, k1 = max(k - 2, 0), min(k + 2, len(Ts) - 1)
            if Ts[k1] > Ts[k0]:
                res = minimize_scalar(f, bounds=(Ts[k0], Ts[k1]), method="bounded", options={"xatol": 1e-13})
                c = (-res.fun, res.x)
            else:
                c = (-f(Ts[k0]), Ts[k0])
            if best is None or c[0] > best[0]:
                best = c
        for t in (ta, tb):
            c = (-f(t), t)
            if c[0] > best[0]:
                best = c
        return best


def gl_integrate(fun, a, b, n=64, pieces=64):
    xs, ws = np.polynomial.legendre.leggauss(n)
    tot = 0.0
    edges = np.linspace(a, b, pieces + 1)
    for i in range(pieces):
        c, h = 0.5 * (edges[i] + edges[i + 1]), 0.5 * (edges[i + 1] - edges[i])
        tot += h * sum(w * fun(c + h * x) for x, w in zip(xs, ws))
    return tot


def split_kinks(argfun, a, b, n=4001, tol=1e-12):
    xs = np.linspace(a, b, n)
    ts = [argfun(x) for x in xs]
    cuts = [a]
    steps = [abs(ts[i + 1] - ts[i]) for i in range(n - 1) if ts[i] is not None and ts[i + 1] is not None]
    typ = float(np.median(steps)) if steps else 0.0
    for i in range(n - 1):
        if ts[i] is None or ts[i + 1] is None:
            continue
        if abs(ts[i + 1] - ts[i]) > 20 * typ + 1e-9:  # arg jumps: a kink between
            lo, hi, tlo = xs[i], xs[i + 1], ts[i]
            while hi - lo > tol:
                mid = 0.5 * (lo + hi)
                tm = argfun(mid)
                if abs(tm - tlo) < abs(tm - ts[i + 1]):
                    lo = mid
                else:
                    hi = mid
            cuts.append(0.5 * (lo + hi))
    cuts.append(b)
    return cuts


def erosion_area(P, r):
    a, b = r, P.L - r
    cuts = split_kinks(lambda x: P.g(x, r)[1], a, b)
    area = 0.0
    for i in range(len(cuts) - 1):
        area += gl_integrate(lambda x: P.g(x, r)[0] - r, cuts[i], cuts[i + 1], n=48, pieces=24)
    return area, len(cuts) - 2


def dilation_area(P, s):
    a, b = -s, P.L + s
    cuts = split_kinks(lambda x: P.U(x, s)[1], a, b, n=1001)
    # the lower envelope has kinks at 0 and L
    cuts = sorted(set(cuts + [0.0, P.L]))
    def integrand(x):
        dx = 0.0 if 0.0 <= x <= P.L else (-x if x < 0 else x - P.L)
        low = -math.sqrt(max(s * s - dx * dx, 0.0))
        return P.U(x, s)[0] - low
    area = 0.0
    for i in range(len(cuts) - 1):
        area += gl_integrate(integrand, cuts[i], cuts[i + 1], n=24, pieces=8)
    return area


if __name__ == "__main__":
    bx, bz, tmax, L, Lp, r, mode = make_profile(sys.argv[1:])
    P = Prof(bx, bz, tmax, L)
    if mode == "in":
        A, nk = erosion_area(P, r)
        print("erosion area=%.12f kinks=%d volume=%.9f" % (A, nk, A * (Lp - 2 * r)))
    else:
        A0 = dilation_area(P, r)
        xs, ws = np.polynomial.legendre.leggauss(16)
        # ∫_0^r A(sqrt(r^2-s^2)) ds with s = r sin(phi): ds = r cos(phi) dphi, phi in [0, pi/2] (smooth)
        tot = 0.0
        for x, w in zip(xs, ws):
            ph = 0.25 * math.pi * (x + 1)
            tot += 0.25 * math.pi * w * dilation_area(P, r * math.cos(ph)) * r * math.cos(ph)
        V = Lp * A0 + 2 * tot
        print("dilation area=%.12f volume=%.9f" % (A0, V))
