import json, sys
runs = sys.argv[1:]
R = {m: json.load(open(m + "/probe.txt")) for m in runs}
ref = R[runs[0]]
for m, r in R.items():
    print(m, "hd=", r["hd"], "obs=", r["obs"], "cmd=", {k: (v["wrapper"] if isinstance(v, dict) else v) for k, v in r["cmd"].items()}, "errors=", [e[:120] for e in r["errors"]])
for sec in ("created", "restored"):
    diffs = []
    for t in ref[sec]:
        row = [(R[m][sec].get(t) or {}).get("wrapper") if isinstance(R[m][sec].get(t), dict) else str(R[m][sec].get(t))[:40] for m in runs]
        if len(set(row)) > 1:
            diffs.append((t, row))
    print(sec, "types", len(ref[sec]), "differing", len(diffs))
    for d in diffs:
        print("   ", d)
