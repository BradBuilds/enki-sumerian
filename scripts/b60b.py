"""Signs made only of down wedges and hooks: table of down-wedge count against hook count. Form only."""
import json, collections, os
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
D = json.load(open(os.path.join(DATA, 'wedges.json')))
S = [s for s in D['signs'] if s['st'] == 'confirmed']
blk = lambda s: 0x12400 <= int(s['cp'],16) <= 0x1247F
rows = []
for s in S:
    kinds = collections.Counter('V' if (w['s'] in 'TB' and w['d'] == 'V') else ('K' if w['s'] == 'K' else ('H' if (w['s'] in 'TB' and w['d']=='H') else 'other')) for w in s['W'])
    rows.append((s, kinds))
print("signs built only from down wedges (V) and hooks (K):")
vk = [(s, k) for s, k in rows if set(k) <= {'V','K'}]
tab = collections.Counter((k.get('V',0), k.get('K',0)) for s, k in vk)
vs = sorted({a for a,b in tab}); ks = sorted({b for a,b in tab})
print("      hooks→ " + " ".join(f"{b:3d}" for b in ks))
for a in vs: print(f"  V={a:2d}      " + " ".join(f"{tab.get((a,b),0) or '.':>3}" for b in ks))
print("  how many of these are in the 12400-1247F block:", sum(blk(s) for s,_ in vk), "of", len(vk))
print("  outside the block:", [(s['cp'], dict(k)) for s,k in vk if not blk(s)])
print("\nsigns built only from across wedges (H):", collections.Counter(k['H'] for s,k in rows if set(k) == {'H'}))
