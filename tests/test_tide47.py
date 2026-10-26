#!/usr/bin/env python3
"""test_tide47.py - the checks of Tide 47.

 1. the astronomy of python/tide47ref.py against NOAA's tables as XTide has them (tests/xtide_tables.json:
    V0 + u at January 1 and f at mid-year, 2020-2040, the 37 NOAA constituents; the speeds);
 2. (when utide is installed) a year of the twin's heights analysed by UTide (Codiga 2011): the constants of the port
    come back (amplitude, phase), an independent check of the nodal corrections;
 3. the C47 (build/TIDE47.txt and the data programs, in c47sim) against the twin, step for step: every port on three
    days, Boston on the days US daylight time starts and ends: the same high and low waters (time to 0.01 s,
    height to 1E-9 m) and the same curve;
 4. the keys: 6 4 3 1 5 (days), 2 8 (ports), + (regions); the end (0): R20-R99 cleared, no matrix left, GRFNT 20,
    GRMOD 0, the stack back; the screens written to docs/.
  python3 tests/test_tide47.py"""
import json, math, os, sys, time
from decimal import Decimal as D
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'python')]
import tide47ref as R          # noqa: E402
import stations                # noqa: E402
import tide47sim as S          # noqa: E402

FAIL = []


def check(ok, what):
    print('  %s  %s' % ('ok  ' if ok else 'FAIL', what), flush=True)
    if not ok:
        FAIL.append(what)


def test_astronomy():
    print('1. the astronomy against NOAA (XTide\'s tables)')
    xt = json.load(open(os.path.join(ROOT, 'tests', 'xtide_tables.json')))
    sp = dict(zip([c[0] for c in R.CONS], R.speeds()))
    check(all(abs(sp[n] - v) < 2e-6 for n, v in xt['speeds'].items()), 'the speeds of the 37 (to 2E-6 deg / h)')
    worst = {}
    for i, y in enumerate(xt['years']):
        a0 = R.astro(R.jd(y, 1, 1))[0]
        am = R.astro(R.jd(y, 7, 2))[0]
        vm = R.vector(R.jd(y, 7, 2))
        for (name, dd, k90, *_), (vum, fm) in list(zip(R.CONS, vm))[:R.NOAA37]:
            V0 = sum(c * x for c, x in zip(dd, a0)) + 90 * k90
            Vm = sum(c * x for c, x in zip(dd, am)) + 90 * k90
            if name == 'M1':          # XTide's table: tau - 90 + xi - nu + Q with V0 at January 1 (no p): + p0 - pm
                Vm -= (am[3] - a0[3] + 180) % 360 - 180
            d = (V0 + vum - Vm - xt['eq'][name][i] + 180) % 360 - 180
            w = worst.setdefault(name, [0, 0])
            w[0] = max(w[0], abs(d)); w[1] = max(w[1], abs(fm - xt['nf'][name][i]))
    bad = [n for n, (da, df) in worst.items() if da > (1 if n == 'M1' else 0.3) or df > (0.04 if n == 'M1' else 0.004)]
    check(not bad, 'V0 + u within 0.3 deg and f within 0.004 (M1: 1 deg, 0.04) for 2020-2040 %s' % (bad or ''))
    print('      the largest: %s' % ', '.join('%s %.2f deg %.4f' % (n, *worst[n]) for n in ('M2', 'K1', 'O1', 'S2', 'N2')))


def test_utide():
    print('2. the twin analysed by UTide')
    try:
        import numpy as np, utide, warnings
        warnings.filterwarnings('ignore')
    except ImportError:
        print('      utide not installed: skipped (pip install utide)')
        return
    names = {'LAM2': 'LDA2', 'M1': 'NO1', '2MK3': 'MO3'}
    for st in (stations.REGIONS[0][3][0], stations.REGIONS[1][3][0]):
        hc = {n: v for n, v in st['hc'].items() if n in [c[0] for c in R.CONS][:R.NOAA37] and n not in ('SA', '2SM2')}
        W = R.speeds()
        t, h = [], []
        j = R.jd(2026, 1, 1)
        for d in range(365):
            vf = R.vector(j + d)
            for k in range(24):
                s = 0
                for (n, *_), (vu, f), w in zip(R.CONS, vf, W):
                    if n in hc:
                        s += f * hc[n][0] * math.cos((vu + w * k - hc[n][1]) * R.D2R)
                t.append(j + d + k / 24 - 1721424.5); h.append(s)
        c = utide.solve(np.array(t), np.array(h), lat=st['lat'], constit=[names.get(n, n) for n in hc], nodal=True,
                        trend=False, method='ols', conf_int='none', verbose=False, epoch='python')
        got = dict(zip(c['name'], zip(c['A'], c['g'])))
        worst = (0, 0)
        for n, (H, g) in hc.items():
            if H >= 0.02:
                a, gg = got[names.get(n, n)]
                worst = (max(worst[0], abs(a - H)), max(worst[1], abs((gg - g + 180) % 360 - 180)))
        check(worst[0] < 0.006 and worst[1] < 0.5, '%s: the constants above 2 cm back within %.4f m, %.2f deg'
              % (st['name'], *worst))


