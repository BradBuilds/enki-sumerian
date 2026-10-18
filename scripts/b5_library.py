"""A: predict missing ladder signs and look for them in the held-out font signs. B: signs built from other signs (left/right or top/bottom).
C: does context in the text follow shared parts, or closeness of shape? No readings or names; code points are labels only."""
import json, collections, math, itertools, os
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
D = json.load(open(os.path.join(DATA, 'wedges.json'))); CTX = json.load(open(os.path.join(DATA, 'context_vectors.json'))); ALLF = json.load(open(os.path.join(DATA, 'detector_shapes.json')))['signs']
S = {s['cp']: s for s in D['signs'] if s['st'] == 'confirmed' and s['W']}
CANON = dict(H=0, S=24, D=45, T=60, V=90, P=300, U=315, R=336)
def kind_of(a):
    al = a % 180
    return "H" if al < 12 or al >= 168 else "S" if al < 35 else "D" if al < 51 else "T" if al < 78 else "V" if al < 102 else "P" if al < 129 else "U" if al < 145 else "R"
adiff = lambda a, b: abs((a - b + 180) % 360 - 180)
dkey_v = lambda w: ('K' + w['d']) if w['s'] == 'K' else ('L' + w['d']) if w['s'] == 'L' else w['d']
def dkey_det(w):
    a = w['a'] % 360
    if w['k'] == 'K': return 'K' + str(int(round((((a + 180) + 90) % 360) / 45.0)) % 8)
    k = kind_of(a); return k + ('r' if adiff(a, CANON[k]) > 90 else '')
uses = lambda cp: CTX.get(cp, {}).get('n', 0)
REC = {cp: collections.Counter(dkey_v(w) for w in s['W']) for cp, s in S.items()}
def fit(r, unit, tolfrac):
    tot = sum(r.values()); best = None
    for n in range(1, 25):
        err = sum(abs(r.get(k, 0) - n * unit.get(k, 0)) for k in set(r) | set(unit))
        if err <= max(1, round(tolfrac * tot)) and (best is None or err < best[1]): best = (n, err)
    return best
def ladder(r):
    best = None
    for n in range(20, 1, -1):
        b = {k: round(v / n) for k, v in r.items()}; b = {k: v for k, v in b.items() if v}
        if not b: continue
        err = sum(abs(r.get(k, 0) - n * b.get(k, 0)) for k in set(r) | set(b))
        if err <= max(1, round(0.05 * sum(r.values()))) and (best is None or (err, -n) < (best[2], -best[0])): best = (n, b, err)
    return best
fam = collections.defaultdict(dict)
for cp, r in REC.items():
    L = ladder(r)
    if L: fam[tuple(sorted(L[1].items()))].setdefault(L[0], []).append(cp)
singles = {tuple(sorted(r.items())): cp for cp, r in REC.items()}
for u in list(fam):   # the unit itself (n = 1) if a sign has exactly that recipe
    if u in singles: fam[u].setdefault(1, []).append(singles[u])
LAD = {u: v for u, v in fam.items() if len(v) >= 3}
print("== A. ladders in the confirmed set and their gaps (1 to 9)")
held = {"%05X" % r['cp']: collections.Counter(dkey_det(w) for w in r['wedges']) for r in ALLF if r.get('wedges') and "%05X" % r['cp'] not in S and "%05X" % r['cp'] not in ('1245D', '1245E', '1219B')}
print("   held-out font signs with a detector shape:", len(held), "| of them used in the Ur III text:", sum(1 for cp in held if uses(cp)))
found_total = pred_total = 0
for u, members in sorted(LAD.items(), key=lambda kv: -len(kv[1])):
    unit = dict(u); have = sorted(members); top = max(9, max(have)); gaps = [n for n in range(1, top + 1) if n not in members]
    hits = collections.defaultdict(list)
    for cp, r in held.items():
        f = fit(r, unit, 0.08)
        if f and f[0] >= 1 and set(r) <= set(unit):
            hits[f[0]].append(cp + ("~" if f[1] else ""))
    pred_total += len(gaps); found_total += sum(1 for n in gaps if hits.get(n))
    print(f"   unit {'+'.join(f'{v}{k}' for k, v in u)}: confirmed counts {have} | gaps {gaps}")
    if hits: print("      held-out signs that fit:", {n: v for n, v in sorted(hits.items())})
print(f"   gaps predicted {pred_total}, filled by a held-out sign {found_total}  (~ = fits with one wedge of slip)")
def parts(s, axis):
    ext = []
    for i, w in enumerate(s['W']):
        a = math.radians(w['c']); x2 = w['x'] + w['len'] * math.sin(a); y2 = w['y'] - w['len'] * math.cos(a)
        lo, hi = (min(w['x'], x2), max(w['x'], x2)) if axis == 'x' else (min(w['y'], y2), max(w['y'], y2))
        ext.append((lo - 0.3, hi + 0.3, i))
    ext.sort(); out = []; cur = [ext[0]]; reach = ext[0][1]
    for e in ext[1:]:
        if e[0] > reach: out.append([i for _, _, i in cur]); cur = []
        cur.append(e); reach = max(reach, e[1])
    out.append([i for _, _, i in cur]); return out
