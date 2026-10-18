"""Build data/summary.json, the numbers the project page draws from. Every number is read from ../data or ../outputs, never typed.
Usage: python3 site_summary.py <out.json>"""
import json, os, re, ast, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, '..', 'data'); OUT = os.path.join(HERE, '..', 'outputs')
D = json.load(open(os.path.join(DATA, 'wedges.json'))); conf = [s for s in D['signs'] if s['st'] == 'confirmed']
txt = lambda f: open(os.path.join(OUT, f), encoding='utf8').read()
def after(text, label):
    """the Python list printed right after `label` on its line"""
    line = next(l for l in text.splitlines() if label in l)
    return ast.literal_eval(line[line.index('['):line.rindex(']') + 1])
def num(text, pattern, cast=int):
    return cast(re.search(pattern, text).group(1).replace(',', ''))
b3, b4t, b4m, b4s, b5, b60 = txt('b3_base.out'), txt('b4_text.out'), txt('b4_more.out'), txt('b4_signs.out'), txt('b5_library.out'), txt('b60.out')

# signs drawn from our own measurements (no font images): head x,y in bits, compass angle, tail length in bits, size stage, type
def geom(cp):
    s = next(x for x in D['signs'] if x['cp'] == cp)
    return dict(cp=cp, cols=s['cols'], rows=s['rows'], wedges=[dict(t=w['s'], x=w['x'], y=w['y'], c=w['c'], len=w['len'], z=w['z']) for w in s['W']])
diamond = ['12423', '12424', '12426', '12427', '12428', '12429', '1242A', '1242B']
down = ['12079', '1222B', '12000', '12409', '1240A', '1240B', '1240C', '1240D', '1240E']
hooks = ['1230B', '12399', '1230D', '1240F', '12410', '12411', '12412', '12413', '12414']
off_by = {}
for m in re.finditer(r"\((\d+), '([0-9A-F]+)', 'off by (\d)'\)", b4s): off_by[m.group(2)] = int(m.group(3))

fol = {}
for line in b3.splitlines():
    m = re.match(r"\s+(then down wedges|end of run|then hooks)\s+(\[.*\])", line)
    if m: fol[m.group(1)] = dict(ast.literal_eval(m.group(2)))
hook_rows = [dict(panel=p, hooks=h, uses=fol[k].get(h, 0)) for p, k in (('before', 'then down wedges'), ('end', 'end of run')) for h in range(1, 10)]
pre = {}
for line in b3.splitlines():
    m = re.match(r"\s+(start of run|after hooks|after down wedges)\s+(\[.*\])", line)
    if m: pre[m.group(1)] = dict(ast.literal_eval(m.group(2)))
sumsA = [dict(hook=int(m.group(1)), found=int(m.group(2)), shuffled=float(m.group(3))) for m in re.finditer(r"hook =\s+(\d+)\s+tablets\s+\d+\s+sums found\s+(\d+)\s+in shuffled order\s+([\d.]+)", b3)]
sumsB = [dict(lead=int(m.group(1)), found=int(m.group(2)), shuffled=float(m.group(3))) for m in re.finditer(r"lead =\s+(\d+)\s+sums found\s+(\d+)\s+shuffled\s+([\d.]+)", b3)]

gs = collections.Counter(g['n'] for s in conf for g in s['G'])
ctx_bins = [dict(lo=int(a), hi=int(b), pairs=int(c), alike=float(d)) for a, b, c, d in re.findall(r"shape distance (\d+)-(\d+): pairs\s+(\d+), context alike ([\d.]+)", b5)]
lad = re.search(r"pairs sharing a ladder: (\d+), context alike ([\d.]+) \| unrelated pairs at the same shape distance ([\d.]+)", b5)
part = re.search(r"pairs sharing a part: (\d+), context alike ([\d.]+) \| unrelated pairs at the same shape distance ([\d.]+)", b5)
rec = re.search(r"most common one appears (\d+) times on (\d+) tablets", b4m)
win = re.search(r"30-multiple \(30,60,120,150\): (\d+) \| of a 45-multiple \(45,135\): (\d+) \| total (\d+)", b60)
chance6 = float(re.search(r"expected by chance in any 6-degree window: ([\d.]+)", b60).group(1))

summary = dict(
    built='2026-10-18',
    headline=dict(signs=len(conf), wedges=sum(len(s['W']) for s in conf), groups=sum(len(s['G']) for s in conf), textShare=round(sum(s['share'] for s in conf), 1),
                  tablets=num(b3, r"tablets (\d+)"), lines=num(b4t, r"complete lines \(no break, no damage\): (\d+)"), runs=num(b3, r"not touching a break or an unconfirmed sign (\d+)"),
                  heldOut=[s['cp'] for s in D['signs'] if s['st'] != 'confirmed']),
    ladders=dict(diamond=[geom(c) for c in diamond], down=[geom(c) for c in down], hooks=[geom(c) for c in hooks], offBy=off_by,
                 fit=num(b4s, r"signs that fit some ladder: (\d+)"), gapsPredicted=num(b5, r"gaps predicted (\d+)"), gapsFilled=num(b5, r"filled by a held-out sign (\d+)")),
    hookCap=dict(rows=hook_rows, downAfterHooks=[dict(n=n, uses=pre['after hooks'].get(n, 0)) for n in range(1, 10)], tenHookBefore=fol['then down wedges'].get(10, 0), tenHookEnd=fol['end of run'].get(10, 0)),
    sums=dict(hook=sumsA, lead=sumsB),
    groupSizes=[dict(size=k, groups=v) for k, v in sorted(gs.items())],
    records=dict(repeatShare=num(b4t, r"also appears on another tablet: ([\d.]+)%", float), distinct=num(b4t, r"distinct lines: (\d+) of"), layoutCount=int(rec.group(1)), layoutTablets=int(rec.group(2)),
                 layout='N a b · N a c · N d e · N d f · N d g', numberFirst=num(b4t, r"\('N', '([\d.]+)%'\)", float), numberShare=num(b4t, r"N is ([\d.]+)% of all tokens", float),
                 symbols=num(b4t, r"symbols in use: (\d+)"), top100=num(b4t, r"top 100 cover ([\d.]+)%", float)),
    context=dict(bins=ctx_bins, rank=num(b5, r"shape distance vs context alike: (-?[\d.]+)", float), pairs=num(b5, r"(\d+) pairs\n"),
                 ladderPairs=int(lad.group(1)), ladderAlike=float(lad.group(2)), ladderBase=float(lad.group(3)), partPairs=int(part.group(1)), partAlike=float(part.group(2)), partBase=float(part.group(3))),
    angles=dict(at30s=int(win.group(1)), at45s=int(win.group(2)), total=int(win.group(3)), chancePerWindow=chance6),
    nearest=dict(identical=len(re.findall(r"\('[0-9A-F]+', '[0-9A-F]+'\)", b4s.split('signs identical to another (0 changes):')[1])) // 2,
                 oneChange=dict(ast.literal_eval(re.search(r"\n\s+(\[\(0, .*?\)\]) \(10 means", b4s).group(1))).get(1)),
)
json.dump(summary, open(sys.argv[1], 'w'), indent=1)
print('wrote', sys.argv[1], '| headline', summary['headline'])
