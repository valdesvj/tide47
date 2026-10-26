#!/usr/bin/env python3
"""build_p47.py - the calculator files (.p47) of Tide 47, made with rejig on your own computer.

  python3 tools/build_p47.py            every program below -> build/p47/NAME.p47 (not in git: *.p47 is ignored)
  python3 tools/build_p47.py NAME ...   only those
  python3 tools/build_p47.py --private  the private build instead (python3 tools/build_tide47.py --private first):
                                        private/build/TIDE47.txt (it calls the private regions too) and every data
                                        program of private/build/ -> private/build/p47/ (git-ignored)

For each program rejig converts the commented forum file (build/forum/NAME.p47u: its '@' lines and the comments
after ';' are not compiled) with --validate=r47 (C47 / R47), and, when there is one, the plain listing too
(build/NAME.txt, the steps only); the two .p47 must be the same bytes: the comments take no memory and no REM
step slipped in. Copy build/p47/*.p47 to the calculator's PROGRAMS folder and load them (or load the .p47u in a
C47 that reads them). Run the build first (python3 tools/build_tide47.py) so build/ is up to date.
Needs rejig on the PATH (or REJIG=/path/to/rejig)."""
import filecmp, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'build', 'p47')
# NAME: (the commented forum file, the plain listing or None), paths from the repository's root
PROGRAMS = {
    'TIDE47': ('build/forum/TIDE47.p47u', 'build/TIDE47.txt'),
    'TIDEME': ('build/forum/TIDEME.p47u', 'build/TIDEME.txt'),
    'TIDEUS': ('build/forum/TIDEUS.p47u', 'build/TIDEUS.txt'),
    'TIDELA': ('build/forum/TIDELA.p47u', 'build/TIDELA.txt'),
}


def rejig(src, dst):
    exe = os.environ.get('REJIG') or shutil.which('rejig')
    if not exe:
        raise SystemExit('rejig not found: put it on the PATH or set REJIG=/path/to/rejig')
    r = subprocess.run([exe, '--validate=r47', '-o', dst, src], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit('rejig %s:\n%s%s' % (os.path.relpath(src, ROOT), r.stdout, r.stderr))
    return r.stdout.strip()


def private_programs():
    """The private build: TIDE47 (plain: its regions differ from the public listing's comments) and the data
    programs of private/build/ (the forum file when there is one, else the plain listing)."""
    d = os.path.join(ROOT, 'private', 'build')
    if not os.path.isdir(d):
        raise SystemExit('no private/build/: run python3 tools/build_tide47.py --private first')
    out = {}
    for fn in sorted(os.listdir(d)):
        if fn.endswith('.txt'):
            name = fn[:-4]
            forum = os.path.join('private', 'build', 'forum', name + '.p47u')
            plain = os.path.join('private', 'build', fn)
            out[name] = (forum, plain) if os.path.exists(os.path.join(ROOT, forum)) else (plain, None)
    return out


def main(names):
    global OUT, PROGRAMS
    if '--private' in names:
        names = [n for n in names if n != '--private']
        OUT = os.path.join(ROOT, 'private', 'build', 'p47')
        PROGRAMS = private_programs()
    os.makedirs(OUT, exist_ok=True)
    bad = 0
    for name in names or list(PROGRAMS):
        forum, plain = PROGRAMS[name]
        src = os.path.join(ROOT, forum)
        if not os.path.exists(src):
            print('%-8s  no %s: run %s first' % (name, forum, 'python3 tools/build_tide47.py')); bad += 1; continue
        dst = os.path.join(OUT, name + '.p47')
        msg = rejig(src, dst)
        same = ''
        if plain and os.path.exists(os.path.join(ROOT, plain)):
            with tempfile.TemporaryDirectory() as d:
                tmp = os.path.join(d, name + '.p47')
                rejig(os.path.join(ROOT, plain), tmp)
                ok = filecmp.cmp(dst, tmp, shallow=False)
                same = '  = %s' % plain if ok else '  DIFFERS from %s (a comment became a step?)' % plain
                bad += not ok
        print('%-8s  %s  %6d bytes%s%s' % (name, os.path.relpath(dst, ROOT), os.path.getsize(dst), same,
                                                     ('  (' + msg + ')') if msg else ''))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