RZ = {cp: collections.Counter((dkey_v(w), w['z']) for w in s['W']) for cp, s in S.items()}
bykey = collections.defaultdict(list)
for cp, r in RZ.items(): bykey[tuple(sorted(r.items()))].append(cp)
def lookup(rc): return bykey.get(tuple(sorted(rc.items())))
comp = {}
for cp, s in S.items():
    for axis in ('x', 'y'):
        ps = parts(s, axis)
        if len(ps) < 2: continue
        names = []
        for p in ps:
            rc = collections.Counter((dkey_v(s['W'][i]), s['W'][i]['z']) for i in p); m = lookup(rc)
            names.append(sorted(c for c in m if c != cp)[0] if m and any(c != cp for c in m) else None)
        if all(names): comp.setdefault(cp, (axis, names))
print("\n== B. signs that are other confirmed signs side by side (left-right) or stacked (top-bottom), same wedges and sizes")
print("   found:", len(comp), "of", len(S))
pl = collections.Counter(); first = collections.defaultdict(set); second = collections.defaultdict(set)
for cp, (ax, names) in comp.items():
    if len(names) == 2: first[ax].add(names[0]); second[ax].add(names[1])
    for n in names: pl[n] += 1
print("   most used building parts:", pl.most_common(12))
for ax in ('x', 'y'):
    used = sum(1 for cp, (a, n) in comp.items() if a == ax and len(n) == 2)
    if used: print(f"   {'left+right' if ax == 'x' else 'top+bottom'} pairs: {used} used, {len(first[ax])} different first parts x {len(second[ax])} different second parts = {len(first[ax]) * len(second[ax])} possible -> {100 * used / max(1, len(first[ax]) * len(second[ax])):.1f}% of the possible pairs are used")
print("   examples:", [(cp, ax, n) for cp, (ax, n) in list(comp.items())[:15]])
cand = [cp for cp in S if uses(cp) >= 200]
tot = collections.Counter()
for cp in cand: tot.update(CTX[cp]['c'])
N = sum(tot.values())
def ppmi(cp):
    c = CTX[cp]['c']; n = sum(c.values()); out = {}
    for k, v in c.items():
        x = math.log((v / n) / (tot[k] / N))
        if x > 0: out[k] = x
    nr = math.sqrt(sum(x * x for x in out.values())); return {k: x / nr for k, x in out.items()}
V = {cp: ppmi(cp) for cp in cand}
cos = lambda a, b: sum(x * b.get(k, 0) for k, x in a.items()) if len(a) < len(b) else sum(x * a.get(k, 0) for k, x in b.items())
def feats(s): return collections.Counter((dkey_v(w), w['z'], min(2, int(3 * w['y'] / max(s['rows'], 1))), min(2, int(3 * w['x'] / max(s['cols'], 1)))) for w in s['W'])
F = {cp: feats(S[cp]) for cp in cand}
dist = lambda a, b: sum(((F[a] - F[b]) + (F[b] - F[a])).values())
famof = {}
for u, mem in LAD.items():
    for n, cps in mem.items():
        for c in cps: famof.setdefault(c, set()).add(u)
partof = {cp: set(n for n in comp[cp][1]) for cp in comp}
rows = []
for a, b in itertools.combinations(cand, 2):
    d = dist(a, b); rel = 'ladder' if famof.get(a, set()) & famof.get(b, set()) else 'part' if (partof.get(a, set()) & (partof.get(b, set()) | {b})) or (partof.get(b, set()) & {a}) else ''
    rows.append((d, cos(V[a], V[b]), rel, a, b))
print("\n== C. how alike two signs are in the text (0 = nothing in common, 1 = same neighbours), %d signs used 200+ times, %d pairs" % (len(cand), len(rows)))
mean = lambda L: sum(L) / len(L) if L else float('nan')
for lo, hi in ((0, 0), (1, 1), (2, 2), (3, 4), (5, 8), (9, 15), (16, 999)):
    L = [c for d, c, r, _, _ in rows if lo <= d <= hi]
    print(f"   shape distance {lo}-{hi}: pairs {len(L):6d}, context alike {mean(L):.3f}")
for rel in ('ladder', 'part'):
    L = [(d, c) for d, c, r, _, _ in rows if r == rel]
    if not L: continue
    base = collections.defaultdict(list)
    for d, c, r, _, _ in rows:
        if not r: base[d].append(c)
    m = mean([c for _, c in L]); mb = mean([mean(base[d]) for d, _ in L if base[d]])
    print(f"   pairs sharing a {rel}: {len(L)}, context alike {m:.3f} | unrelated pairs at the same shape distance {mb:.3f}")
def spearman(x, y):
    def rk(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]: j += 1
            for k in range(i, j + 1): r[o[k]] = (i + j) / 2
            i = j + 1
        return r
    a, b = rk(x), rk(y); ma, mb = mean(a), mean(b)
    return sum((p - ma) * (q - mb) for p, q in zip(a, b)) / math.sqrt(sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b))
print("   rank correlation, shape distance vs context alike: %.3f (0 = shape tells nothing about context)" % spearman([d for d, *_ in rows], [c for _, c, *_ in rows]))
near = sorted([r for r in rows if r[0] <= 1], key=lambda r: r[1])
print("   one change apart but unalike in the text:", [(a, b, round(c, 2)) for d, c, r, a, b in near[:10]])
print("   one change apart and alike:", [(a, b, round(c, 2)) for d, c, r, a, b in near[-8:]])
far = sorted([r for r in rows if r[0] >= 9], key=lambda r: -r[1]); print("   very different shapes but alike in the text:", [(a, b, d, round(c, 2)) for d, c, r, a, b in far[:10]])
