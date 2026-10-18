"""Context of each sign in the text: counts of the sign directly to its left and right (count signs shown as N). Sign identity and order from the editions only."""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "..", "data")
ROOT = os.environ.get("SUMERIAN_DATA", os.path.join(DATA, "raw"))   # where signs.tsv and ur3.signs.tsv live (see README)
import csv, collections, json
csv.field_size_limit(10**9)
cls = json.load(open(os.path.join(DATA, "signclass.json"))); cp_of = {}
for r in csv.DictReader(open(os.path.join(ROOT, "signs.tsv"), encoding="utf-8"), delimiter="\t"):
    if r["unicode_cp"] and r["kind"] == "sign": cp_of[r["oid"]] = r["unicode_cp"].upper()
isnum = lambda o: (lambda c: bool(c) and (c[0] == "V" or (c[0] == "K" and c[2] == "6")))(cls.get(cp_of.get(o, ""), None))
ctx = collections.defaultdict(collections.Counter); occ = collections.Counter(); cur = None; buf = []
def flush():
    if not buf: return
    toks = ["^"] + [("N" if (o and isnum(o)) else (o or "?")) for o in buf] + ["$"]
    for i, o in enumerate(buf, 1):
        cp = cp_of.get(o) if o else None
        if not cp: continue
        occ[cp] += 1; ctx[cp]["L:" + toks[i - 1]] += 1; ctx[cp]["R:" + toks[i + 1]] += 1
with open(os.path.join(ROOT, "ur3.signs.tsv"), encoding="utf-8") as f:
    rd = csv.reader(f, delimiter="\t"); hd = next(rd); ix = {h: i for i, h in enumerate(hd)}
    for r in rd:
        key = (r[ix["text"]], r[ix["surface"]], r[ix["column"]], r[ix["line_ix"]])
        if key != cur: flush(); cur = key; buf = []
        buf.append(r[ix["oid"]] if r[ix["kind"]] == "S" and r[ix["oid"]] else None)
    flush()
json.dump({cp: {"n": occ[cp], "c": dict(c)} for cp, c in ctx.items()}, open(os.path.join(DATA, "context_vectors.json"), "w"))
print("signs with context:", len(ctx), "| with 200+ uses:", sum(1 for v in occ.values() if v >= 200))
