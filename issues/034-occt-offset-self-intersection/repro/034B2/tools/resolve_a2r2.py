"""resolve_a2r2.py: resolves the 3-way merge of B2 r1 (32aed017) onto A2 r2 (7192f9ea): keep both insertions.
Hunk 1 (static helpers after hasNoFace034): A2 block, then B2 block. Hunk 2 (end of MakeOffsetShape): A2 check
(closed by its own brace), then the B2 check (closed by the common brace that follows the markers)."""
src = 'C:/dev/occt8-mig/offset-034b2/build/merge-conflict.cxx'
dst = 'C:/dev/occt8-mig/offset-034b2/build/merged-a2r2-b2.cxx'
lines = open(src, encoding='utf-8', newline='').read().split('\n')
out, i, hunk = [], 0, 0
while i < len(lines):
    l = lines[i]
    if l.startswith('<<<<<<< '):
        hunk += 1
        ours, theirs = [], []
        i += 1
        while not lines[i].startswith('======='):
            ours.append(lines[i]); i += 1
        i += 1
        while not lines[i].startswith('>>>>>>> '):
            theirs.append(lines[i]); i += 1
        i += 1
        if hunk == 1:
            out += ours + ['', '//======================================================================='] + theirs
        else:
            out += ours + ['  }'] + theirs
        continue
    out.append(l)
    i += 1
assert hunk == 2
open(dst, 'w', encoding='utf-8', newline='').write('\n'.join(out))
print('resolved', hunk)
