#!/usr/bin/env python3
"""Reference parser for osl.asl -> signs.tsv + sign_values.tsv (kept separate).
Usage: python3 -I osl_parse.py /path/osl.asl outdir
Standard library only. Parses data; executes nothing from it."""
import re, sys, csv, json, collections

TAG = re.compile(r'^@([A-Za-z]+)([-+])?(?:[ \t]+(.*?))?[ \t]*$')
SUB = '₀₁₂₃₄₅₆₇₈₉'
OPS_LOOSE = '.+'          # beside / joining (lowest precedence)
OPS_TIGHT = '×&%@'        # containing / above / crossing / opposing

class Ent(dict):
    __getattr__ = dict.get

def parse_asl(path):
    ents, header, cur_sign, cur, last_tag = [], [], None, None, None
    tagcount = collections.Counter()
    with open(path, encoding='utf8') as f:
        for ln, raw in enumerate(f, 1):
            line = raw.rstrip('\n')
            if not line.strip():
                continue
            if line == '@@':
                tagcount['@@'] += 1
                cur = cur_sign; continue
            m = TAG.match(line)
            if not m:                    # continuation line (leading whitespace)
                tagcount['(continuation)'] += 1
                continue
            tag, flag, arg = m.group(1), m.group(2) or '', (m.group(3) or '')
            tagcount['@' + tag + flag] += 1
            if tag in ('sign', 'pcun', 'xsux'):
                cur_sign = cur = Ent(kind=tag, name=arg, flag=flag, line=ln, lists=[], ucp=[], aka=[],
                                     values=[], sys=[], parent=None, forms=[])
                ents.append(cur)
            elif tag == 'end':
                cur_sign = cur = None
            elif tag == 'form':
                q = arg.endswith('?')
                cur = Ent(kind='form', name=arg.rstrip('?'), flag=flag, quest=q, line=ln, lists=[], ucp=[],
                          aka=[], values=[], sys=[], parent=cur_sign)
                if cur_sign is not None: cur_sign['forms'].append(cur)
                ents.append(cur)
            elif tag == 'compoundonly':
                ents.append(Ent(kind='compoundonly', name=arg, flag=flag, line=ln, lists=[], ucp=[], aka=[],
                                values=[], sys=[], parent=None))
                cur = ents[-1] if cur_sign is None else cur
            elif cur is None:
                header.append((tag, arg))
            elif tag == 'oid':   cur['oid'] = arg
            elif tag == 'list':
                tok = arg.split()[0]
                if tok.startswith('U+'): cur['ucp'].append(tok[2:])
                else: cur['lists'].append(arg)
            elif tag == 'uname': cur.setdefault('uname', arg)
            elif tag == 'ucun':  cur.setdefault('ucun', arg)
            elif tag == 'useq':  cur['useq'] = arg
            elif tag == 'upua':  cur['upua'] = arg
            elif tag == 'uage':  cur.setdefault('uage', arg)
            elif tag == 'aka':   cur['aka'].append(arg)
            elif tag == 'pname': cur['pname'] = arg
            elif tag == 'fake':  cur['fake'] = True
            elif tag == 'sys':   cur['sys'].append(arg)
            elif tag == 'v':
                lang = ''
                if arg.startswith('%'):
                    lang, _, arg = arg.partition(' ')
                unc = arg.endswith('?')
                val = arg[:-1] if unc else arg
                cur['values'].append(dict(value=val, lang=lang.lstrip('%'), deprecated=(flag == '-'),
                                          uncertain=unc, numeric=('(' in val), xval=val.endswith('ₓ') or 'ₓ(' in val))
            last_tag = tag
    return ents, header, tagcount

# ---------- compound-name parser (GDL-style, as observed in osl.asl) ----------
class P:
    def __init__(s, t): s.t, s.i = t, 0
    def peek(s): return s.t[s.i] if s.i < len(s.t) else ''
    def seq(s):
        items, ops = [s.tight()], []
        while s.peek() in OPS_LOOSE and s.peek():
            ops.append(s.peek()); s.i += 1; items.append(s.tight())
        return items[0] if not ops else {'op': ops[0] if len(set(ops)) == 1 else ''.join(ops), 'ops': ops, 'args': items}
    def is_opp(s):  # '@' as binary 'opposing' operator: followed by uppercase or '('
        if s.peek() != '@': return False
        nx = s.t[s.i+1:s.i+2]
        return bool(nx) and (nx == '(' or nx.isupper())
    def tight(s):
        node = s.unit()
        while s.peek() and (s.peek() in '×&%' or s.is_opp()):
            op = s.peek(); s.i += 1
            node = {'op': op, 'args': [node, s.unit()]}
        return node
    def unit(s):
        rep = None
        m = re.match(r'(\d+)×', s.t[s.i:])
        if m: rep = int(m.group(1)); s.i += m.end()
        m = re.match(r'(\d+(?:/\d+)?|N(?:/\d+)?)\(', s.t[s.i:])
        if m:
            s.i += m.end(); inner = s.seq()
            if s.peek() != ')': raise ValueError('expected ) at %d in %s' % (s.i, s.t))
            s.i += 1
            node = {'num': m.group(1), 'of': inner}
        elif s.peek() == '(':
            s.i += 1; node = s.seq()
            if s.peek() != ')': raise ValueError('expected ) at %d in %s' % (s.i, s.t))
            s.i += 1
            node = {'group': node}
        else:
            m = re.match(r'[^.+×&%@()|~]+', s.t[s.i:])
            if not m: raise ValueError('expected name at %d in %s' % (s.i, s.t))
            s.i += m.end(); node = {'s': m.group(0)}
        mods = []
        while True:
            m = re.match(r'@(\d+|[a-z])(?![A-Z(])|~[a-z0-9]+', s.t[s.i:])
            if not m or s.is_opp(): break
            mods.append(m.group(0)); s.i += m.end()
        if mods: node = {'mods': mods, 'base': node}
        if rep: node = {'rep': rep, 'of': node}
        return node

