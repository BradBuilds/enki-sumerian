#!/usr/bin/env python3
"""ingest.py - ORACC corpusjson zip -> clean sign-occurrence table (TSV).  Standard library only.
Usage: python3 -I ingest.py <zip> <outprefix> [--resolve] [--check] [--max N]
  --resolve : ignore native oid, resolve the editor's transliteration to a sign id with osl.asl
  --check   : (with --resolve on a build that HAS native oids) compare resolved vs native oid
Outputs: <outprefix>.signs.tsv        clean stream (S sign, X illegible position, G gap in line, B block/non-text state, P punctuation, W excised word)
         <outprefix>.quarantine.tsv   interpretive labels keyed by row id (NOT for pattern discovery)
         <outprefix>.report.txt       rule-by-rule counts
Never written to the clean table: reading values, lemma, language, word boundaries, determinative/logogram role.
The reading IS read (in memory only) when --resolve is on: it is the only route to a sign id in legacy builds."""
import sys, json, re, zipfile, collections, multiprocessing as mp, unicodedata
import os
ASL = os.environ.get('OSL_ASL', os.path.join('data', 'raw', 'osl', '00lib', 'osl.asl'))   # the Oracc sign list file (see README)
TOK = re.compile(r'<<|>>|<\(|\)>|\[|\]|<|>|\(|\)')
OPEN = {'[': 'brk', '<<': 'excised', '<(': 'implied', '<': 'supplied', '(': 'maybe'}
CLOSE = {']': 'brk', '>>': 'excised', ')>': 'implied', '>': 'supplied', ')': 'maybe'}
OBJ = {'tablet', 'envelope', 'prism', 'bulla', 'fragment', 'sealing', 'cylinder', 'object'}
SURF = {'obverse', 'reverse', 'left', 'right', 'top', 'bottom', 'edge', 'face', 'seal', 'docket', 'surface'}
SUBD = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
UNSUB = str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')

def load_asl():
    """name->oid ; value -> list of (parent_sign, holder, kind, deprecated) in file order"""
    name2oid = {}; oid2name = {}; vown = collections.defaultdict(list); sign = cur = None; kind = None; listref = []
    for ln in open(ASL, encoding='utf8'):
        if not ln.startswith('@'): continue
        p = ln.rstrip('\n').split(None, 1); t = p[0]; a = p[1].strip() if len(p) > 1 else ''
        if t in ('@sign', '@sign-', '@sign+', '@pcun'): sign = cur = a; kind = 'sign'
        elif t in ('@form', '@form-', '@form+'): cur = a.rstrip('?'); kind = 'form'
        elif t == '@@': cur = sign; kind = 'sign'
        elif t == '@fake' and cur: FAKE.add(cur)
        elif t == '@oid' and cur:
            if kind == 'sign': name2oid[cur] = a
            else: name2oid.setdefault(cur, a)
            oid2name.setdefault(a, cur)
        elif t == '@aka' and cur and cur in name2oid: name2oid.setdefault(a, name2oid[cur])
        elif t == '@list' and cur and a and not a.startswith('U+'): listref.append((a.split()[0], cur))
        elif t in ('@v', '@v-') and cur:
            v = (a.split()[-1] if a.startswith('%') else a.split()[0]).rstrip('?')
            vown[v].append((sign, cur, kind, t == '@v-'))
        elif t == '@end': sign = cur = None
    for ref, cur in listref:
        if cur in name2oid: name2oid.setdefault(ref, name2oid[cur])
    return name2oid, oid2name, dict(vown)

N2O = O2N = VOWN = None
FAKE = set()        # names flagged @fake in osl.asl (placeholders such as O = blank space; not signs)
def norm(s): return unicodedata.normalize('NFC', s).replace('ḫ', 'h').replace('Ḫ', 'H')

def res_value(v):
    """-> (oid, status)  status U unique | F parent-vs-form (parent chosen) | M several signs | '' unresolved"""
    own = VOWN.get(v)
    if not own: return None, ''
    parents = []
    for s, h, k, dep in own:
        if s not in parents: parents.append(s)
    if len(parents) == 1:
        s = parents[0]; holders = {h for _, h, _, _ in own}
        if holders == {s}: return N2O.get(s), 'U'
        if s in holders:   return N2O.get(s), 'F'          # listed on sign and on a variant form: parent sign
        if len(holders) == 1: return N2O.get(next(iter(holders))), 'f'   # only on one form: that form
        return N2O.get(s), 'F'
    live = []
    for s, h, k, dep in own:
        if k == 'sign' and not dep and s not in live: live.append(s)
    if len(live) == 1: return N2O.get(live[0]), 'F'
    if live: return N2O.get(live[-1]), 'M'
    return N2O.get(parents[-1]), 'M'

