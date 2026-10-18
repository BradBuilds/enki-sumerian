"""Groups and counts from the validated file. Grouping rule: wedges of one type and direction side by side, within 0.13 of a full tail along their direction and 0.50 across it (a full tail = 113.4 units); hooks join within 0.50.
Usage: python3 scripts/group_wedges.py   (reads data/validated_wedges.json and data/sign_meta.json, writes data/wedges.json). No sign name or reading is used; code points are labels only."""
import json, math, re, sys, collections
import os
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
VAL, OUT = os.path.join(DATA, "validated_wedges.json"), os.path.join(DATA, "wedges.json")
REFPX, TOL, GAP, BIT = 113.4, 0.13, 0.50, 40.31
CANON = dict(H=0, S=24, D=45, T=60, V=90, P=300, U=315, R=336)
def adiff(a, b): return abs((a - b + 180) % 360 - 180)
def kind_of(a):
    al = a % 180
    return "H" if al < 12 or al >= 168 else "S" if al < 35 else "D" if al < 51 else "T" if al < 78 else "V" if al < 102 else "P" if al < 129 else "U" if al < 145 else "R"
def form(w):
    if w["k"] == "K": return "K", str(int(round(((w["a"] + 90) % 360) / 45.0)) % 8)   # hook: compass octant of its point, 0 = up
    if w["k"] == "L": return "L", kind_of(w["a"])                                       # line: no head, so no reverse
    k = kind_of(w["a"]); return ("T" if w["l"] > 0 else "B"), k + ("r" if adiff(w["a"], CANON[k]) > 90 else "")
def groups(ws):
    by = collections.defaultdict(list)
    for i, w in enumerate(ws): by[form(w)].append(i)
    res = []
    for (s, d), items in sorted(by.items()):
        if s == "K":
            seen, comps = set(), []
            for i in items:
                if i in seen: continue
                comp, q = [i], [i]; seen.add(i)
                while q:
                    a = q.pop()
                    for b in items:
                        if b not in seen and math.hypot(ws[a]["x"] - ws[b]["x"], ws[a]["y"] - ws[b]["y"]) / REFPX <= GAP: seen.add(b); comp.append(b); q.append(b)
                comps.append(comp)
        else:
            ang = math.radians(CANON[d[0]]); ux, uy = math.cos(ang), math.sin(ang)
            al = lambda i: (ws[i]["x"] * ux + ws[i]["y"] * uy) / REFPX
            ac = lambda i: (-ws[i]["x"] * uy + ws[i]["y"] * ux) / REFPX
            its = sorted(items, key=al); bands, cur = [], []
            for i in its:
                if cur and al(i) - al(cur[-1]) > TOL: bands.append(cur); cur = []
                cur.append(i)
            if cur: bands.append(cur)
            comps = []
            for b in bands:
                b = sorted(b, key=ac); c = [b[0]]
                for i in b[1:]:
                    if ac(i) - ac(c[-1]) > GAP: comps.append(c); c = []
                    c.append(i)
                comps.append(c)
        for c in comps: res.append((s, d, sorted(c)))
    return res
meta = json.load(open(os.path.join(DATA, "sign_meta.json")))["signs"]
val = json.load(open(VAL))["signs"]; out = []; tally = collections.Counter()
for cp, m in sorted(meta.items(), key=lambda kv: kv[1]["rank"]):
    v = val.get(cp); ws = []
    if v:
        for a in v["wedges"]: ws.append(dict(k=a[0], x=a[1], y=a[2], a=a[3], l=a[4] if a[0] != "K" else 0, z=a[6]))
    gs = groups(ws) if ws else []; gi = {}
    for n_, (s, d, c) in enumerate(gs):
        for i in c: gi[i] = n_
    W = []
    for i, w in enumerate(ws):
        s, d = form(w)
        W.append(dict(s=s, d=d, z=w["z"] + 1, c=round((w["a"] + 90) % 360, 1), len=round(w["l"] / 0.42 / BIT, 1) if s in ("T", "L") else 0,
                      x=round((w["x"] / 0.42 - m["x0"]) / BIT, 2), y=round((w["y"] / 0.42 - m["y0"]) / BIT, 2), g=gi[i]))
    G = []
    for s, d, c in gs:
        sz = sorted(ws[i]["z"] + 1 for i in c)
        G.append(dict(s=s, d=d, n=len(c), sz="".join(map(str, sz)), x=round(sum(W[i]["x"] for i in c) / len(c), 2), y=round(sum(W[i]["y"] for i in c) / len(c), 2)))
    status = "missing" if not v else ("confirmed" if v["checked"] else "unconfirmed"); tally[status] += 1
    out.append(dict(cp=cp, rank=m["rank"], share=m["share"], st=status, cols=m["cols"], rows=m["rows"], W=W, G=G))
json.dump(dict(bit=BIT, signs=out), open(OUT, "w"), separators=(",", ":"))
print(dict(tally), "signs", len(out), "wedges", sum(len(o["W"]) for o in out), "groups", sum(len(o["G"]) for o in out))
