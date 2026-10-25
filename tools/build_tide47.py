#!/usr/bin/env python3
"""Build the TIDE47 files from the commented source programs_rem/TIDE47.txt (as Chess 47, Zones 47, Logic 47):
named labels LBL :NAME: get free local numbers, the STRUCT commands are checked as the firmware's VALID does and
numbered, the REM lines and the indentation go. Written by the build into the source:
  {NAME}            a constant of the nodal formulas (python/tide47ref.py K: one value for both twins)
  REM ==== CONS     the matrices DM (Doodson numbers), UM (the nodal u), EM (the node-factor powers x 2), one
                    number a row (two digits a column, + 50: LBL :ROW: unpacks it), from tide47ref.CONS
  REM ==== NCONS    the number of constituents
The data programs TIDEME, TIDEUS, TIDELA (one a region) are written from python/stations.py: X = the port's number
(0: R96 the number of ports, R97 the region's title); a port: its name, time zone, DST, datum, source, the mean
sea level above the datum, and the matrix HG (a number a constituent: H in 0.1 mm x 100000 + g in 0.01 deg).
Files: programs/ and build/ TIDE47.txt TIDEME.txt TIDEUS.txt TIDELA.txt (the calculator files, to convert with
rejig), listings/TIDE47_doc.txt (numbered steps with comments), listings/TIDE47_labels.txt.
  python3 tools/build_tide47.py              the public build (3 regions)
  python3 tools/build_tide47.py --private    private/build/: TIDE47 with the regions of python/stations_private.py
                                             too (+ cycles through them) and their data programs (never in git)"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = 'TIDE47'
NAMED_RE = re.compile(r'(LBL|GTO|XEQ) :([A-Za-z0-9?]{1,7}):$')
OPENERS = {'IF': 'ENDIF', 'DO': 'ENDDO', 'REPEAT': 'UNTIL'}
STRUCT = ('IF', 'ELSE', 'ENDIF', 'DO', 'WHILE', 'ENDDO', 'REPEAT', 'UNTIL')
DM42_MAX = 255                 # the C47 / R47 / DM42n (TIDE47 is for them, not the old DM42)
C47_LEVELS = 63
NOT_USED = ('FOR', 'NEXT', 'FORₓ', 'NEXTₓ', 'FOR𝑦ˣ', 'FORᵀᴼᴾ')


def is_test(step):
    """A step that leaves a test answer (the firmware's structTest list: the comparisons, the flag and type
    tests ending with ?, the counters, KEY?)."""
    op = step.split(' ')[0]
    return op.endswith('?') or op in ('DSE', 'ISG', 'DSZ', 'ISZ', 'DSL', 'ISE')


def structures(steps):
    """The steps with the partner numbers of the STRUCT commands, as VALID numbers them (manage.c /
    structured.c structWalkProgram): per program, IF, DO and REPEAT in three series from 1, in the order
    the openers appear; ELSE, WHILE, ENDDO, ENDIF, UNTIL take the number of their opener. Stops on what
    VALID refuses (a closer without its opener or of another kind, a structure left open at END or across
    a routine (RTN then LBL), a DO without WHILE, an IF / WHILE / UNTIL without a test just before it) and
    on a test before ELSE, ENDIF, DO, ENDDO, REPEAT or UNTIL: the firmware never skips those (structured.c
    structNoLegacySkip)."""
    out, open_, n = [], [], {}

    def fail(i, msg):
        raise SystemExit('STRUCT, step %d (%s): %s' % (i + 1, steps[i], msg))
    for i, s in enumerate(steps):
        op = s.split(' ')[0]
        prev = steps[i - 1] if i else ''
        if op in NOT_USED:
            fail(i, 'FOR / NEXT not used here (they take the start, end and step off the stack)')
        if op in STRUCT and s != op:
            fail(i, 'written without a number: the build numbers the structures')
        if op in ('IF', 'WHILE', 'UNTIL') and not is_test(prev):
            fail(i, 'no test just before it')
        if op in ('ELSE', 'ENDIF', 'DO', 'ENDDO', 'REPEAT', 'UNTIL') and is_test(prev) and not op == 'UNTIL':
            fail(i, 'a test before it: the firmware never skips a structure step')
        if s == 'END' or (s.startswith('LBL ') and prev == 'RTN'):
            if open_:
                fail(i, 'structure %s %02d still open' % tuple(open_[-1][:2]))
            if s == 'END':
                n = {}
        if op in OPENERS:
            n[op] = n.get(op, 0) + 1
            # the original DM42 (c43 structured.h, OLD_HW): 10 numbers of each kind per program, 10 levels
            if n[op] > DM42_MAX or len(open_) >= C47_LEVELS:
                fail(i, 'past the C47 limit: %d %s a program, %d levels (structured.h)' % (DM42_MAX, op, C47_LEVELS))
            open_.append([op, n[op], False])
            out.append('%s %02d' % (op, n[op]))
            continue
        if op in STRUCT:
            want = {'ELSE': 'IF', 'ENDIF': 'IF', 'WHILE': 'DO', 'ENDDO': 'DO', 'UNTIL': 'REPEAT'}[op]
            if not open_ or open_[-1][0] != want:
                fail(i, 'no %s open here' % want)
            top = open_[-1]
            if op in ('ELSE', 'WHILE'):
                if top[2]:
                    fail(i, 'a second %s' % op)
                top[2] = True
            if op == 'ENDDO' and not top[2]:
                fail(i, 'a DO without WHILE')
            if op in ('ENDIF', 'ENDDO', 'UNTIL'):
                open_.pop()
            out.append('%s %02d' % (op, top[1]))
            continue
        out.append(s)
    if open_:
        raise SystemExit('STRUCT: %s %02d still open at the end' % tuple(open_[-1][:2]))
    return out


def estimate(steps):
    """Estimated .p47 bytes of a program: 2.3 bytes per command, 2 + its characters per number and
    per binary number, 2 + its UTF-8 bytes per text. Calibrated on Almanac 47's MOON47 (4 836 bytes) and
    NAVFULL (24 160 bytes), within 3 % of both; rejig gives the real size."""
    b = 0.0
    for s in steps:
        if s.startswith('"'):
            b += 2 + len(s.encode('utf-8')) - 2
        elif re.fullmatch(r'-?[\d.]+(E-?\d+)?|[01]+#2', s):
            b += 2 + len(s)
        elif NAMED_RE.match(s):
            b += 3 + len(s.split(':')[1])      # command, 249, length, the name (bytes of the test program)
        else:
            b += 2.3
    return int(round(b))


def resolve(steps):
    """The steps with each named label replaced by a free local number (the fallback file), and the
    numbers: the numbers 00-99 not taken by a numeric label of the first program (the other programs
    have their own local labels), in order. Stops on a name defined twice, a name used but not defined,
    more labels than 00-99."""
    defs = [m.group(2) for s in steps for m in [NAMED_RE.match(s)] if m and m.group(1) == 'LBL']
    dup = sorted({d for d in defs if defs.count(d) > 1})
    if dup:
        raise SystemExit('named labels defined twice: %s' % ', '.join(dup))
    used = {m.group(2) for s in steps for m in [NAMED_RE.match(s)] if m}
    if used - set(defs):
        raise SystemExit('named labels used but not defined: %s' % ', '.join(sorted(used - set(defs))))
    bad = [s for s in steps if re.match(r'(LBL|GTO|XEQ) :', s) and not NAMED_RE.match(s)]
    if bad:
        raise SystemExit('a named label is 1-7 letters or digits between colons: %s' % bad[:3])
    first = steps[:steps.index('END') + 1] if 'END' in steps else steps
    taken = {int(m.group(1)) for s in first for m in [re.fullmatch(r'LBL (\d\d)', s)] if m}
    free = [n for n in range(100) if n not in taken]
    if len(defs) > len(free):
        raise SystemExit('%d named labels, only %d local numbers free' % (len(defs), len(free)))
    num = dict(zip(defs, free))
    return [NAMED_RE.sub(lambda m: '%s %02d' % (m.group(1), num[m.group(2)]), s) for s in steps], num


def programs(steps):
    """The programs of a list of steps (each ends with END)."""
    out, cur = [], []
    for s in steps:
        cur.append(s)
        if s == 'END':
            out.append(cur); cur = []
    return out


def source_steps(lines):
    """The steps of the source lines: no REM, no empty lines, the indentation off."""
    return [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith('REM')]


def regions(private=False):
    """The regions: python/stations.py, and with private=True also python/stations_private.py (not in git: data
    that may not be published, such as constants worked out from Aramco's tables; tools/make_private.py)."""
    sys.path.insert(0, os.path.join(ROOT, 'python'))
    import stations
    out = list(stations.REGIONS)
    if private:
        try:
            import stations_private
        except ImportError:
            raise SystemExit('no python/stations_private.py: run tools/make_private.py first')
        out += list(stations_private.REGIONS)
    return out


def region_steps(regs):
    """LBL :REG:'s body: one IF a region (X = the port's number in R90)."""
    out = []
    for i, (code, label, title, ports) in enumerate(regs, 1):
        out += [str(i), 'RCL 20', 'X=Y?', 'IF', '  RCL 90', '  XEQ "%s"' % label, 'ENDIF']
    return out


def fill(lines, regs):
    """The markers and the {NAME} constants."""
    sys.path.insert(0, os.path.join(ROOT, 'python'))
    import tide47ref as R
    out = []
    for ln in lines:
        ind = ln[:len(ln) - len(ln.lstrip())]
        if ln.strip() == 'REM ==== CONS':
            out.append(ind + 'REM the matrices DM UM EM of python/tide47ref.py CONS, a row a number (written by the build)')
            out += [ind + st for st in cons_steps(R)]
        elif ln.strip() == 'REM ==== NCONS':
            out.append(ind + str(len(R.CONS)))
        elif ln.strip() == 'REM ==== REGIONS':
            out.append(ind + 'REM the regions %s (written by the build)' % ' '.join(r[1] for r in regs))
            out += [ind + st for st in region_steps(regs)]
        elif ln.strip() == 'REM ==== NREG':
            out.append(ind + str(len(regs)))
        else:
            for k, v in R.K.items():
                ln = ln.replace('{%s}' % k, repr(v))
            if re.search(r'\{[A-Z0-9]+\}', ln) and not ln.lstrip().startswith('REM'):
                raise SystemExit('unknown constant in: ' + ln)
            out.append(ln)
    return out


def pack(vals, scale=1):
    """A row as one number: two digits a value (value x scale + 50), the first value the leftmost."""
    n = 0
    for v in vals:
        d = int(round(v * scale)) + 50
        assert 0 <= d < 100, vals
        n = n * 100 + d
    return n


def cons_steps(R):
    k = len(R.CONS)
    out = []
    for mat, n, scale, rows in (
            ('DM', 7, 1, [list(dd) + [k90] for _, dd, k90, _, _ in R.CONS]),
            ('UM', 7, 1, [[uc.get(b, 0) for b in R.UB] for _, _, _, uc, _ in R.CONS]),
            ('EM', 10, 2, [[fc.get(b, 0) for b in R.FB] for _, _, _, _, fc in R.CONS])):
        out += [str(k), str(n), 'NEWMAT', 'STO "%s"' % mat, 'INDEX "%s"' % mat, str(n), 'STO 48', str(scale), 'STO 46']
        for r in rows:
            out += [str(pack(r, scale)), 'XEQ :ROW:']
    return out


def data_program(code, label, title, ports):
    """The steps of a region's data program."""
    import tide47ref as R
    names = [c[0] for c in R.CONS]
    st = ['LBL "%s"' % label, 'X=0?', 'GTO 99', 'STO 99', 'XEQ IND 99', 'RTN',
          'LBL 99', '"%s"' % title, 'STO 97', str(len(ports)), 'STO 96', 'RTN']
    for i, p in enumerate(ports, 1):
        st += ['LBL %02d' % i, '"%s"' % p['name'], 'STO 26', repr(p['tz']), 'STO 27', '1' if p['dst'] == 'US' else '0',
               'STO 28', '"%s"' % p['datum'], 'STO 29', '"%s"' % p['src'], 'STO 95', repr(p['z0']), 'STO 24',
               str(len(names)), '1', 'NEWMAT', 'STO "HG"', 'INDEX "HG"']
        for n in names:
            H, g = p['hc'].get(n, (0.0, 0.0))
            v = int(round(H * 1e4)) * 100000 + int(round(g * 100)) % 36000
            st += [str(v), 'STOEL', 'J+']
        st.append('RTN')
    st.append('END')
    return st


def build_data(regs, dirs):
    out = []
    for code, label, title, ports in regs:
        st = data_program(code, label, title, ports)
        for d in dirs:
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, label + '.txt'), 'w', encoding='utf-8') as fh:
                fh.write('\n'.join(st) + '\n')
        out.append((label, len(st), estimate(st), len(ports)))
    return out