def res_name(nm):
    if nm in N2O: return N2O[nm], 'C'
    a = nm.translate(UNSUB) if re.match(r'^\|?\d*\(?N[₀-₉]', nm) else None      # N₀₁ -> N01
    if a and a in N2O: return N2O[a], 'C'
    b = nm.replace('Ŋ', 'G').replace('DIGIR', 'DINGIR')
    if b != nm and b in N2O: return N2O[b], 'C'
    return None, ''

def resolve(g):
    """leaf -> (oid, status).  Reads the transliteration; returns only a sign id."""
    if 'q' in g:
        q = g.get('qualified', [])
        last = q[-1] if q else {}
        nm = last.get('s') or last.get('c') or last.get('form') or ''
        if not nm:
            m = re.search(r'\((.*)\)$', g['q']); nm = m.group(1) if m else ''
        o, s = res_name(norm(nm))
        if o: return o, 'Q'
        if nm.lower() != nm:
            o, s = res_value(norm(nm).lower())
            if o: return o, 'Q'
        return None, ''
    if 'n' in g:
        f = norm(g.get('form', ''))
        o, s = res_value(f)
        if o: return o, s
        o, s = res_name(f)
        if o: return o, s
        m = re.match(r'^([\d/]+|n)\((.*)\)$', f, re.I)
        if m:
            cnt, unit = m.group(1), m.group(2)
            o, s = res_name(cnt + '(' + unit.upper() + ')')
            if o: return o, s
            o, s = res_value(cnt + '(' + unit.lower() + ')')
            if o: return o, s
            # count(unit) not itself listed: resolve the unit sign U and look for COUNT(U)
            uo, us = res_name(unit)
            if not uo: uo, us = res_value(unit.lower())
            if uo:
                un = O2N.get(uo, '')
                m2 = re.match(r'^1\((.*)\)$', un)
                base = m2.group(1) if m2 else un
                o, s = res_name(cnt + '(' + base + ')')
                if o: return o, 'u'
                if cnt == '1': return uo, 'u'
                return None, 'n:' + cnt + '(' + base + ')'       # numeral not in list: caller mints a name-id
        return None, ''
    if 'c' in g: return res_name(norm(g['c']))
    if 's' in g:
        nm = norm(g['s'])
        o, s = res_name(nm)
        if o: return o, s
        o, s = res_value(nm.lower())
        return (o, 'c' if o else '')
    if 'v' in g: return res_value(norm(g['v']))
    if 'form' in g:
        nm = norm(g['form']); o, s = res_name(nm)
        if o: return o, s
        m = re.match(r'^([^@~]+)((?:[@~][a-z0-9]+)*)$', nm)
        if m and m.group(1).lower() == m.group(1):          # lower-case base + modifiers, e.g. u@c
            o, s = res_name(m.group(1).upper() + m.group(2))
            if o: return o, 'c'
            o, s = res_value(nm)
            if o: return o, s
    return None, ''

def surf_class(obj, surf):
    s = (surf or '').lower()
    if s.startswith('seal') or 'seal' in (obj or '').lower(): return 's'
    if s.startswith('obv') or s == 'o': return 'o'
    if s.startswith('rev') or s == 'r': return 'r'
    if s.split(' ')[0].rstrip('?') in ('left', 'right', 'top', 'bottom', 'edge') or s in ('l.e.', 'r.e.', 't.e.', 'b.e.'): return 'e'
    return 'x' if s else ''