def parse_name(name):
    t = name[1:-1] if name.startswith('|') and name.endswith('|') else name
    p = P(t); n = p.seq()
    if p.i != len(t): raise ValueError('trailing %r in %s' % (t[p.i:], name))
    return n

def unparse(n):
    if 's' in n: return n['s']
    if 'mods' in n: return unparse(n['base']) + ''.join(n['mods'])
    if 'group' in n: return '(' + unparse(n['group']) + ')'
    if 'num' in n: return n['num'] + '(' + unparse(n['of']) + ')'
    if 'rep' in n: return '%d×%s' % (n['rep'], unparse(n['of']))
    ops = n.get('ops') or [n['op']] * (len(n['args']) - 1)
    out = unparse(n['args'][0])
    for o, a in zip(ops, n['args'][1:]): out += o + unparse(a)
    return out

def leaves(n):
    """Leaf component sign names (with modifiers, numbers kept whole)."""
    if 's' in n: return [n['s']]
    if 'mods' in n:
        if 's' in n['base'] or 'num' in n['base']: return [unparse(n)]
        return leaves(n['base'])
    if 'num' in n: return [unparse(n)]
    if 'group' in n: return leaves(n['group'])
    if 'rep' in n: return leaves(n['of'])
    return [x for a in n['args'] for x in leaves(a)]

def depth(n):
    if 's' in n or 'num' in n: return 0
    if 'mods' in n: return depth(n['base'])
    if 'group' in n: return depth(n['group'])
    if 'rep' in n: return 1 + depth(n['of'])
    return 1 + max(depth(a) for a in n['args'])

def is_compound(name): return name.startswith('|')
def is_numeral(name):
    return bool(re.match(r'^(\d+(/\d+)?|N(/\d+)?)\(', name) or re.match(r'^N\d\d', name))
def value_base(v):
    v = re.sub(r'[⁺⁻]', '', v)
    return re.sub(r'[%sₓ]+$' % SUB, '', v)

def main():
    path, outdir = sys.argv[1], sys.argv[2]
    ents, header, tagcount = parse_asl(path)
    with open(outdir + '/signs.tsv', 'w', encoding='utf8', newline='') as fs, \
         open(outdir + '/sign_values.tsv', 'w', encoding='utf8', newline='') as fv:
        ws = csv.writer(fs, delimiter='\t'); wv = csv.writer(fv, delimiter='\t')
        ws.writerow(['row', 'kind', 'oid', 'name', 'parent_oid', 'parent_name', 'deprecated', 'default_form', 'fake',
                     'is_compound', 'is_numeral', 'components', 'tree_json', 'unicode_cp', 'useq', 'upua', 'ucun',
                     'uname', 'uage', 'aka', 'lists', 'src_line'])
        wv.writerow(['row', 'oid', 'name', 'parent_oid', 'value', 'value_base', 'lang', 'deprecated', 'uncertain',
                     'numeric', 'x_value', 'on_form'])
        nv = 0
        for i, e in enumerate(ents):
            try:
                tree = parse_name(e.name); comps = leaves(tree) if is_compound(e.name) else []
                tj = json.dumps(tree, ensure_ascii=False) if is_compound(e.name) else ''
            except ValueError as ex:
                comps, tj = [], 'PARSE_ERROR'
            p = e.parent
            ws.writerow([i, e.kind, e.oid or '', e.name, (p.oid or '') if p else '', p.name if p else '',
                         int(e.flag == '-'), int(e.flag == '+'), int(bool(e.fake)), int(is_compound(e.name)),
                         int(is_numeral(e.name)), ' '.join(comps), tj, ' '.join(e.ucp), e.useq or '', e.upua or '',
                         e.ucun or '', e.uname or '', e.uage or '', ' '.join(e.aka), ' '.join(l.split()[0] for l in e.lists), e.line])
            for v in e['values']:
                nv += 1
                wv.writerow([i, e.oid or '', e.name, (p.oid or '') if p else '', v['value'], value_base(v['value']),
                             v['lang'], int(v['deprecated']), int(v['uncertain']), int(v['numeric']), int(v['xval']),
                             int(e.kind == 'form')])
    print('signs.tsv rows:', len(ents), ' sign_values.tsv rows:', nv)
    print('by kind:', dict(collections.Counter(e.kind for e in ents)))

if __name__ == '__main__':
    main()
