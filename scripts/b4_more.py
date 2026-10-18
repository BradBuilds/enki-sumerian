import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "b4_text.py")).read().split("print(\"complete lines")[0])
import collections, math, random
H = lambda c: -sum(v / sum(c.values()) * math.log2(v / sum(c.values())) for v in c.values())
shuf = [tuple(random.sample(l, len(l))) for l in lines]
# shuffle that keeps each line's first symbol fixed (so only the order of the rest is tested)
shuf1 = [l[:1] + tuple(random.sample(l[1:], len(l) - 1)) for l in lines]
for nm, ls in (("real", lines), ("shuffled", shuf), ("first kept, rest shuffled", shuf1)):
    out = []
    for k in (1, 2, 3):
        nx = collections.defaultdict(collections.Counter)
        for l in ls:
            if len(l) > k: nx[l[:k]][l[k]] += 1
        hb = sorted(H(c) for p, c in nx.items() if sum(c.values()) >= 50); out.append("after %d: %.2f bits" % (k, hb[len(hb) // 2]))
    print("%-28s" % nm, " | ".join(out))
tl = collections.Counter(lines); tot = len(lines)
print("\nmost common whole lines cover: top 10 %.1f%%, top 100 %.1f%%, top 1000 %.1f%%" % tuple(100 * sum(v for _, v in tl.most_common(k)) / tot for k in (10, 100, 1000)))
print("lines seen only once: %.1f%%" % (100 * sum(v for v in tl.values() if v == 1) / tot))
L15 = collections.Counter(l for l in lines if len(l) == 15); print("\nlength-15 lines:", sum(L15.values()), "| distinct", len(L15), "| top 3 cover %.0f%%" % (100 * sum(v for _, v in L15.most_common(3)) / sum(L15.values())))
top = L15.most_common(1)[0]; print("  most common one appears", top[1], "times on", len({t for l, t in zip(lines, tab_of) if l == top[0]}), "tablets; its symbols:", " ".join(top[0]))