def process(doc, do_resolve, do_check):
    C = collections.Counter(); rows = []; quar = []; chk = collections.Counter(); miss = collections.Counter()
    st = dict(obj='', surf='', col='', line_ix=0, label='', span=set(), pos=0, gap_open=False, field=0)
    text = doc.get('textid') or ''
    def emit(kind, oid='', name='', flags='', res='', num='', q=None):
        if kind == 'G':
            if st['gap_open']: return
            st['gap_open'] = True
        else: st['gap_open'] = False
        rows.append((text, st['obj'], st['surf'], surf_class(st['obj'], st['surf']), st['col'], str(st['line_ix']),
                     st['label'], str(st['pos']), kind, oid, name, flags, res, num))
        st['pos'] += 1
        C['emit_' + kind] += 1
        if q is not None: quar.append((len(rows) - 1,) + q)
    def leaf(g, word_ix, role, ctx):
        if 'x' in g:
            if g['x'] == 'ellipsis': C['in_gap_ellipsis'] += 1; emit('G', flags='ellipsis')
            else: C['skip_x_' + g['x']] += 1
            return
        C['in_sign_leaves'] += 1
        span = st['span']; here = set(span)
        for t in TOK.findall(g.get('o', '')):
            if t in OPEN: span.add(OPEN[t]); here.add(OPEN[t])
            else: here.add(CLOSE[t]); span.discard(CLOSE[t])
        brk = g.get('break', '') or ctx.get('brk', '')
        # ---- rules, in order ----
        if ctx.get('surro_implied'): C['drop_ditto_expansion'] += 1; return
        if 'implied' in here: C['drop_implied'] += 1; return
        if 'supplied' in here: C['drop_supplied'] += 1; return
        if ctx.get('corr_as_read'): C['drop_correction_as_read'] += 1; return
        if brk == 'missing': C['drop_restored'] += 1; emit('G', flags='restored'); return
        fl = []
        if brk == 'damaged': fl.append('d')
        if g.get('queried'): fl.append('q')
        if 'excised' in here: fl.append('e')
        if 'maybe' in here: fl.append('m')
        if ctx.get('corr_on_tablet'): fl.append('c')
        if g.get('gdl_remarked') and not ctx.get('corr_on_tablet'): fl.append('k')
        for k in ('lig', 'reord', 'alt'):
            if ctx.get(k): fl.append(k)
        v = g.get('v'); s = g.get('s')
        kindq = 'q' if 'q' in g else 'n' if 'n' in g else 'c' if 'c' in g else 's' if s is not None else 'v' if v is not None else 'm'
        num = ''
        unitq = ''
        if 'n' in g:
            sq = g.get('seq', [])
            r = [x['r'] for x in sq if 'r' in x]
            num = r[0] if r else ''
            f = g.get('form', '')
            m = re.match(r'^[^()]*\((.*)\)$', f); unitq = m.group(1) if m else ''
            if '(' not in f: C['bare_number_to_X'] += 1; emit('X', flags='barenum'); return
            if num in ('n', 'N') or f[:1] in 'nN': C['unknown_count_to_X'] += 1; emit('X', flags='ncount'); return
        if v in ('x', 'X', 'n', 'N') or s in ('X', 'x', 'N') or g.get('gdl_sign') == 'X':
            C['illegible_to_X'] += 1; emit('X', flags=','.join(fl)); return
        native = g.get('oid', '')
        oid = native; name = g.get('gdl_sign', ''); res = 'N' if native else ''
        if do_resolve:
            oid, res = resolve(g)
            if oid: name = O2N.get(oid, '')
            elif res.startswith('n:'): oid = res; name = res[2:]; res = 'n'
            else:
                oid = ''; name = ''
            if do_check and native and not ctx.get('corr_on_tablet'):
                if native >= 'o0900000':      # proto-cuneiform sign list (separate id space, not in osl.asl)
                    chk['pc_idspace_checked'] += 1
                    chk['pc_idspace_same_name'] += (name == g.get('gdl_sign'))
                    pcskip = True
                else: pcskip = False
                if pcskip: pass
                else: chk['checked'] += 1; chk['checked_' + kindq] += 1
                if pcskip: pass
                elif not oid or oid.startswith('n:'): chk['unresolved'] += 1; chk['unresolved_' + kindq] += 1
                elif oid == native: chk['agree'] += 1; chk['agree_res_' + res] += 1
                else:
                    chk['disagree'] += 1; chk['disagree_res_' + res] += 1; chk['disagree_' + kindq] += 1
                    miss[('DIS', g.get('v') or g.get('s') or g.get('form') or g.get('c') or g.get('q'), name, g.get('gdl_sign'))] += 1
        if not oid:
            C['unresolved_to_U'] += 1; C['unresolved_' + kindq] += 1
            miss[('UNRES', kindq, g.get('v') or g.get('s') or g.get('form') or g.get('c') or g.get('q'))] += 1
            # sign is on the tablet and was read, but has no id in the sign list: keep position, kind U
            rawname = (g.get('c') or g.get('s') or (g.get('form') if kindq == 'm' else '') or '')
            if kindq == 'q':
                mq = re.search(r'\((.*)\)$', g['q']); rawname = mq.group(1) if mq else ''
            emit('U', name=norm(rawname), flags=','.join(fl), q=('+'.join(role), kindq, word_ix, unitq, ctx.get('lang', '')))
            return
        if do_resolve and name == 'O' and name in FAKE:      # only the blank-space placeholder; other @fake entries are provisional numerals
            C['fake_listsign_to_P'] += 1; C['fake_' + name] += 1; emit('P', name='fake:' + name); return
        C['res_' + res] += 1
        emit('S', oid, name, ','.join(fl), res, num, q=('+'.join(role), kindq, word_ix, unitq, ctx.get('lang', '')))

    def gdl(nodes, word_ix, role, ctx):
        for g in nodes:
            if not isinstance(g, dict): continue
            if 'det' in g:
                gdl(g.get('seq', []), word_ix, role + ['det-' + g['det'] + '-' + g.get('pos', '')], ctx)
            elif 'gloss' in g:
                for w in g.get('seq', []):
                    gdl(w.get('gdl', []), word_ix, role + ['gloss-' + g['gloss']], ctx)
            elif 'gg' in g or 'surro' in g:
                kids = [k for k in g.get('group', []) if not (len(k) == 1 and 't' in k)]
                typ = g.get('gg') or 'surro'
                C['group_' + typ] += 1
                if typ == 'diszless':
                    C['in_sign_leaves'] += 1; C['bare_number_to_X'] += 1
                    if g.get('break') == 'missing': C['drop_restored'] += 1; C['bare_number_to_X'] -= 1; emit('G', flags='restored')
                    else: emit('X', flags='barenum')
                    continue
                for i, k in enumerate(kids):
                    c2 = dict(ctx)
                    r2 = role
                    if typ == 'correction' and len(kids) >= 2:
                        if i == 0: c2['corr_as_read'] = True; c2['_brk0'] = k.get('break', '')
                        else: c2['corr_on_tablet'] = True; c2['brk'] = kids[0].get('break', '')
                    elif typ == 'surro' and i > 0: c2['surro_implied'] = True
                    elif typ == 'ligature': c2['lig'] = True
                    elif typ == 'reordering': c2['reord'] = True
                    elif typ == 'alternation':
                        if i > 0: C['in_sign_leaves'] += 1; C['drop_alternation_2nd_candidate'] += 1; continue
                        c2['alt'] = True
                    elif typ == 'logo': r2 = role + ['logo']
                    if any(x in k for x in ('det', 'gloss', 'gg', 'surro')): gdl([k], word_ix, r2, c2)
                    else:
                        if typ == 'correction' and len(kids) >= 2 and i == 0:
                            # keep bracket bookkeeping in step, then drop
                            leaf(k, word_ix, r2, c2)
                        else: leaf(k, word_ix, r2, c2)
            elif any(k in g for k in ('v', 's', 'n', 'c', 'q', 'x', 'oid', 'form', 'mods')):
                leaf(g, word_ix, role, ctx)

    def cdl(nodes):
        for n in nodes:
            k = n.get('node')
            if k == 'd':
                t = n.get('type')
                if t in OBJ and (t == 'object' or 'subtype' in n or t in OBJ - {'object'}):
                    st.update(obj=n.get('subtype') or t, surf='', col='')
                elif t in SURF:
                    st.update(surf=n.get('label') or n.get('subtype') or t, col='')
                    if t != 'surface' and not n.get('label'): st['surf'] = t + (' ' + n.get('n') if n.get('n') else '')
                elif t == 'column': st.update(col=n.get('n', ''))
                elif t == 'line-start':
                    st['line_ix'] += 1; st.update(label=n.get('label', '') or n.get('n', ''), pos=0, gap_open=False)
                    st['span'] = set(); C['in_lines'] += 1
                elif t == 'nonx':
                    stt = n.get('state', '') or 'other'
                    C['nonx_' + stt] += 1
                    st['line_ix'] += 1; st.update(label='', pos=0, gap_open=False)
                    emit('B', name=stt, flags='%s/%s' % (n.get('extent', ''), n.get('scope', '')))
                elif t in ('nonw', 'excised', 'punct'):
                    fr = n.get('frag', '')
                    if t == 'excised' or fr.startswith('<<'): C['excised_word_W'] += 1; emit('W', flags='excised-word')
                    elif fr.strip() in ('*', ':', ':"', ":'", ':.', '/', '::', ':*'): C['punct_P'] += 1; emit('P', name=fr.strip())
                    else: C['nonw_other_skipped'] += 1
            elif k == 'l' or k == 'll':
                w = n if k == 'l' else (n.get('choices') or [{}])[0]
                ref = w.get('ref', ''); f = w.get('f', {})
                if 'gdl' not in f: C['word_without_gdl'] += 1
                gdl(f.get('gdl', []), ref.rsplit('.', 1)[-1] if ref else '', [], {'lang': f.get('lang', '')})
            if 'cdl' in n: cdl(n['cdl'])
    cdl(doc.get('cdl', []))
    return rows, quar, C, chk, miss

