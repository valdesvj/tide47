#!/usr/bin/env python3
"""build_forum.py - the commented rejig sources (.p47u) of Tide 47, for the forum and the PROGRAMS folder of a C47
release (as Chess 47's, Logic 47's and Almanac 47's tools/build_forum.py: '@' header lines, then the steps).

  build/forum/TIDE47.p47u   from build/TIDE47.txt (the steps) and listings/TIDE47_doc.txt (the comments)
  build/forum/TIDEME.p47u, TIDEUS.p47u, TIDELA.p47u   the data programs (build/*.txt), each port named after ';'
  private/build/forum/TIDEAR.p47u ... with --private: the private data programs of private/build/ (git-ignored)

The steps are those of build/*.txt, one by one (the same .p47 as the plain listing): indented as the source
(STRUCT, two spaces a level), the partner numbers written (DO 01 ... ENDDO 01). After the '@' metadata, the
narrative of tools/forum/NAME.txt (TIDE47) or tools/forum/DATA.txt (a data program: its region and ports filled
in), in plain words, then the source's header as technical notes. The source's comment blocks (its REM lines) are
'@' lines before the steps they stand before; the name of a label (LBL :INIT:) is given after ';' on its LBL and
on each XEQ / GTO to it. rejig compiles neither '@' lines nor what follows ';', so the comments take no memory. A
line that starts with ';' or '#' would become a REM step on the calculator (Almanac 47 DEVELOPMENT_NOTES): none.

  python3 tools/build_tide47.py   (writes them too; --private: the private data programs' files as well)
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'build', 'forum')
AUTHOR = 'Victor Valdes'
SOURCE = 'https://github.com/valdesvj/tide47'
COL = 32                              # the column of the ';' comments (wider steps: two spaces after them)

HEAD = {
    'TIDE47': """@ Index:   Tide predictions: the high and low waters and the tide curve of a day, by harmonic constants
@ Author:  %(author)s
@ Version: %(version)s
@ Source:  %(source)s
@ Tested:  C47 simulator (python/c47sim.py): tests/test_tide47.py, the astronomy against NOAA's tables (XTide),
@ Tested:  the constants back from a year of predictions (UTide), the C47 against python/tide47ref.py (25 ports x 3
@ Tested:  days, to 0.01 s and 1E-12 m); not yet run on a calculator (LN and LBL? are new there)
@ Input:   the data programs loaded (TIDEME, TIDEUS, TIDELA: any of them); the day from the calculator's date
@ Output:  Mina Salman (Bahrain) 2026-10-25: the day's curve and the table of its high and low waters (LAT)
@
""",
}
DATA_HEAD = """@ Index:   Tide 47 data: %(title)s (%(n)d ports)
@ Author:  %(author)s
@ Version: %(version)s
@ Source:  %(source)s
@ Tested:  with TIDE47 in the C47 simulator (tests/test_tide47.py)
@ Input:   X = a port's number (1-%(n)d), or 0 for the region (called by TIDE47)
@ Output:  the port's name, time zone, datum, source, Z0 and the matrix HG of its harmonic constants
@
"""

STEP = re.compile(r'^\s*(\d+)  (.*)$')
NAMED = re.compile(r'^(\s*)(.*?)\s{4}\((\d+)\)$')            # "XEQ :INIT:    (83)", "DO    (01)"


def narrative(name):
    """tools/forum/NAME.txt: what the program does and how to use it, in plain words, as '@' lines."""
    fn = os.path.join(ROOT, 'tools', 'forum', name + '.txt')
    lines = open(fn, encoding='utf-8').read().rstrip('\n').split('\n')
    return ['@ ' + ln if ln.strip() else '@' for ln in lines] + ['@']


def parse(name):
    """The doc listing: the header comments, then [(indent, step text with names, number, comments before it)]."""
    head, steps, pending = [], [], []
    for ln in open(os.path.join(ROOT, 'listings', name + '_doc.txt'), encoding='utf-8'):
        ln = ln.rstrip('\n')
        m = STEP.match(ln)
        if m:
            body = m.group(2)
            ind = body[:len(body) - len(body.lstrip())]
            steps.append((ind, body.strip(), int(m.group(1)), pending)); pending = []
        elif ln.strip().startswith(';'):
            text = ln.strip()[1:].strip()
            (pending if steps else head).append(text)          # before step 1: the program's header
    return head, steps


def data_notes(name, plain, names):
    """Notes on numbered labels with no name (none in TIDE47)."""
    return {}


def data(label, title, ports, src_dir, out_dir, version):
    """The forum file of a data program: the '@' metadata, tools/forum/DATA.txt filled in, then its steps: each
    port's label named after ';', LBL 99 the region."""
    st = [s for s in open(os.path.join(src_dir, label + '.txt'), encoding='utf-8').read().split('\n') if s.strip()]
    f = dict(author=AUTHOR, version=version, source=SOURCE, title=title, n=len(ports))
    out = [(DATA_HEAD % f).rstrip('\n')]
    names = '; '.join(p['name'] for p in ports)
    text = open(os.path.join(ROOT, 'tools', 'forum', 'DATA.txt'), encoding='utf-8').read().rstrip('\n')
    text = text.replace('{LABEL}', label).replace('{TITLE}', title).replace('{N}', str(len(ports))).replace('{PORTS}', names)
    import textwrap
    wrapped, para = [], []
    for ln in text.split('\n') + ['']:                      # a paragraph filled in, then wrapped again
        if ln.strip() and not ln.startswith('----'):
            para.append(ln.strip()); continue
        if para:
            wrapped += textwrap.wrap(' '.join(para), 112, break_on_hyphens=False); para = []
        wrapped.append(ln)
    wrapped = wrapped[:-1]
    out += ['@ ' + ln if ln.strip() else '@' for ln in wrapped] + ['@', '']
    for k, step in enumerate(st):
        if ';' in step or step.lstrip().startswith(('#', '@')):
            raise SystemExit('%s step %d: %r would not survive rejig' % (label, k + 1, step))
        note = ''
        m = re.fullmatch(r'LBL (\d\d)', step)
        if step == 'LBL "%s"' % label:
            note = 'X = 0: the region (GTO 99); else the port X (XEQ IND)'
        elif m and m.group(1) == '99':
            note = 'the region: its title (R97), its number of ports (R96), the constituents (R93)'
        elif m:
            note = 'port %d: %s' % (int(m.group(1)), ports[int(m.group(1)) - 1]['name'])
        elif step == 'NEWMAT':
            note = 'HG: one number a constituent, H x 100000 + g (H in 0.1 mm, g in 0.01 degree)'
        out.append(step.ljust(COL) + '; ' + note if note else step)
    os.makedirs(out_dir, exist_ok=True)
    fn = os.path.join(out_dir, label + '.p47u')
    with open(fn, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out).rstrip('\n') + '\n')
    print('%s  %d steps, %d ports' % (os.path.relpath(fn, ROOT), len(st), len(ports)))


