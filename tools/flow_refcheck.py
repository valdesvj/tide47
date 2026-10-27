#!/usr/bin/env python3
"""flow_refcheck.py - which station's High Water do the atlas's charts use? (they only say "High Water")

Run on your computer (it needs your private data: python/stations_private.py, python/flow_private.py). It prints:
 1. each candidate reference's High Water against the assumed one (Ras Tanura): the mean difference over 30 days and
    its spread (Mina Salman, Bahrain, public, stands in for Dammam: no Aramco station there);
 2. a physical check from the charts themselves: in the Dammam - Bahrain channel the stream runs south (into the
    Gulf of Bahrain) from HW-3 to HW+3 of the reference, slack at about HW+2.9; a basin's flood stops at the basin's
    own High Water, so the reference must have its High Water about 2.9 h BEFORE the Gulf of Bahrain's (Mina Salman):
    each candidate's |its lead on Mina Salman - 2.9 h| (small = consistent);
 3. how much the predicted streams at the fields change if the reference were each candidate (kn rms);
 4. with observations (private/obs/currents.txt, one a line: YYYY-MM-DD HH:MM LAT LON SET KN, local time UTC+3,
    position in degrees, e.g. from the DP log): each candidate's rms error against them, and the best extra time
    offset: the real test.
  python3 tools/flow_refcheck.py [--days 30] [--from YYYY-MM-DD]"""
import datetime as dt, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'python'), os.path.join(ROOT, 'tests')]
import tide47ref as R

FIELDS = {'Safaniya': (28.10, 48.85), 'Zuluf': (28.42, 49.25), 'Marjan': (28.40, 49.60), 'Hasbah': (28.10, 49.85),
          'Karan': (27.72, 49.85), 'Arabiyah': (27.78, 50.13), 'Manifa': (27.68, 49.10), 'Berri': (27.20, 49.70),
          'Abu Safah': (26.98, 50.45), 'Juaymah SPM': (26.95, 50.10)}
CHANNEL = [(26.167, 50.25), (26.167, 50.417), (26.333, 50.25), (26.333, 50.417)]   # Dammam - Bahrain


def load():
    import stations
    notes = []
    try:
        import stations_private
        ports = [p for r in stations_private.REGIONS for p in r[3] if 47 < p['lon'] < 53]   # the Gulf stations
    except ImportError:
        ports = []
        notes.append('no python/stations_private.py: only public stations')
    salman = stations.REGIONS[0][3][0]
    cands = ports + [dict(salman, name='Mina Salman (for Dammam)')]
    try:
        import flow_private
        atlas = flow_private.FLOW
    except ImportError:
        import synth_flow
        atlas = synth_flow.atlas()
        notes.append('no python/flow_private.py: a SYNTHETIC atlas (the checks mean nothing)')
    key = atlas.get('ref', 'Ras Tanura').lower()
    base = next((p for p in cands if key in p['name'].lower()), None)
    if base is None:
        base = cands[-1]
        notes.append('the reference %s not found: %s used' % (atlas.get('ref'), base['name']))
    return cands, base, atlas, salman, notes


def hws(st, n0, days):
    """the High Waters of st over the days: [(JDN + hour / 24, height)] (local time)"""
    out = []
    for n in range(n0, n0 + days):
        out += [(n + t / 24, h) for t, h, k in R.day(st, n)[1] if k > 0]
    return out


def lead(a, b, n0, days):
    """b's High Water minus a's (hours): each of a's matched to b's nearest within 6.2 h -> mean, spread"""
    A, B = hws(a, n0, days), hws(b, n0, days)
    d = []
    for t, _ in A:
        x = min(B, key=lambda e: abs(e[0] - t))
        if abs(x[0] - t) * 24 <= 6.2:
            d.append((x[0] - t) * 24)
    if not d:
        return float('nan'), float('nan')
    m = sum(d) / len(d)
    return m, math.sqrt(sum((x - m) ** 2 for x in d) / len(d))


def channel_slack(atlas):
    """the semidiurnal fit of the north component in the channel: the slack turning to north (hours from HW)"""
    import numpy as np
    k = 60 / atlas['step_min']
    V = np.zeros(13)
    for la, lo in CHANNEL:
        i, j = round((la - atlas['lat0']) * k), round((lo - atlas['lon0']) * k)
        c = atlas['cells'][i * atlas['nlon'] + j]
        if c:
            V += np.array([(v - 50) * atlas['q'] for _, v in c])
    t = np.arange(-6, 7); w = 2 * math.pi / 12.42
    a, b, c = np.linalg.lstsq(np.stack([np.ones(13), np.cos(w * t), np.sin(w * t)], 1), V, rcond=None)[0]
    f = lambda x: a + b * math.cos(w * x) + c * math.sin(w * x)
    for s in range(1200):
        x0 = -6 + s * 0.01
        if f(x0) < 0 <= f(x0 + 0.01):
            return x0
    return float('nan')


