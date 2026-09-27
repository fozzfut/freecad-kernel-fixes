"""mkfam3.py: round-1 continuation families (vanishing blends whose sets end on SHARP edges without a tube).
Box 20x14x10 families (vbox 4 vertical fillets, tbox 4 top fillets, ebox 1 vertical fillet, vtbox 8 fillets),
tri (30/60/90 prism, 3 vertical fillets), tray (open pocket, concave vertical fillets, sharp floor); r in {1,2},
a = analytic / n = NURBS, placements 0/1. Offsets: inward -m*r for the convex families, outward +m*r for tray;
thick: inward -m*r with the largest (bottom) face removed; tray +m*r with the rim face (index 1) removed.
m in {0.5 (control, not in class), 1.0 (threshold), 1.01, 1.5, 3.0}. Reference solids (independent, booleans of
boxes) for the box families when m > 1: offset -> plain box [d,20-d]x[d,14-d]x[d,10-d]; thick -> member minus
[d,20-d]x[d,14-d]x[-1,10-d]."""
import subprocess
B = 'C:/dev/occt8-mig/offset-034b2/r1c/cases'
R = 'C:/dev/occt8-mig/offset-034b2/tools/r.sh'
L = []
def gen(*a):
    subprocess.run(['bash', R, 'w', 'gen'] + [str(x) for x in a], stdout=subprocess.DEVNULL)
for fam in ('vbox', 'tbox', 'ebox', 'vtbox', 'tri', 'tray'):
    for r in (1, 2):
        for v in 'an':
            for p in (0, 1):
                f = f'{B}/{fam}_r{r}_{v}_p{p}.brep'
                for m in (0.5, 1.0, 1.01, 1.5, 3.0):
                    d = round(m * r, 4)
                    box = fam in ('vbox', 'tbox', 'ebox', 'vtbox')
                    if fam == 'tray':
                        L.append(f'{fam}{r}{v}p{p}_off+{d:g} {f} offset {d} arc none')
                        L.append(f'{fam}{r}{v}p{p}_thk+{d:g} {f} thick {d} arc 1')
                        continue
                    ref_o = ref_t = '-'
                    if box and m > 1.0 and 10 - 2 * d > 0:
                        ref_o = f'{B}/ref_box_{d:g}_p{p}.brep'
                        gen('refbox', d, d, d, 20 - d, 14 - d, 10 - d, p, ref_o)
                        ref_t = f'{B}/ref_{fam}thk_r{r}_{v}_p{p}_{d:g}.brep'
                        # the removed ("largest") face: top (z=10) for vbox/ebox (tie, lowest index), bottom otherwise
                        if fam in ('vbox', 'ebox'):
                            gen('cutbox', f, d, d, d, 20 - d, 14 - d, 11, p, ref_t)
                        else:
                            gen('cutbox', f, d, d, -1, 20 - d, 14 - d, 10 - d, p, ref_t)
                    if fam == 'tri' and m > 1.0 and d < 20 * 0.2113:
                        # hypotenuse wall removed: cavity = {x>=d, y>=d} inside the triangle, z in [d, 10-d]
                        ref_t = f'{B}/ref_trithk_r{r}_{v}_p{p}_{d:g}.brep'
                        gen('cuttri', f, d, 10 - d, d, d, 40, d, d, 40, p, ref_t)
                    L.append(f'{fam}{r}{v}p{p}_off-{d:g} {f} offset -{d} arc none 0 {ref_o}')
                    L.append(f'{fam}{r}{v}p{p}_thk-{d:g} {f} thick -{d} arc largest 0 {ref_t}')
open('C:/dev/occt8-mig/offset-034b2/r1c/fam3.txt', 'w').write('\n'.join(L) + '\n')
print(len(L))
