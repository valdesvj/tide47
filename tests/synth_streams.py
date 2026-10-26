"""synth_streams.py - current tables made from known constants, for the tests of tools/make_private_streams.py.

  rect_station()   a real NOAA station (Pollock Rip Channel, public domain), its clock moved to UTC+3 (no DST)
  rot_station()    a SYNTHETIC rotary station (invented constants of a Gulf-like size: M2 about 0.9 kn, rotating;
                   not a real place: only to test the method)
  table(st, y0, y1, form)  the rows a table would print, rounded as tables are (the minute, 0.1 kn, 1 deg):
                   form 'events' (SLACK / FLOOD / EBB, or MAX / MIN with speed and set) or 'hourly' (speed and set)"""
import copy, datetime as dt, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'python'))
import tide47ref as R
import streams


def rect_station():
    st = copy.deepcopy(streams.REGIONS[0][3][0])
    st.update(tz=3, dst='', name='TEST RECT Pollock Rip')
    return st


def rot_station():
    hc = {'M2': (0.71, 95.0), 'S2': (0.27, 140.0), 'N2': (0.15, 70.0), 'K2': (0.075, 135.0), 'K1': (0.24, 20.0),
          'O1': (0.16, 300.0), 'P1': (0.08, 15.0), 'Q1': (0.03, 280.0), 'M4': (0.05, 40.0), 'MS4': (0.03, 90.0),
          'NU2': (0.03, 75.0), 'L2': (0.02, 110.0), 'SA': (0.03, 200.0)}
    hv = {'M2': (0.58, 225.0), 'S2': (0.21, 270.0), 'N2': (0.12, 200.0), 'K2': (0.06, 265.0), 'K1': (0.19, 140.0),
          'O1': (0.13, 60.0), 'P1': (0.06, 135.0), 'Q1': (0.025, 40.0), 'M4': (0.04, 170.0), 'MS4': (0.025, 220.0),
          'NU2': (0.025, 205.0), 'L2': (0.015, 240.0), 'SSA': (0.02, 30.0)}
    return dict(name='TEST ROT (synthetic)', lat=27.0, lon=50.0, tz=3, dst='', kind='rot', flood=0, ebb=0, z0=0.05,
                v0=-0.08, datum='ROTARY, KNOTS', src='synthetic', hc=hc, hv=hv)


def table(st, y0, y1, form='events'):
    rows = []
    n0, n1 = R.jdn(y0, 1, 1), R.jdn(y1 + 1, 1, 1)
    for n in range(n0, n1):
        y, m, d = R.cal(n)
        if form == 'hourly':
            for h in range(24):
                v, s = R.stream_now(st, n, h)
                sp = round(abs(v), 1)
                rows.append(('AT', dt.datetime(y, m, d, h), sp, float(round(s) % 360)))
            continue
        for t, v, s, k in R.sday(st, n)[1]:
            mi = int(round(t * 60))
            if mi >= 1440:
                continue
            when = dt.datetime(y, m, d) + dt.timedelta(minutes=mi)
            if st['kind'] == 'rect':
                if k < 0:
                    rows.append(('SLACK', when, None, None))
                else:
                    rows.append(('FLOOD' if v > 0 else 'EBB', when, round(abs(v), 1), None))
            else:
                rows.append(('MAX' if k > 0 else 'MIN', when, round(abs(v), 1), float(round(s) % 360)))
    return rows


def write(st, rows, fn, header=True):
    with open(fn, 'w', encoding='utf-8') as fh:
        fh.write('# name: %s\n# lat: %s\n# lon: %s\n# tz: %s\n# source: test table\n' % (
            st['name'], st['lat'], st['lon'], st['tz']))
        if st['kind'] == 'rect' and header:
            fh.write('# flood: %d\n# ebb: %d\n' % (st['flood'], st['ebb']))
        if st['kind'] == 'rot':
            fh.write('# kind: rot\n')
        for kind, t, sp, d in rows:
            ts = t.strftime('%Y-%m-%d %H:%M')
            if kind == 'AT':
                fh.write('%s %.1f %.0f\n' % (ts, sp, d))
            elif kind == 'SLACK':
                fh.write('SLACK %s\n' % ts)
            elif kind in ('FLOOD', 'EBB'):
                fh.write('%s %s %.1f\n' % (kind, ts, sp))
            else:
                fh.write('%s %s %.1f %.0f\n' % (kind, ts, sp, d))
