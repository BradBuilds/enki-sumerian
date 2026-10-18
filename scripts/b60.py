"""Base-60 tests on the matrix data: group sizes, wedges and groups per sign, angle periodicity. Form only."""
import json, math, collections, random, os
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
D = json.load(open(os.path.join(DATA, 'wedges.json')))
S = [s for s in D['signs'] if s['st'] == 'confirmed']
DIV = {1,2,3,4,5,6,10,12,15,20,30,60}
numblk = lambda s: 0x12400 <= int(s['cp'],16) <= 0x1247F
def neigh(c, label):
    """each count vs the mean of its two neighbours; divisors of 60 vs the rest (n>=2)."""
    keys = sorted(c); out = []
    for n in range(2, max(keys)):
        a, b = c.get(n-1, 0), c.get(n+1, 0)
        if a + b == 0 and c.get(n,0) == 0: continue
        out.append((n, c.get(n,0), (a+b)/2))
    d = [(n,x,e) for n,x,e in out if n in DIV]; o = [(n,x,e) for n,x,e in out if n not in DIV]
    r = lambda L: sum(x for _,x,_ in L)/max(1e-9, sum(e for _,_,e in L))
    print(f"  {label}: observed/neighbour-mean  divisors of 60 {r(d):.2f}  others {r(o):.2f}")
for nm, sub in [("all signs", S), ("without the numbers block 12400-1247F", [s for s in S if not numblk(s)]), ("numbers block only", [s for s in S if numblk(s)])]:
    print("==", nm, len(sub), "signs")
    gs = collections.Counter(g['n'] for s in sub for g in s['G'])
    print("  group sizes:", sorted(gs.items())); neigh(gs, "group size")
    wc = collections.Counter(len(s['W']) for s in sub); gc = collections.Counter(len(s['G']) for s in sub)
    neigh(wc, "wedges per sign"); neigh(gc, "groups per sign")
    print("  wedges per sign:", sorted(wc.items()))
print("== group size by type and direction (all confirmed signs)")
by = collections.defaultdict(collections.Counter)
for s in S:
    for g in s['G']: by[(g['s'], g['d'] if g['s'] != 'K' else 'K'+g['d'])][g['n']] += 1
for k, c in sorted(by.items(), key=lambda kv: -sum(kv[1].values()))[:14]:
    print(" ", k, "max", max(c), sorted(c.items()))
print("== groups of 4+ : which signs (block) ")
big = [(s['cp'], g['s'], g['d'], g['n'], g['sz']) for s in S for g in s['G'] if g['n'] >= 4]
print("  total", len(big), "in numbers block", sum(0x12400 <= int(c,16) <= 0x1247F for c,*_ in big))
print("  examples outside block:", [b for b in big if not (0x12400 <= int(b[0],16) <= 0x1247F)][:25])
A = [w['c'] for s in S for w in s['W'] if w['s'] in 'TL' and w['len'] > 0]
off = [a for a in A if min(abs((a - t + 180) % 360 - 180) for t in (0,90,180,270)) > 1.0]
print("== angles:", len(A), "tailed; off the quarter lines:", len(off))
def R(L, p):
    x = sum(math.cos(2*math.pi*a/p) for a in L)/len(L); y = sum(math.sin(2*math.pi*a/p) for a in L)/len(L); return math.hypot(x,y)
sc = sorted(((R(off, p), p) for p in [x/2 for x in range(6, 121)]), reverse=True)
print("  strongest periods (degrees):", [(p, round(r,3)) for r,p in sc[:10]])
print("  chance level for this many angles ~", round(1/math.sqrt(len(off)),3))
for p in (6,12,15,30,45,60): print("   period", p, round(R(off,p),3))
print("\n== where the off-quarter angles sit (compass, 0 up, folded to 0-180 so a line and its reverse coincide)")
fold = [a % 180 for a in off]
h = collections.Counter(int(a // 3) * 3 for a in fold)
for b in range(0, 180, 3):
    n = h.get(b, 0)
    if n >= 15: print(f"  {b:3d}-{b+3:<3d} {n:4d} " + "#" * (n // 8))
for p in (45, 60):
    x = sum(math.cos(2*math.pi*a/p) for a in off); y = sum(math.sin(2*math.pi*a/p) for a in off)
    print(f"  period {p}: peaks sit at {math.degrees(math.atan2(y,x))*p/360 % p:.1f} + k*{p}")
near = lambda a, m: min(abs((a - k + 90) % 180 - 90) for k in range(0, 180, m)) <= 3
print("  within 3 deg of a 30-multiple (30,60,120,150):", sum(near(a,30) and not near(a,90) for a in fold), "| of a 45-multiple (45,135):", sum(near(a,45) and not near(a,90) for a in fold), "| total", len(fold))
print("  expected by chance in any 6-degree window:", round(len(fold) * 6 / 180, 1))
def stat(c, special):
    keys = [n for n in range(2, 30)]
    obs = [(c.get(n,0), (c.get(n-1,0)+c.get(n+1,0))/2) for n in keys]
    sp = [o for n,o in zip(keys,obs) if n in special]; ot = [o for n,o in zip(keys,obs) if n not in special]
    f = lambda L: sum(a for a,_ in L) / max(1e-9, sum(b for _,b in L))
    return f(sp) - f(ot)
random.seed(1)
for nm, sub in [("all", S), ("outside numbers block", [s for s in S if not numblk(s)])]:
    for what, c in [("groups per sign", collections.Counter(len(s['G']) for s in sub)), ("wedges per sign", collections.Counter(len(s['W']) for s in sub))]:
        sp = {n for n in DIV if 2 <= n < 30}; o = stat(c, sp)
        null = [stat(c, set(random.sample(range(2, 30), len(sp)))) for _ in range(5000)]
        print(f"  {nm} · {what}: divisor edge {o:+.2f}; random number sets beat it {sum(x >= o for x in null)/len(null):.1%} of the time")
print("\n== big hook groups (8+)")
for s in S:
    for g in s['G']:
        if g['s'] == 'K' and g['n'] >= 8: print(" ", s['cp'], "hook dir", g['d'], "n", g['n'], "sizes", g['sz'], "share", s['share'])
