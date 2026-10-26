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
 5. tidal streams: the C47 against the twin (tide47ref.sday) at every NOAA stream station on three days, and at a
    synthetic rotary station through a private-style build; the end after a stream day; tools/make_private_streams.py
    on current tables made from known constants (tests/synth_streams.py): a year fitted, the next predicted.
  python3 tests/test_tide47.py"""
import json, math, os, sys, time
from decimal import Decimal as D
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'python')]
import tide47ref as R          # noqa: E402
import stations                # noqa: E402
import streams                 # noqa: E402
import tide47sim as S          # noqa: E402
sys.path[:0] = [os.path.join(ROOT, 'tools'), os.path.join(ROOT, 'tests')]
ALLREG = stations.REGIONS + streams.REGIONS

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


def test_fast():
    print('3a. the v0.3 engine (one evaluation an hour, cubics) against the exact v0.2 method (tide47ref.day_exact)')
    wt = wh = wc = 0
    for _, _, _, ports in stations.REGIONS:
        for st in ports:
            for n in range(R.jdn(2026, 1, 1), R.jdn(2026, 1, 1) + 30):
                a, b = R.day(st, n), R.day_exact(st, n)
                ok = len(a[1]) == len(b[1]) and all(x[2] == y[2] for x, y in zip(a[1], b[1]))
                if not ok:
                    check(False, '%s day %d: %s / %s' % (st['name'], n, a[1], b[1]))
                for x, y in zip(a[1], b[1]):
                    wt = max(wt, abs(x[0] - y[0]) * 3600); wh = max(wh, abs(x[1] - y[1]))
                wc = max(wc, max(abs(p - q) for p, q in zip(a[2], b[2])))
    check(wt < 1 and wh < 1e-4 and wc < 0.002, 'tides: high and low waters within %.2f s, %.1g m; the curve within %.2f '
          'mm' % (wt, wh, wc * 1000))
    wt = wv = 0
    for st in streams.REGIONS[0][3]:
        for n in range(R.jdn(2026, 1, 1), R.jdn(2026, 1, 1) + 30):
            a, b = R.sday(st, n), R.sday_exact(st, n)
            if len(a[1]) != len(b[1]):
                check(False, '%s day %d: %d / %d events' % (st['name'], n, len(a[1]), len(b[1])))
            for x, y in zip(a[1], b[1]):
                wt = max(wt, abs(x[0] - y[0]) * 3600); wv = max(wv, abs(x[1] - y[1]))
    check(wt < 60 and wv < 0.002, 'streams: slacks and maxima within %.0f s, %.4f kn' % (wt, wv))


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
    shots, c = S.run([S.REGION] * len(ALLREG))
    names = [e[3] for e in c.ev]
    check(names == [ALLREG[i % len(ALLREG)][3][0]['name'] for i in range(len(ALLREG) + 1)], 'regions: %s' % names)
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
    old = open(P['TIDEUS'], encoding='utf-8').read().replace('\n3060\nSTO 93\n', '\n', 1)
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


def test_streams():
    print('6. tidal streams')
    import build_tide47 as B, synth_streams as SY, make_private_streams as MPS, c47sim, tempfile, shutil, datetime as dt
    days = [R.jdn(2026, 10, 25), R.jdn(2027, 3, 21), R.jdn(2028, 6, 30)]
    ri = len(stations.REGIONS)
    wt = wv = ws = 0
    n = 0
    for pi, st in enumerate(streams.REGIONS[0][3]):
        for dn in days:
            shots, c = S.run([S.REGION] * ri + [S.DOWN] * pi, clock=dn + 1 / 24)
            fr, ev, n25, name = c.ev[-1]
            tz, tw, cu = R.sday(st, dn)
            ok = name == st['name'] and n25 == dn and len(ev) == len(tw)
            for a, b in zip(ev, tw):
                wt = max(wt, abs(a[0] - b[0]) * 3600); wv = max(wv, abs(a[1] - b[1]))
                if b[3] > 0:                       # a slack's set is the sign of a speed of 1E-15 (not shown)
                    ws = max(ws, abs(a[2] - b[2]))
                ok = ok and a[3] == b[3]
            if not ok:
                check(False, '%s %s: %s / %s' % (st['name'], R.cal(dn), ev, tw))
            n += 1
    check(wt < 0.01 and wv < 1e-9 and ws < 1e-9, '%d NOAA stream-days: the same slacks and maxima (%.2g s, %.2g kn, '
          'the sets %.2g deg)' % (n, wt, wv, ws))
    # a rotary station: TIDE47 and its data program built with a test region (as build_tide47.py --private)
    tmp = tempfile.mkdtemp()
    try:
        rot = SY.rot_station()
        regs = ALLREG + [('TS', 'TIDETS', 'TEST: SYNTHETIC', [rot])]
        B.build(regs, [tmp], listings=False)
        B.build_data(regs, [tmp])
        progs = [os.path.join(tmp, l + '.txt') for _, l, _, _ in [('', 'TIDE47', '', '')] + regs]
        wt = wv = ws = 0
        for dn in days:
            shots, c = S.run([S.REGION] * (len(regs) - 1), clock=dn + 1 / 24, progs=progs)
            fr, ev, n25, name = c.ev[-1]
            tz, tw, cu = R.sday(rot, dn)
            ok = name == rot['name'] and len(ev) == len(tw)
            for a, b in zip(ev, tw):
                wt = max(wt, abs(a[0] - b[0]) * 3600); wv = max(wv, abs(a[1] - b[1]))
                ws = max(ws, abs((a[2] - b[2] + 180) % 360 - 180)); ok = ok and a[3] == b[3]
            check(ok, 'rotary %04d-%02d-%02d: %d events' % (R.cal(dn) + (len(ev),)))
        check(wt < 0.01 and wv < 1e-9 and ws < 1e-9, 'rotary: the same maxima and minima (%.2g s, %.2g kn, %.2g deg)'
              % (wt, wv, ws))
        S.png(os.path.join(ROOT, 'docs', 'TIDE47_rotary_test.png'), shots[-1])
        cc = c47sim.load(progs)
        cc.s = [D(11), D(22), D(33), D(44)]; cc.pix = []; cc.keys = [S.REGION] * (len(regs) - 1) + [S.END]
        cc.steps = 0; cc.clock = S.CLOCK; cc.frames = []; cc.lastx = D(55)
        cc.run('TIDE47', maxsteps=10 ** 9)
        check(not cc.mats and [int(v) for v in cc.s[:4]] == [11, 22, 33, 44], 'the end after a stream day: no matrix '
              'left, the stack back %s' % (sorted(cc.mats) or ''))
        # the fit: a year of tables, the next predicted
        d = os.path.join(tmp, 'tables')
        os.makedirs(d)
        SY.write(SY.rect_station(), SY.table(SY.rect_station(), 2026, 2027), os.path.join(d, 'rect.txt'))
        SY.write(rot, SY.table(rot, 2026, 2027), os.path.join(d, 'rot.txt'))
        old = sys.argv
        sys.argv = ['x', '--test-from', '2027-01-01', d]
        try:
            ports, rep = MPS.main()
        finally:
            sys.argv = old
        rc = dict(rep)
        a, b = rc[SY.rect_station()['name']], rc[rot['name']]
        check(a['t_rms'] < 1 and a['s_rms'] < 0.05 and a['miss'] == 0, 'rectilinear tables (slack, flood, ebb): the '
              'next year within %.1f min, %.2f kn rms' % (a['t_rms'], a['s_rms']))
        check(b['t_rms'] < 2 and b['s_rms'] < 0.05 and b['miss'] < 5, 'rotary tables (max, min, set): the next year '
              'within %.1f min, %.2f kn rms' % (b['t_rms'], b['s_rms']))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        priv = os.path.join(ROOT, 'private', 'STREAMS_COMPARE.md')
        if os.path.exists(priv) and 'TEST ' in open(priv).read():
            os.remove(priv)


def test_flow():
    print('7. FLOW47: the C47 against the twin (tide47ref.flow_*) with a synthetic atlas and Mina Salman as the reference')
    import build_tide47 as B, synth_flow as SF, tempfile, shutil, c47sim
    fl = SF.atlas()
    ref = stations.REGIONS[0][3][0]
    tmp = tempfile.mkdtemp()
    try:
        regs = list(ALLREG)
        ri, pi = B.flow_find(regs, fl)
        flow = (ri, pi, fl, regs[ri - 1][1])
        B.build(regs, [tmp], listings=False, flow=flow)
        open(os.path.join(tmp, 'TIDEFL.txt'), 'w').write('\n'.join(B.flow_data(fl)) + '\n')
        progs = [os.path.join(tmp, 'TIDE47.txt')] + [os.path.join(ROOT, 'build', r[1] + '.txt') for r in regs] + \
            [os.path.join(tmp, 'TIDEFL.txt')]
        K = S.FLOWKEYS
        keys = [K['NEXT'], K['NEXT'], K['PREV'], K['DAYF'], K['DAYB'], K['PREV'], K['NOW']]
        today = R.jdn(2026, 10, 25)
        worst = 0
        for lat, lon, wd, wk in ((28.24, 49.36, 320, 25), (27.15, 50.03, 0, 0), (26.3, 50.4, 90, 12), (26.2, 49.0, 0, 0),
                                 (29.5, 49.0, 0, 0)):
            shots, c = S.run_flow(keys, lat, lon, wd, wk, progs=progs)
            cell = R.flow_cell(fl, R.dm(lat), R.dm(lon))
            st = [f for _, f in c.fl]
            if cell is None:
                check(all(f['ok'] == 0 for f in st), '%.2f %.2f: no atlas here (land or outside), as the twin' % (lat, lon))
                continue
            n, m = R.flow_pick(ref, today, 13.0)
            want = [(n, m)]
            for k in keys:
                if k == K['NEXT']:
                    n, m = R.flow_step(ref, n, m, 1)
                elif k == K['PREV']:
                    n, m = R.flow_step(ref, n, m, -1)
                elif k in (K['DAYF'], K['DAYB']):
                    t = R.flow_cycle(ref, n, m)[0]
                    n, m = R.flow_pick(ref, n + (1 if k == K['DAYF'] else -1), t)
                else:
                    n, m = R.flow_pick(ref, today, 13.0)
                want.append((n, m))
            ok = len(st) == len(want)
            for f, (n, m) in zip(st, want):
                t, h, rng, fac = R.flow_cycle(ref, n, m)
                ok = ok and f['ok'] == 1 and f['n'] == n and f['m'] == m
                worst = max(worst, abs(f['t'] - t) * 3600, abs(f['f'] - fac) * 1e4)
            for a, b in zip(st[0]['FU'] + st[0]['FV'], cell[0] + cell[1]):
                worst = max(worst, abs(a - b) * 1e4)
            check(ok, '%.2f %.2f: the same High Waters through the keys %s' % (lat, lon, [(f['n'] - today, f['m']) for f in st]))
        check(worst < 1e-3, 'the hours, the factors and the atlas values the same (worst %.2g: s, 1E-4 of the factor, '
              '1E-4 kn)' % worst)
        S.png(os.path.join(ROOT, 'docs', 'FLOW47_synthetic.png'), S.run_flow([], 28.24, 49.36, 0, 0, progs=progs)[0][0])
        cc = c47sim.load(progs)
        from decimal import Decimal as Dd
        cc.s = [Dd(11), Dd(22), Dd(33), Dd(44)]; cc.pix = []; cc.keys = [S.END]; cc.steps = 0; cc.clock = S.CLOCK
        cc.frames = []; cc.lastx = Dd(55)
        for k, v in (('LAT', 27.3), ('LON', 50.1), ('WDIR', 0), ('WKN', 0)):
            cc.reg[k] = Dd(v)
        cc.run('FLOW47', maxsteps=10 ** 9)
        left = [k for k in cc.mats]
        check(not left and [int(v) for v in cc.s[:4]] == [11, 22, 33, 44], 'the end of FLOW47: no matrix left, the stack '
              'back %s' % (left or ''))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    test_astronomy()
    test_utide()
    test_fast()
    test_c47()
    test_keys()
    test_probe()
    test_streams()
    test_flow()
    print('ALL OK' if not FAIL else '%d FAILED' % len(FAIL))
    sys.exit(1 if FAIL else 0)
