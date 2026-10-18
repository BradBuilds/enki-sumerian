"""Does the order of count signs on tablets show a base? Form only: a count sign is a confirmed sign made only of down wedges (V)
or only of left-pointing hooks (K); its count is its number of wedges. The editions give only which sign stands where in a line.
No reading, sign name or editor number value is used. No base is assumed: hook and place values are chosen by the data in part 3."""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "..", "data")
ROOT = os.environ.get("SUMERIAN_DATA", os.path.join(DATA, "raw"))   # where signs.tsv and ur3.signs.tsv live (see README)
import csv, collections, json, random, sys, itertools
csv.field_size_limit(10**9); random.seed(20261017)

cls = json.load(open(os.path.join(DATA, "signclass.json")))
cp_of = {}
for r in csv.DictReader(open(os.path.join(ROOT, "signs.tsv"), encoding="utf-8"), delimiter="\t"):
    if r["unicode_cp"] and r["kind"] == "sign": cp_of[r["oid"]] = r["unicode_cp"].upper()
def tok(oid):
    cp = cp_of.get(oid); c = cls.get(cp) if cp else None
    if not c: return ("u",)                                   # no confirmed shape
    if c[0] == "V": return ("V", c[1], cp)
    if c[0] == "K" and c[2] == "6": return ("K", c[1], cp)
    return ("x",)
tabs = collections.OrderedDict(); cur = None
with open(os.path.join(ROOT, "ur3.signs.tsv"), encoding="utf-8") as f:
    rd = csv.reader(f, delimiter="\t"); hd = next(rd); ix = {h: i for i, h in enumerate(hd)}
    for r in rd:
        key = (r[ix["text"]], r[ix["surface"]], r[ix["column"]], r[ix["line_ix"]])
        if key != cur: cur = key; line = []; tabs.setdefault(r[ix["text"]], []).append(line)
        line.append(tok(r[ix["oid"]]) if r[ix["kind"]] == "S" else ("gap",))
print("tablets", len(tabs), "lines", sum(len(t) for t in tabs.values()))
# runs of count signs inside a line
runs = []   # (tablet, signs list, clean)
for tn, t in tabs.items():
    for ln in t:
        i = 0
        while i < len(ln):
            if ln[i][0] in "VK":
                j = i
                while j < len(ln) and ln[j][0] in "VK": j += 1
                clean = not ((i > 0 and ln[i-1][0] in ("u", "gap")) or (j < len(ln) and ln[j][0] in ("u", "gap")))
                runs.append((tn, ln[i:j], clean, i == 0)); i = j
            else: i += 1
C = [r for r in runs if r[2]]
print("runs of count signs", len(runs), "| not touching a break or an unconfirmed sign", len(C))
def blocks(signs):
    b = []
    for s in signs:
        if b and b[-1][0] == s[0]: b[-1][1] += s[1]; b[-1][2] += 1
        else: b.append([s[0], s[1], 1])
    return b
pat = collections.Counter("".join(b[0] for b in blocks(s)) for _, s, _, _ in C)
print("\n== 1. order of kinds in a run (blocks of the same kind merged):", pat.most_common(10))
print("   same kind written as 2+ signs side by side, per block:", collections.Counter(b[2] for _, s, _, _ in C for b in blocks(s)).most_common(5))
print("\n== 2. totals by place. A cap would show as a hard stop.")
pos = collections.defaultdict(collections.Counter)
for _, s, _, _ in C:
    B = blocks(s); p = "".join(b[0] for b in B)
    for k, (kind, n, _) in enumerate(B): pos[(p, k, kind)][n] += 1
for key in sorted(pos, key=lambda k: -sum(pos[k].values()))[:12]:
    c = pos[key]; p, k, kind = key
    print("   run %-5s block %d (%s): %6d runs | totals %s" % (p, k + 1, kind, sum(c.values()), sorted(c.items())[:22]))
# hooks alone vs hooks before downs: distribution of single hook-sign counts
print("\n   single hook signs, by what follows them in the run:")
fol = collections.defaultdict(collections.Counter)
for _, s, _, _ in C:
    for a, b in zip(s, s[1:] + [None]):
        if a[0] == "K": fol["then down wedges" if b and b[0] == "V" else "then hooks" if b else "end of run"][a[1]] += 1
for k, c in fol.items(): print("     %-18s %s" % (k, sorted(c.items())))
print("   single down-wedge signs, by what comes before them:")
pre = collections.defaultdict(collections.Counter)
for _, s, _, _ in C:
    for a, b in zip([None] + s[:-1], s):
        if b[0] == "V": pre["after hooks" if a and a[0] == "K" else "after down wedges" if a else "start of run"][b[1]] += 1
for k, c in pre.items(): print("     %-18s %s" % (k, sorted(c.items())))
# 3. let the data choose the values: lines that start with a run give one number each; test sums for many value choices
first = collections.defaultdict(list); bad = set()
for tn, s, cl, st in runs:
    if not st: continue
    if not cl: bad.add(tn); continue
    first[tn].append(blocks(s))
def val(B, H, L):
    p = "".join(b[0] for b in B); n = [b[1] for b in B]
    if p == "V": return n[0]
    if p == "K": return H * n[0]
    if p == "KV": return H * n[0] + n[1]
    if p == "VK": return L * n[0] + H * n[1]
    if p == "VKV": return L * n[0] + H * n[1] + n[2]
    return None
T = {tn: L for tn, L in first.items() if tn not in bad and len(L) >= 3}
print("\n== 3. sums. Tablets whose lines start with numbers, clean, 3+ such lines:", len(T))
def hits(lists, floor):
    h = 0
    for a in lists:
        ok = False
        for i in range(2, len(a)):
            if a[i] < floor: continue
            s = 0
            for j in range(i - 1, -1, -1):
                s += a[j]
                if s == a[i] and i - j >= 2: ok = True; break
                if s > a[i]: break
            if ok: break
        h += ok
    return h
def lists_for(H, L):
    out = []
    for Ls in T.values():
        v = [val(B, H, L) for B in Ls]
        if all(x is not None for x in v): out.append(v)
    return out
def score(H, L, floor=10, reps=8):
    lists = lists_for(H, L); real = hits(lists, floor); sh = []
    for _ in range(reps): sh.append(hits([random.sample(a, len(a)) for a in lists], floor))
    m = sum(sh) / len(sh); sd = (sum((x - m) ** 2 for x in sh) / len(sh)) ** 0.5 or 1
    return real, m, (real - m) / sd, len(lists)
print("   part A: value of one hook, with no leading down-wedge block (runs K, KV, V only count; L unused):")
for H in range(2, 21):
    r, m, z, n = score(H, 10**6)
    print("     hook = %2d   tablets %5d   sums found %5d   in shuffled order %7.1f   excess %+5.1f spreads" % (H, n, r, m, z))
print("   part B: hook = 10, value of a leading down wedge (place above the hooks):")
for L in (20, 30, 40, 50, 60, 70, 80, 90, 100, 120):
    r, m, z, n = score(10, L)
    print("     lead = %3d   sums found %5d   shuffled %7.1f   excess %+5.1f spreads" % (L, r, m, z))
