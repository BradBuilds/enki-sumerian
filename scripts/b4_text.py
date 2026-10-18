"""Machine-record tests on the Ur III text. Sign identity and order come from the editions; no reading, name or number value is used.
A run of count signs (confirmed down-wedge-only or left-hook-only signs) becomes N. Every test is compared with the same lines shuffled."""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "..", "data")
ROOT = os.environ.get("SUMERIAN_DATA", os.path.join(DATA, "raw"))   # where signs.tsv and ur3.signs.tsv live (see README)
import csv, collections, json, math, random
csv.field_size_limit(10**9); random.seed(7)
cls = json.load(open(os.path.join(DATA, "signclass.json"))); cp_of = {}
for r in csv.DictReader(open(os.path.join(ROOT, "signs.tsv"), encoding="utf-8"), delimiter="\t"):
    if r["unicode_cp"] and r["kind"] == "sign": cp_of[r["oid"]] = r["unicode_cp"].upper()
isnum = lambda o: (lambda c: bool(c) and (c[0] == "V" or (c[0] == "K" and c[2] == "6")))(cls.get(cp_of.get(o, ""), None))
lines = []; tab_of = []; cur = None; broken = False; buf = []
def flush():
    if cur and buf and not broken:
        out = []
        for o in buf:
            t = "N" if isnum(o) else o
            if not (t == "N" and out and out[-1] == "N"): out.append(t)
        lines.append(tuple(out)); tab_of.append(cur[0])
with open(os.path.join(ROOT, "ur3.signs.tsv"), encoding="utf-8") as f:
    rd = csv.reader(f, delimiter="\t"); hd = next(rd); ix = {h: i for i, h in enumerate(hd)}
    for r in rd:
        key = (r[ix["text"]], r[ix["surface"]], r[ix["column"]], r[ix["line_ix"]])
        if key != cur: flush(); cur = key; buf = []; broken = False
        if r[ix["kind"]] != "S" or not r[ix["oid"]]: broken = True
        else: buf.append(r[ix["oid"]])
    flush()
print("complete lines (no break, no damage):", len(lines), "on", len(set(tab_of)), "tablets")
H = lambda c: -sum(v / sum(c.values()) * math.log2(v / sum(c.values())) for v in c.values())
shuf = [tuple(random.sample(l, len(l))) for l in lines]
# 1 line length
L = collections.Counter(len(l) for l in lines); print("\n== 1. line length in signs (number runs count as one):", sorted(L.items())[:16])
# 2 frequencies
sc = collections.Counter(t for l in lines for t in l); fr = sorted(sc.values(), reverse=True)
xs = [math.log(i + 1) for i in range(min(1000, len(fr)))]; ys = [math.log(fr[i]) for i in range(len(xs))]
mx, my = sum(xs) / len(xs), sum(ys) / len(ys); slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
print("\n== 2. symbols in use:", len(sc), "| top 10 cover %.1f%%, top 100 cover %.1f%% | rank-frequency slope over ranks 1-1000: %.2f" % (100 * sum(fr[:10]) / sum(fr), 100 * sum(fr[:100]) / sum(fr), slope), "| N is %.1f%% of all tokens" % (100 * sc["N"] / sum(fr)))
# 3 redundancy: how much does the previous symbol predict the next
def cond(ls):
    big = collections.Counter(); prev = collections.Counter()
    for l in ls:
        for a, b in zip(("^",) + l, l + ("$",)): big[(a, b)] += 1; prev[a] += 1
    n = sum(big.values()); return -sum(v / n * math.log2(v / prev[a]) for (a, b), v in big.items())
h0 = H(collections.Counter(t for l in lines for t in l + ("$",))); h1, h1s = cond(lines), cond(shuf)
print("\n== 3. bits per symbol: on its own %.2f | knowing the one before, real order %.2f | same lines shuffled %.2f" % (h0, h1, h1s))
print("   share of the uncertainty removed by order: %.0f%%" % (100 * (h1s - h1) / h1s))
# 4 positional entropy
print("\n== 4. how predictable each position is (bits; lower = more fixed). Lines of 3+ symbols.")
for nm, ls in (("real", lines), ("shuffled", shuf)):
    row = []
    for k in (0, 1, 2, 3):
        c = collections.Counter(l[k] for l in ls if len(l) >= 3 and len(l) > k); row.append("pos %d: %.2f" % (k + 1, H(c)))
    c = collections.Counter(l[-1] for l in ls if len(l) >= 3); row.append("last: %.2f" % H(c))
    print("   %-9s" % nm, " | ".join(row))
first = collections.Counter(l[0] for l in lines if len(l) >= 3); print("   real first symbol, most common:", [(k, "%.1f%%" % (100 * v / sum(first.values()))) for k, v in first.most_common(5)])
# 5 templates
def shape(l): return tuple(t if t == "N" else "s" for t in l)
tp = collections.Counter(shape(l) for l in lines); tl = collections.Counter(lines)
cov = lambda c, k: 100 * sum(v for _, v in c.most_common(k)) / sum(c.values())
print("\n== 5. layouts (N = number, s = any other sign): %d different | top 5 cover %.1f%%, top 20 cover %.1f%%" % (len(tp), cov(tp, 5), cov(tp, 20)))
print("   most common:", [(" ".join(k), v) for k, v in tp.most_common(8)])
tps = collections.Counter(shape(l) for l in shuf); print("   shuffled: top 5 cover %.1f%%" % cov(tps, 5))
# 6 what follows a number
after = collections.Counter(l[i + 1] for l in lines for i in range(len(l) - 1) if l[i] == "N"); allc = collections.Counter(t for l in lines for t in l if t != "N")
print("\n== 6. the symbol right after a number: %d different, %.2f bits (any non-number symbol: %.2f bits); top 5 cover %.1f%%" % (len(after), H(after), H(allc), cov(after, 5)))
before = collections.Counter(l[i - 1] for l in lines for i in range(1, len(l)) if l[i] == "N"); print("   right before a number: %.2f bits; top 5 cover %.1f%%" % (H(before), cov(before, 5)))
# 7 exact repeats
rep = collections.defaultdict(set)
for l, t in zip(lines, tab_of): rep[l].add(t)
multi = sum(tl[l] for l, ts in rep.items() if len(ts) >= 2); print("\n== 7. lines whose exact symbol sequence also appears on another tablet: %.1f%%" % (100 * multi / len(lines)))
nonum = [l for l in lines if "N" not in l]; rn = collections.defaultdict(set)
for l, t in zip(lines, tab_of):
    if "N" not in l: rn[l].add(t)
print("   among lines with no number: %.1f%% | distinct lines: %d of %d" % (100 * sum(1 for l, t in zip(lines, tab_of) if "N" not in l and len(rn[l]) >= 2) / max(1, len(nonum)), len(tl), len(lines)))
# 8 prefixes (like an address tree): how many different continuations after the first k symbols
print("\n== 8. branching: different next symbols after a given start of line (median over starts seen 50+ times)")
for k in (1, 2, 3):
    nx = collections.defaultdict(collections.Counter)
    for l in lines:
        if len(l) > k: nx[l[:k]][l[k]] += 1
    b = sorted(len(c) for p, c in nx.items() if sum(c.values()) >= 50); hb = sorted(H(c) for p, c in nx.items() if sum(c.values()) >= 50)
    if b: print("   after %d: starts %d, median different next %d, median %.2f bits" % (k, len(b), b[len(b) // 2], hb[len(hb) // 2]))
