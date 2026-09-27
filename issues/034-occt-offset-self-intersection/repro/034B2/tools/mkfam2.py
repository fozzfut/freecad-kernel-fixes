"""mkfam2.py: family 2 = thick solids (PD Thickness path) of rounded boxes and bosses whose blends vanish.
rbox 20x14x10 filleted r (a = analytic, n = NURBS, m = NURBS split C1), placements 0/1/2, thick -t with the bottom face
removed ("largest" = the z=0 face, checked in the harness output rem=), t in {0.5r (control, not in class), r, 1.5r, 3r};
reference solid for t > r = rbox minus the sharp cavity [t,20-t]x[t,14-t]x[-1,10-t] (independent construction).
boss (plate 30x30x5 + cylinder R6 h6, concave root fillet r): thick +t with the bottom removed (outward shell)."""
import subprocess
C = 'C:/dev/occt8-mig/offset-034b2/cases'
R = 'C:/dev/occt8-mig/offset-034b2/tools/r.sh'
L = []
def gen(*a):
    subprocess.run(['bash', R, 'w', 'gen'] + [str(x) for x in a], stdout=subprocess.DEVNULL)
for r in (0.5, 1, 2):
    for v in 'anm':
        for p in (0, 1, 2):
            f = f'rbox_r{r}_{v}_p{p}.brep'
            gen('rbox', r, v, p, f'{C}/{f}')
            for m in (0.5, 1.0, 1.5, 3.0):
                t = round(m * r, 4)
                if 20 - 2 * t <= 0 or 10 - t <= 0:
                    continue
                ref = '-'
                if m > 1.0:
                    ref = f'ref_rboxthk_r{r}_t{t}_{v}_p{p}.brep'
                    gen('cutbox', f'{C}/{f}', t, t, -1, 20 - t, 14 - t, 10 - t, p, f'{C}/{ref}')
                L.append(f'rbox{r}{v}p{p}_thk-{t:g} {f} thick -{t} arc largest 0 {ref}')
for r in (0.5, 1, 2):
    for v in 'am':
        for p in (0, 1, 2):
            f = f'boss_r{r}_{v}_p{p}.brep'
            for m in (0.5, 1.0, 1.5, 2.0):
                t = round(m * r, 4)
                L.append(f'boss{r}{v}p{p}_thk+{t:g} {f} thick {t} arc largest 0 -')
open('C:/dev/occt8-mig/offset-034b2/runs/fam2.txt', 'w').write('\n'.join(L) + '\n')
print(len(L))