def work(a):
    global N2O, O2N, VOWN
    zp, names, do_resolve, do_check = a
    if do_resolve and N2O is None: N2O, O2N, VOWN = load_asl()
    z = zipfile.ZipFile(zp); out = []; C = collections.Counter(); K = collections.Counter(); M = collections.Counter(); qout = []
    for nm in names:
        raw = z.read(nm); C['files_in'] += 1
        if not raw.strip(): C['skip_empty_file'] += 1; continue
        doc = json.loads(raw)
        rows, quar, c, chk, miss = process(doc, do_resolve, do_check)
        C.update(c); K.update(chk); M.update(miss)
        nS = sum(1 for r in rows if r[8] in 'SXU')
        if nS == 0: C['skip_text_no_signs'] += 1; C['skip_text_no_signs_rows'] += len(rows); continue
        C['texts_out'] += 1
        out.append((rows, quar))
    return out, C, K, M

def main():
    zp, pref = sys.argv[1], sys.argv[2]
    do_resolve = '--resolve' in sys.argv; do_check = '--check' in sys.argv
    mx = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else None
    names = sorted(i.filename for i in zipfile.ZipFile(zp).infolist() if '/corpusjson/' in i.filename and i.filename.endswith('.json'))
    if mx: names = names[:mx]
    C = collections.Counter(); K = collections.Counter(); M = collections.Counter(); rid = 0
    oids = set(); seen = set()
    with mp.Pool(8) as pool, open(pref + '.signs.tsv', 'w', encoding='utf8') as fs, open(pref + '.quarantine.tsv', 'w', encoding='utf8') as fq:
        fs.write('rid\ttext\tobject\tsurface\tsurf_class\tcolumn\tline_ix\tline_label\tpos\tkind\toid\tsign_name\tflags\tres\tnum\n')
        fq.write('rid\trole\tleaf_kind\tword_ix\tunit_reading\tlang\n')
        jobs = [(zp, names[i:i + 400], do_resolve, do_check) for i in range(0, len(names), 400)]
        for out, c, k, m in pool.imap(work, jobs):
            C.update(c); K.update(k); M.update(m)
            for rows, quar in out:
                if rows[0][0] in seen: C['dup_text_id_in_zip'] += 1
                seen.add(rows[0][0])
                base = rid
                for r in rows:
                    fs.write(str(rid) + '\t' + '\t'.join(x.replace('\t', ' ').replace('\n', ' ') for x in r) + '\n'); rid += 1
                    if r[8] == 'S': oids.add(r[9])
                for q in quar:
                    fq.write(str(base + q[0]) + '\t' + '\t'.join(str(x) for x in q[1:]) + '\n')
    with open(pref + '.report.txt', 'w', encoding='utf8') as fr:
        def p(*a):
            s = ' '.join(str(x) for x in a); print(s); fr.write(s + '\n')
        p('# ingest.py', ' '.join(sys.argv[1:]))
        p('files_in', C['files_in'], 'empty', C['skip_empty_file'], 'no_signs', C['skip_text_no_signs'], 'texts_out', C['texts_out'])
        for k_, v_ in sorted(C.items()): p('  %-36s %d' % (k_, v_))
        p('distinct sign ids (kind S)', len(oids), ' rows written', rid)
        if do_check:
            p('# resolver check against native oid')
            for k_, v_ in sorted(K.items()): p('  %-30s %d' % (k_, v_))
            if K['checked']: p('  agreement %.4f%%  disagreement %.4f%%  unresolved %.4f%%' % (100 * K['agree'] / K['checked'], 100 * K['disagree'] / K['checked'], 100 * K['unresolved'] / K['checked']))
        p('# top unresolved / disagreeing')
        for k_, v_ in M.most_common(60): p('  ', v_, k_)

if __name__ == '__main__':
    main()
