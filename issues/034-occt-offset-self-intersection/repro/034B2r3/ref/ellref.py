# ellref.py a b r H : exact volume of the inward offset (erosion by r) of the elliptic cylinder a,b,height H
# (test side). Inner parallel curve q(t) = p(t) - r n(t); for b^2/a < r < b it self-intersects on the major axis;
# the kept part is t in [t*, pi - t*] mirrored (y>0 half, Green's theorem) - t* solves q_y(t)=0, t in (0, pi/2).
import sys, math
from scipy.integrate import quad
from scipy.optimize import brentq
a, b, r, H = map(float, sys.argv[1:5])
def q(t):
    x, y = a*math.cos(t), b*math.sin(t)
    nx, ny = b*math.cos(t), a*math.sin(t)
    m = math.hypot(nx, ny)
    return x - r*nx/m, y - r*ny/m
def dq(t, h=1e-6):
    # analytic derivative: q'(t) = p'(t) (1 - r k(t)) ; p' = (-a sin, b cos), k = ab / m^3
    nx, ny = b*math.cos(t), a*math.sin(t); m = math.hypot(nx, ny)
    k = a*b/m**3; s = 1 - r*k
    return -a*math.sin(t)*s, b*math.cos(t)*s
if r <= b*b/a:
    t0 = 0.0
else:
    t0 = brentq(lambda t: q(t)[1], 1e-12, math.pi/2 - 1e-12, xtol=1e-15)
# upper half area: region above y=0 bounded by q on [t0, pi-t0] (counter-clockwise) and the axis segment
f = lambda t: (q(t)[0]*dq(t)[1] - q(t)[1]*dq(t)[0]) * 0.5
A_half, err = quad(f, t0, math.pi - t0, epsabs=1e-14, epsrel=1e-14, limit=500)
# closing segment on y=0 from q(pi-t0) to q(t0) contributes x dy - y dx = 0
A = 2*A_half
print("t*=%.12f x*=%.12f area=%.12f vol=%.9f" % (t0, q(t0)[0], A, A*(H - 2*r)))
