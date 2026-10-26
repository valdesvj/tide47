#!/usr/bin/env python3
"""test_app.py - the PC app (app/tide47_gtk.py) station by station, and its parity with the calculator.

For every station of the app's region (your Aramco stations when python/stations_private.py is there; else the
Middle East ports standing in):
 1. the labels: the station chosen (as the Station list does) -> the Tide, ARTF and Map tabs all draw its name (the
    Tide tab's title, ARTF's "Tide: name (0.0 nm)", the Map's station label, or its note that the station is outside
    the atlas area), and the position goes to it, so the
    station nearest the position is that station; a position typed near it gives the same station back;
 2. the parity: ARTF47 on the calculator (a build like --artf, in c47sim) at the station's position against the app:
    the same nearest station (NST) and distance, the same High Water of the cycle and factor, the same high and low
    waters of the station's day, the same 13 spring streams of the atlas there.
The app's clock is set to the simulator's (2026-10-25 13:00) for the parity.
  python3 tests/test_app.py"""
import os, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'app'), os.path.join(ROOT, 'python'), os.path.join(ROOT, 'tools'),
                os.path.join(ROOT, 'tests')]
import tide47_gtk as A          # noqa: E402
import tide47ref as R           # noqa: E402
import tide47sim as S           # noqa: E402

FAIL = []


def check(ok, what):
    print('  %s  %s' % ('ok  ' if ok else 'FAIL', what), flush=True)
    if not ok:
        FAIL.append(what)


class FakeCairo:
    """a cairo context that draws nothing (the labels are recorded by tide47_gtk.text)"""
    class _E:
        x_advance = 10.0

    def text_extents(self, s):
        return self._E()

    def __getattr__(self, name):
        return lambda *a, **k: None


def drawn(view, st, w=1000, h=680):
    A.RECORD = []
    view(FakeCairo(), w, h, st)
    out, A.RECORD = A.RECORD, None
    return out


def dm_exact(v):
    """degrees -> DD.MMmmmm for the calculator's INPUT (exact enough: 1E-6 minute)"""
    a = abs(v); d = int(a)
    return (1 if v >= 0 else -1) * (d + (a - d) * 0.6)


def main():
    data = A.Data()
    n0, h0 = R.jdn(2026, 10, 25), 13.0
    data.now = lambda st: (n0, h0)
    st = A.State(data)
    ports = data.ports
    print('stations: %s (%d)%s' % (data.region[2], len(ports), '; ' + '; '.join(data.notes) if data.notes else ''))
    print('1. the labels: each station chosen shows in every tab')
    for p in ports:
        st.set_station(p)
        tide, artf, mp = drawn(A.view_tide, st), drawn(A.view_artf, st), drawn(A.view_map, st)
        near, dnm = st.nearest()
        same_pos = [q['name'] for q in ports if (q['lat'], q['lon']) == (p['lat'], p['lon'])]
        on_map = p['name'] in mp or any(t.startswith('%s is outside the atlas area' % p['name']) for t in mp)
        ok = (st.station is p and (near is p or near['name'] in same_pos) and tide[0] == p['name']
              and any(t.startswith('Tide: %s ' % near['name']) for t in artf) and on_map)
        st.set_position(p['lat'] + 0.01, p['lon'] - 0.01)          # a position typed next to it
        ok2 = st.station is st.nearest()[0]
        check(ok and ok2, '%-24s Tide "%s", ARTF "%s", Map %s' % (
            p['name'], tide[0], next((t for t in artf if t.startswith('Tide: ')), '?'),
            'labelled' if p['name'] in mp else 'says outside' if on_map else 'NOT labelled'))
    print('2. the parity: ARTF47 on the calculator against the app, at each station')
    import build_tide47 as B
    reg = data.region
    ri, pi = 1, ports.index(data.ref) + 1
    tmp = tempfile.mkdtemp()
    try:
        B.build([reg], [tmp], listings=False, flow=(1, pi, data.atlas, reg[1]), art=dict(ports=ports))
        B.build_data([reg], [tmp])
        open(os.path.join(tmp, 'TIDEFL.txt'), 'w').write('\n'.join(B.flow_data(data.atlas)) + '\n')
        progs = [os.path.join(tmp, n + '.txt') for n in ('TIDE47', reg[1], 'TIDEFL')]
        worst = 0
        for k, p in enumerate(ports, 1):
            shots, c = S.run_flow([], dm_exact(p['lat']), dm_exact(p['lon']), progs=progs, label='ARTF47')
            f = c.fl[0][1]
            st.set_station(p)
            st.to_now()
            t, hgt, rng, fac, rows, off, nowuv = st.cycle()
            ev = R.day(p, st.n)[1]
            cell = R.flow_cell(data.atlas, st.lat, st.lon)
            ok = (int(f['nst']) == ports.index(st.nearest()[0]) + 1 and f['n'] == st.n and f['m'] == st.m
                  and len(f['ev']) == len(ev) and bool(f['ok']) == (cell is not None))
            worst = max([worst, f['ndst'] * 1e3, abs(f['t'] - t) * 3600, abs(f['f'] - fac) * 1e4]
                        + [abs(a[0] - b[0]) * 3600 for a, b in zip(f['ev'], ev)]
                        + ([abs(a - b) * 1e4 for a, b in zip(f['FU'] + f['FV'], cell[0] + cell[1])] if cell else []))
            check(ok, '%-24s the calculator: station %d, HW %s, %d tides, atlas %s' % (
                p['name'], int(f['nst']), A.hhmm(f['t']), len(f['ev']), 'there' if f['ok'] else 'not there'))
        check(worst < 1e-3, 'the distances (1E-3 nm), the hours (s), the factors and streams (1E-4) the same: worst '
              '%.2g' % worst)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('ALL OK' if not FAIL else '%d FAILED' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
