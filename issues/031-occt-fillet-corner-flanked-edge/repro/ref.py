# ref.py: exact rolling-ball (morphological opening, Rossignac-Requicha) reference for a "ridge" vertex: two convex
# blended edges A (faces W1,W2) and B (faces R1,R2) meeting at V with two concave sharp edges W1|R1, W2|R2.
# The ball centre path solves d(c, K1) = r and d(c, K2) = r, K1/K2 = the convex outside wedges behind the sharp
# edges; the exact corner is the pipe of radius r along that path (a canal surface). Planar faces only.
import math
import numpy as np
import FreeCAD as App, Part
V = App.Vector

def outward_plane(face):
    u0, u1, v0, v1 = face.ParameterRange
    n = face.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    P = face.Surface.Position
    return (np.array([P.x, P.y, P.z]), np.array([n.x, n.y, n.z]))

def wedge_foot(c, P1, n1, P2, n2):
    """closest point of the convex wedge {(p-P1).n1>=0, (p-P2).n2>=0} to c (c outside it); returns (dist, foot, kind)"""
    s1 = (c - P1).dot(n1); s2 = (c - P2).dot(n2)
    best = (1e30, None, None)
    q1 = c - n1 * s1
    if (q1 - P2).dot(n2) >= -1e-12 and abs(s1) < best[0]: best = (abs(s1), q1, 1)
    q2 = c - n2 * s2
    if (q2 - P1).dot(n1) >= -1e-12 and abs(s2) < best[0]: best = (abs(s2), q2, 2)
    d = np.cross(n1, n2); d = d / np.linalg.norm(d)
    q = np.linalg.solve(np.array([n1, n2, d]), np.array([P1.dot(n1), P2.dot(n2), c.dot(d)]))
    dq = np.linalg.norm(c - q)
    if dq < best[0]: best = (dq, q, 0)
    return best

class Ridge:
    def __init__(self, W1, R1, W2, R2, r, Vx):
        self.W1, self.R1, self.W2, self.R2, self.r = W1, R1, W2, R2, r
        self.V = np.array([Vx.x, Vx.y, Vx.z])
    def ev(self, c):
        d1, f1, k1 = wedge_foot(c, self.W1[0], self.W1[1], self.R1[0], self.R1[1])
        d2, f2, k2 = wedge_foot(c, self.W2[0], self.W2[1], self.R2[0], self.R2[1])
        return d1 - self.r, d2 - self.r, (c - f1) / d1, (c - f2) / d2, (f1, k1, f2, k2)
    def correct(self, c):
        for it in range(40):
            g1, g2, a, b, _ = self.ev(c)
            if abs(g1) < 1e-12 and abs(g2) < 1e-12: break
            aa, ab, bb = a.dot(a), a.dot(b), b.dot(b); det = aa * bb - ab * ab
            l1 = (bb * g1 - ab * g2) / det; l2 = (aa * g2 - ab * g1) / det
            c = c - a * l1 - b * l2
        return c
    def trace(self, dirA, span=4.0, h=None):
        r = self.r; h = h or r / 200.0
        dirA = np.array(dirA)
        c = self.correct(self.V - dirA * (span * r) - (self.W1[1] + self.W2[1]) * r)
        pts = [c]; t = dirA; kinds = []
        for k in range(int(8 * span * r / h)):
            g1, g2, a, b, info = self.ev(c)
            tn = np.cross(a, b); tn = tn / np.linalg.norm(tn)
            if tn.dot(t) < 0: tn = -tn
            t = tn
            c = self.correct(c + t * h)
            pts.append(c); kinds.append((info[1], info[3]))
            if np.linalg.norm(c - self.V) > span * r and k > 50: break
        self.path = np.array(pts); self.kinds = kinds
        return self.path
    def dev(self, P):
        """P: (M,3) points -> distance to the centre polyline minus r"""
        A = self.path[:-1]; B = self.path[1:]; AB = B - A; L2 = (AB * AB).sum(1)
        out = np.empty(len(P))
        for i in range(0, len(P), 256):
            p = P[i:i + 256][:, None, :]
            t = np.clip(((p - A[None]) * AB[None]).sum(2) / L2[None], 0, 1)
            q = A[None] + t[..., None] * AB[None]
            out[i:i + 256] = np.sqrt(((p - q) ** 2).sum(2)).min(1)
        return out - self.r

def ridge_from_shape(ch, vert_idx, miter_idx, r):
    ve = ch.Edges[vert_idx - 1]; me = ch.Edges[miter_idx - 1]
    Vx = [v for v in ve.Vertexes if any(v.isSame(w) for w in me.Vertexes)][0]
    fa = [f for f in ch.Faces if any(e.isSame(ve) for e in f.Edges)]
    fb = [f for f in ch.Faces if any(e.isSame(me) for e in f.Edges)]
    def share(f, g): return any(e.isSame(x) for e in f.Edges for x in g.Edges)
    W1, W2 = fa; R1 = [f for f in fb if share(f, W1)][0]; R2 = [f for f in fb if not f.isSame(R1)][0]
    return Ridge(outward_plane(W1), outward_plane(R1), outward_plane(W2), outward_plane(R2), r, V(Vx.Point)), ve

def face_dev(rg, face, defl=0.01):
    pts, tris = face.tessellate(defl)
    P = np.array([[p.x, p.y, p.z] for p in pts])
    d = rg.dev(P)
    return float(np.abs(d).max()), len(pts)