def build(name):
    head, steps = parse(name)
    plain = open(os.path.join(ROOT, 'build', name + '.txt'), encoding='utf-8').read().split('\n')
    plain = [s for s in plain if s.strip()]
    if len(plain) != len(steps):
        raise SystemExit('%s: %d steps in build/, %d in listings/' % (name, len(plain), len(steps)))
    m = re.search(r'v(\d+\.\d+\.\d+)', head[0])
    version = m.group(1) if m else '?'
    names = {}                                                    # label number -> :NAME:
    for ind, text, n, com in steps:
        mm = NAMED.match(ind + text)
        if mm and mm.group(2).startswith('LBL :'):
            names[mm.group(3)] = mm.group(2)[4:]
    out = [(HEAD[name] % dict(author=AUTHOR, version=version, source=SOURCE)).rstrip('\n')]
    data = data_notes(name, plain, names)
    out += narrative(name)
    out += ['@ ---- Technical notes (from the commented source) ----']
    out += ['@ ' + h if h else '@' for h in head] + ['@', '']
    for k, ((ind, text, n, com), step) in enumerate(zip(steps, plain)):
        if ';' in step or step.lstrip().startswith(('#', '@')):
            raise SystemExit('%s step %d: %r would not survive rejig' % (name, n, step))
        if com:                                                  # the source's comment block: '@' lines (not compiled)
            if com[0].startswith('----') and out[-1] != '':
                out.append('@')
            out += ['@ ' + ind + c if c else '@' for c in com]
        note = ''
        mm = re.fullmatch(r'(LBL|XEQ|GTO) (\d\d)', step)
        if mm and mm.group(2) in names:
            note = names[mm.group(2)] if mm.group(1) == 'LBL' else '-> ' + names[mm.group(2)]
        if k in data:
            note = (note + '  ' if note else '') + data[k]
        line = ind + step
        if note:
            line = line.ljust(COL) + '; ' + note if len(line) < COL else line + '  ; ' + note
        out.append(line)
    os.makedirs(OUT, exist_ok=True)
    fn = os.path.join(OUT, name + '.p47u')
    with open(fn, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out).rstrip('\n') + '\n')
    ncom = sum(1 for ln in out if ln.startswith('@ ') or re.search(r'\s; ', ln))
    print('build/forum/%s.p47u  %d steps, %d with a comment, version %s' % (name, len(plain), ncom, version))
    return out


def main(private=False):
    """TIDE47 and the public data programs; with private: the data programs of private/build/ too."""
    sys.path.insert(0, os.path.join(ROOT, 'python'))
    import stations
    head = open(os.path.join(ROOT, 'programs_rem', 'TIDE47.txt'), encoding='utf-8').readline()
    m = re.search(r'v(\d+\.\d+\.\d+)', head)
    version = m.group(1) if m else '?'
    build('TIDE47')
    for code, label, title, ports in stations.REGIONS:
        data(label, title, ports, os.path.join(ROOT, 'build'), OUT, version)
    if private:
        import stations_private
        for code, label, title, ports in stations_private.REGIONS:
            data(label, title, ports, os.path.join(ROOT, 'private', 'build'),
                 os.path.join(ROOT, 'private', 'build', 'forum'), version)


if __name__ == '__main__':
    main('--private' in sys.argv)