def run_day(port_keys):
    """The C47's events and curve of the first day shown after the keys."""
    shots, c = S.run(port_keys)
    return shots, c


def test_c47():
    print('3. the C47 against the twin')
    days = [R.jdn(2026, 10, 25), R.jdn(2027, 3, 21), R.jdn(2028, 6, 30)]
    worst_t = worst_h = 0
    n = 0
    t0 = time.time()
    for ri, (code, label, title, ports) in enumerate(stations.REGIONS):
        for pi, st in enumerate(ports):
            for dn in days:
                y, m, d = R.cal(dn)
                clock = dn - 1 + 13 / 24 + 0.5 - 0.5          # c47sim's clock: the JD (.0 = noon) of 13:00 that day
                clock = dn + 1 / 24
                keys = [S.REGION] * ri + [S.DOWN] * pi
                shots, c = S.run(keys, clock=clock)
                fr, ev, n25, name = c.ev[-1]
                tz, tw, cu = R.day(st, dn)
                ok = name == st['name'] and n25 == dn and len(ev) == len(tw)
                for a, b in zip(ev, tw):
                    worst_t = max(worst_t, abs(a[0] - b[0]) * 3600); worst_h = max(worst_h, abs(a[1] - b[1]))
                    ok = ok and a[2] == b[2]
                if not ok:
                    check(False, '%s %04d-%02d-%02d: %s / %s' % (st['name'], y, m, d, ev, tw))
                n += 1
    check(worst_t < 0.01 and worst_h < 1e-9, '%d port-days: the same high and low waters (%.3g s, %.2g m)'
          % (n, worst_t, worst_h))
    print('      %.0f s here' % (time.time() - t0))
    boston = stations.REGIONS[1][3][0]
    for dn, want in ((R.jdn(2026, 3, 7), -5), (R.jdn(2026, 3, 8), -4), (R.jdn(2026, 10, 31), -4), (R.jdn(2026, 11, 1), -5)):
        shots, c = S.run([S.REGION], clock=dn + 1 / 24)
        check(float(R.day(boston, dn)[0]) == want, 'Boston %04d-%02d-%02d: UTC%+d (twin)' % (R.cal(dn) + (want,)))
        snap = c.ev[-1]
        tz, tw, cu = R.day(boston, dn)
        check(len(snap[1]) == len(tw) and all(abs(a[0] - b[0]) < 1e-5 for a, b in zip(snap[1], tw)),
              'Boston %04d-%02d-%02d: the C47 the same' % R.cal(dn))


