# idc.py <int file> <r3 file> [--neg] : line-by-line identity after stripping volatile fields (as offset-034int idcmp norm)
import sys, re
V = re.compile(r"\b(ms|msO|chkus|bopus|peakMB|rel|relc)=\S+")
def L(p): return [re.sub(r"\s+", " ", V.sub("", l.replace("(cache)", "").strip())) for l in open(p, errors="replace") if l.strip()]
a, b = L(sys.argv[1]), L(sys.argv[2])
if "--neg" in sys.argv: b[0] = b[0] + " X"
d = [(x, y) for x, y in zip(a, b) if x != y]
print(sys.argv[2].split("/")[-1], len(a), len(b), "diff", len(d))
for x, y in d[:8]: print(" INT", x[:200]); print(" R3 ", y[:200])
