import pefile, hashlib, sys
def secs(p):
    pe = pefile.PE(p); return {s.Name.rstrip(b'\0').decode(): (s.SizeOfRawData, hashlib.md5(s.get_data()).hexdigest()) for s in pe.sections}
a, b = secs(sys.argv[1]), secs(sys.argv[2])
import os; print("size", os.path.getsize(sys.argv[1]), os.path.getsize(sys.argv[2]))
for k in sorted(set(a) | set(b)): print(k, a.get(k), b.get(k), "SAME" if a.get(k) == b.get(k) else "DIFF")