def test_keys():
    print('4. the keys and the end')
    dn = R.jdn(2026, 10, 25)
    steps = [(S.RIGHT, 1), (S.RIGHT, 2), (S.LEFT, 1), (S.WEEKF, 8), (S.WEEKB, 1), (S.TODAY, 0)]
    shots, c = S.run([k for k, _ in steps])
    days = [e[2] - dn for e in c.ev]
    check(days == [0] + [d for _, d in steps], 'days: %s' % days)
    shots, c = S.run([S.DOWN, S.DOWN, S.UP, S.UP, S.UP])
    names = [e[3] for e in c.ev]
    me = [p['name'] for p in stations.REGIONS[0][3]]
    check(names == [me[0], me[1], me[2], me[1], me[0], me[-1]], 'ports: %s' % names)
    shots, c = S.run([S.REGION, S.REGION, S.REGION])
    names = [e[3] for e in c.ev]
    check(names == [stations.REGIONS[i % 3][3][0]['name'] for i in range(4)], 'regions: %s' % names)
    import c47sim
    cc = c47sim.load(S.PROGS)
    cc.s = [D(11), D(22), D(33), D(44)]; cc.pix = []; cc.keys = [S.END]; cc.steps = 0; cc.clock = S.CLOCK; cc.frames = []
    cc.lastx = D(55)
    cc.reg['5'] = D(7)
    cc.run('TIDE47', maxsteps=10 ** 9)
    left = [k for k in cc.reg if k.isdigit() and 20 <= int(k) <= 99 and cc.reg[k] not in (0, D(0), '')]
    check(not left, 'R20-R99 cleared %s' % (left or ''))
    check(not cc.mats, 'no matrix left %s' % (sorted(cc.mats) or ''))
    check(getattr(cc, 'grfnt', 20) == 20 and getattr(cc, 'grmod', 0) == 0, 'GRFNT 20, GRMOD 0')
    check([int(v) for v in cc.s[:4]] == [11, 22, 33, 44] and cc.reg.get('5') == D(7), 'the stack and R05 back')
    shots, c = S.run([])
    print('      the start %d steps (%.1f s on the C47); a port %d (%.1f s)' % (
        c.at_steps[0], S.secs(c.at_steps[0]), 0, 0) if False else '      the start: %d steps, %.1f s on the C47'
          % (c.at_steps[0], S.secs(c.at_steps[0])))
    shots, c = S.run([S.RIGHT, S.DOWN])
    print('      a day: %d steps (%.1f s), a port: %d steps (%.1f s)' % (
        c.at_steps[1] - c.at_steps[0], S.secs(c.at_steps[1] - c.at_steps[0]),
        c.at_steps[2] - c.at_steps[1], S.secs(c.at_steps[2] - c.at_steps[1])))


def test_probe():
    print('5. only some data programs loaded (LBL?), an older one, none')
    import tempfile
    B = os.path.join(ROOT, 'build')
    P = {k: os.path.join(B, k + '.txt') for k in ('TIDE47', 'TIDEME', 'TIDEUS', 'TIDELA')}
    first = {lab: reg[3][0]['name'] for reg, lab in zip(stations.REGIONS, ('TIDEME', 'TIDEUS', 'TIDELA'))}
    shots, c = S.run([S.REGION, S.REGION], progs=[P['TIDE47'], P['TIDEUS']])
    names = [e[3] for e in c.ev]
    check(names == [first['TIDEUS']] * 3, 'TIDE47 + TIDEUS only: USA at the start, + stays there: %s' % names)
    shots, c = S.run([S.REGION, S.REGION], progs=[P['TIDE47'], P['TIDELA'], P['TIDEME']])
    names = [e[3] for e in c.ev]
    check(names == [first['TIDEME'], first['TIDELA'], first['TIDEME']], 'TIDEME + TIDELA: + goes from one to the other: %s'
          % names)
    old = open(P['TIDEUS'], encoding='utf-8').read().replace('\n60\nSTO 93\n', '\n', 1)
    assert old != open(P['TIDEUS'], encoding='utf-8').read()
    fn = os.path.join(tempfile.mkdtemp(), 'TIDEUS.txt')
    open(fn, 'w', encoding='utf-8').write(old)
    shots, c = S.run([S.REGION], progs=[P['TIDE47'], P['TIDEME'], fn])
    names = [e[3] for e in c.ev]
    check(names == [first['TIDEME']] * 2, 'an older TIDEUS (no R93) is left out (OLD DATA, REBUILD: TIDEUS): %s' % names)
    import c47sim
    cc = c47sim.load([P['TIDE47']])
    cc.s = [D(11), D(22), D(33), D(44)]; cc.pix = []; cc.keys = []; cc.steps = 0; cc.clock = S.CLOCK; cc.frames = []
    cc.run('TIDE47', maxsteps=10 ** 9)
    check(not cc.mats and [int(v) for v in cc.s[:4]] == [11, 22, 33, 44], 'TIDE47 alone: NO TIDE DATA, the end (no '
          'matrix left, the stack back)')


if __name__ == '__main__':
    test_astronomy()
    test_utide()
    test_c47()
    test_keys()
    test_probe()
    print('ALL OK' if not FAIL else '%d FAILED' % len(FAIL))
    sys.exit(1 if FAIL else 0)
