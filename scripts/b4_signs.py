"""Sign set as a code. 1) ladders: signs that are one unit repeated n times, by direction recipe, with rounding (about one wedge of slip allowed).
2) distance between signs: how many wedges must change to turn one sign into its nearest neighbour."""
import json, collections, os
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
D = json.load(open(os.path.join(DATA, 'wedges.json')))
S = [s for s in D['signs'] if s['st'] == 'confirmed' and s['W']]
key = lambda w: w['s'] + '.' + w['d']
R = {s['cp']: collections.Counter(key(w) for w in s['W']) for s in S}
def ladder(r):
    tot = sum(r.values()); best = None
    for n in range(20, 1, -1):
        b = {k: round(v / n) for k, v in r.items()}; b = {k: v for k, v in b.items() if v}
        if not b: continue
        err = sum(abs(r.get(k, 0) - n * b.get(k, 0)) for k in set(r) | set(b))
        tol = max(1, round(0.05 * tot))
        if err <= tol and (best is None or (err, -n) < (best[2], -best[0])): best = (n, b, err)
    return best
fam = collections.defaultdict(list)
for s in S:
    L = ladder(R[s['cp']])
    if L: fam[tuple(sorted(L[1].items()))].append((L[0], s['cp'], L[2]))
print("== ladders: one unit repeated n times (n >= 2), at least 3 different n")
for b, items in sorted(fam.items(), key=lambda kv: -len({n for n, _, _ in kv[1]})):
    ns = sorted({n for n, _, _ in items})
    if len(ns) < 3: continue
    unit = " + ".join(f"{v} {k}" for k, v in b)
    print(f"  unit [{unit}]  ({sum(v for _, v in b)} wedges)  counts {ns}")
    print("     ", sorted((n, cp) + (("off by %d" % e,) if e else ()) for n, cp, e in items))
print("  signs that fit some ladder:", sum(len(v) for v in fam.values()), "of", len(S))
def feats(s):
    return collections.Counter((key(w), w['z'], min(2, int(3 * w['y'] / max(s['rows'], 1))), min(2, int(3 * w['x'] / max(s['cols'], 1)))) for w in s['W'])
F = {s['cp']: feats(s) for s in S}
def dist(a, b): return sum(((a - b) + (b - a)).values())
nn = {}
cps = list(F)
for a in cps:
    nn[a] = min((dist(F[a], F[b]), b) for b in cps if b != a)
c = collections.Counter(min(d, 10) for d, _ in nn.values())
print("\n== nearest other sign, in wedge changes (type, direction, size and which third of the sign each wedge sits in)")
print("  ", sorted(c.items()), "(10 means 10 or more)")
print("   signs one change from another:", [(a, b) for a, (d, b) in nn.items() if d == 1][:30])
print("   signs identical to another (0 changes):", [(a, b) for a, (d, b) in nn.items() if d == 0])