def labels_text(lines, num):
    out = ['TIDE47 local labels: name (programs_rem/TIDE47.txt), number (build/TIDE47.txt), what it does', '']
    for i, ln in enumerate(lines):
        m = NAMED_RE.match(ln)
        if m and m.group(1) == 'LBL':
            j = i
            while j > 0 and lines[j - 1].startswith('REM'):
                j -= 1
            note = lines[j][3:].strip(' -') if j < i else ''
            note = re.sub(r'^(LBL )?:%s:\s*' % m.group(2), '', note)
            out.append(':%s:%s %02d  %s' % (m.group(2), ' ' * (8 - len(m.group(2))), num[m.group(2)], note[:90]))
    return '\n'.join(out) + '\n'


def build(regs, dirs, listings=True):
    src = os.path.join(ROOT, 'programs_rem', NAME + '.txt')
    lines = fill([ln.rstrip() for ln in open(src, encoding='utf-8')], regs)
    steps = source_steps(lines)
    numeric, num = resolve(steps)
    numeric = structures(numeric)
    if [s for s in steps if s.startswith('LBL "')] != ['LBL "%s"' % NAME] or steps.count('END') != 1:
        raise SystemExit('one program, %s' % NAME)
    listing, n = [], 0
    for ln in lines:
        if not ln.strip():
            continue
        ind = ln[:len(ln) - len(ln.lstrip())]
        if ln.lstrip().startswith('REM'):
            listing.append('      ' + ind + '; ' + ln.lstrip()[3:].strip())
        else:
            extra = '' if numeric[n] == steps[n] else '    (%s)' % numeric[n].split(' ', 1)[1]
            listing.append('%4d  %s' % (n + 1, ind + steps[n] + extra))
            n += 1
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, NAME + '.txt'), 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(numeric) + '\n')
    if not listings:
        return numeric
    os.makedirs(os.path.join(ROOT, 'listings'), exist_ok=True)
    with open(os.path.join(ROOT, 'listings', NAME + '_doc.txt'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(listing) + '\n')
    with open(os.path.join(ROOT, 'listings', NAME + '_labels.txt'), 'w', encoding='utf-8') as fh:
        fh.write(labels_text(lines, num))
    return numeric


if __name__ == '__main__':
    private = '--private' in sys.argv
    regs = regions(private)
    if private:                                            # private/build/: TIDE47 with the private regions, and theirs
        dirs = [os.path.join(ROOT, 'private', 'build')]
        st = build(regs, dirs, listings=False)
        data = build_data(regs[3:], dirs)
    else:
        dirs = [os.path.join(ROOT, 'programs'), os.path.join(ROOT, 'build')]
        st = build(regs, dirs)
        data = build_data(regs, dirs)
    print('%s %5d steps, %2d local labels, about %d bytes (.p47, estimated); IF %d, DO %d' % (
        NAME, len(st), sum(1 for s in st if re.match(r'LBL \d\d', s)), estimate(st),
        sum(1 for s in st if s.startswith('IF ')), sum(1 for s in st if s.startswith('DO '))))
    for label, n, b, ports in data:
        print('%-7s %5d steps, %2d ports, about %d bytes' % (label, n, ports, b))
