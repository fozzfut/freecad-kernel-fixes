import sys, hashlib
a = open(sys.argv[1], 'rb').read(); b = open(sys.argv[2], 'rb').read()
print('md5', hashlib.md5(a).hexdigest(), hashlib.md5(b).hexdigest(), 'size', len(a), len(b))
if len(a) == len(b):
    d = [i for i in range(len(a)) if a[i] != b[i]]
    print('differing bytes', len(d), 'offsets', [hex(x) for x in d[:16]])