def shift_rms(atlas, dh):
    """the streams' change at the fields (kn rms) when the reference's High Water is dh hours off"""
    tot, n = 0.0, 0
    for la, lo in FIELDS.values():
        c = R.flow_cell(atlas, la, lo)
        if not c:
            continue
        rows = list(zip(*c))
        for k in range(13):
            o = k - 6 + dh
            if -6 <= o <= 6:
                u, v = R.flow_now(rows, o)
                tot += (u - rows[k][0]) ** 2 + (v - rows[k][1]) ** 2; n += 1
    return math.sqrt(tot / n) if n else float('nan')


def obs_score(cands, atlas, path):
    """each candidate as the reference: the rms vector error against the observations, and the best extra offset"""
    obs = []
    for ln in open(path):
        p = ln.split()
        if len(p) >= 6 and not ln.startswith('#'):
            t = dt.datetime.strptime(p[0] + ' ' + p[1], '%Y-%m-%d %H:%M')
            obs.append((R.jdn(t.year, t.month, t.day), t.hour + t.minute / 60, float(p[2]), float(p[3]),
                        float(p[5]) * math.sin(math.radians(float(p[4]))), float(p[5]) * math.cos(math.radians(float(p[4])))))
    out = []
    for X in cands:
        best = None
        for off10 in range(-30, 31, 5):
            off = off10 / 10
            err, n = 0.0, 0
            for nday, h, la, lo, u, v in obs:
                cell = R.flow_cell(atlas, la, lo)
                if not cell:
                    continue
                nn, m = R.flow_pick(X, nday, h - off)
                t, _, _, f = R.flow_cycle(X, nn, m)
                o = (nday - nn) * 24 + h - off - t
                if abs(o) > 6:
                    continue
                pu, pv = R.flow_now(R.flow_rows(cell, f), o)
                err += (pu - u) ** 2 + (pv - v) ** 2; n += 1
            if n and (best is None or err / n < best[0]):
                best = (err / n, off, n)
        if best:
            out.append((math.sqrt(best[0]), best[1], best[2], X['name']))
    return sorted(out)


def main():
    days = int(sys.argv[sys.argv.index('--days') + 1]) if '--days' in sys.argv else 30
    if '--from' in sys.argv:
        y, m, d = map(int, sys.argv[sys.argv.index('--from') + 1].split('-'))
        n0 = R.jdn(y, m, d)
    else:
        t = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=3)
        n0 = R.jdn(t.year, t.month, t.day)
    cands, base, atlas, salman, notes = load()
    for x in notes:
        print('NOTE: ' + x)
    slack = channel_slack(atlas)
    print('The charts: in the Dammam - Bahrain channel the stream turns north (the Gulf of Bahrain\'s flood ends) at '
          'HW%+.1f of the reference.' % slack)
    print('So the reference\'s High Water should come about %.1f h before Mina Salman\'s.\n' % slack)
    print('%-30s %10s %8s %12s %12s' % ('candidate reference', 'HW - ' + base['name'][:10], 'spread',
                                        'lead on M.S.', 'misfit'))
    rows = []
    for X in cands:
        m, sd = lead(base, X, n0, days)
        ld, _ = lead(X, salman, n0, days)
        rows.append((abs(ld - slack), X['name'], m, sd, ld))
    for mis, name, m, sd, ld in sorted(rows):
        print('%-30s %+9.2f h %6.2f h %+10.2f h %10.2f h%s' % (name, m, sd, ld, mis,
                                                            '   <- assumed' if name == base['name'] else ''))
    print('\nThe streams at the fields change by (kn rms) when the reference is off by:')
    print('   ' + '   '.join('%+.1f h: %.2f' % (d, shift_rms(atlas, d)) for d in (0.5, 1, 2, 3)))
    obs = os.path.join(ROOT, 'private', 'obs', 'currents.txt')
    if os.path.exists(obs):
        print('\nAgainst your observations (%s):' % obs)
        for e, off, n, name in obs_score(cands, atlas, obs)[:8]:
            print('  %-30s %.2f kn rms (%d observations), best extra offset %+.1f h' % (name, e, n, off))
    else:
        print('\nNo observations yet: put the DP log\'s currents in private/obs/currents.txt (YYYY-MM-DD HH:MM LAT LON '
              'SET KN) for the real test.')


if __name__ == '__main__':
    main()
