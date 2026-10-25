#!/usr/bin/env python3
"""make_private.py - a private region for Tide 47 (ARAMCO): the harmonic constants of stations whose data may not be
published (Saudi Aramco's tide tables are Aramco's copyright), worked out on your computer and kept out of git.

Input: one text file a station in private/aramco/ (any name ending .txt), typed from the tables:
    # name: Ras Tanura                    the name on the C47 (at most 22 characters)
    # lat: 26.64                          degrees, + north (shown; not needed for the fit)
    # lon: 50.16                          degrees, + east
    # tz: 3                               the tables' time zone (hours, + east of Greenwich)
    # datum: CD                           the tables' datum (Aramco: chart datum)
    # source: Aramco 2026                 shown on the C47 (the tables you typed)
    then the rows, in the tables' local time, metres above the datum:
    HW 2026-01-01 04:12 2.05              the high and low waters (HW / LW), or
    2026-01-01 04:00 1.97                 hourly heights (a time and a height), or
    CONST M2 0.5821 123.40                harmonic constants if the tables give them (H m, g deg Greenwich),
    Z0 1.234                              with Z0, the mean sea level above the datum
A file with heights is analysed by least squares with Tide 47's own astronomy and nodal corrections (so the
constants are in its convention): the constituents the record's length separates (Rayleigh 1) among Tide 47's 45;
high and low waters give two equations each (the height, and h' = 0 at their time).

Output (never in git): python/stations_private.py (the region ARAMCO, data program TIDEAR), then
    python3 tools/build_tide47.py --private      -> private/build/TIDE47.txt and TIDEAR.txt (load them instead of
                                                    the public TIDE47; TIDEME TIDEUS TIDELA as before)
    python3 tools/compare_tables.py              -> private/COMPARE.md: Tide 47 against the tables
  python3 tools/make_private.py [--test-from YYYY-MM-DD] [--rayleigh 0.9] [folder]
  --test-from: the rows from that date are left out of the fit (compare_tables.py compares on them: a fair test)."""
import datetime as dt, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'python'))
import tide47ref as R

# the order to keep the constituents in (NOAA's importance) when the record is short
PRIORITY = ['M2', 'S2', 'N2', 'K1', 'O1', 'K2', 'P1', 'Q1', 'NU2', 'MU2', '2N2', 'L2', 'T2', 'J1', 'M4', 'MS4', 'MN4',
            'LAM2', 'OO1', 'M3', 'MK3', '2MK3', 'M6', 'S4', 'RHO1', '2Q1', 'EPS2', 'MKS2', 'SA', 'SSA', 'MF', 'MM',
            'MSF', 'M1', '2SM2', 'N4', 'S1', 'R2', 'M8', 'S6',
            'STA', 'TAU1', 'PSI1', 'SO1', 'MSSA2', 'MSN2', 'PHI1', 'MSM', 'SIG1', 'MA2', 'MB2', 'MTM', 'MSQM', 'S3',
            'O1SA', 'O1SB', 'Q1SA', 'SA4', 'MFSA', 'MTSA']


def read_station(fn):
    st = dict(name=os.path.basename(fn)[:-4], lat=0.0, lon=0.0, tz=3.0, datum='CD', source='Aramco tables')
    ev, hourly, hc, z0 = [], [], {}, None
    for ln in open(fn, encoding='utf-8'):
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith('#'):
            if ':' in ln:
                k, v = ln[1:].split(':', 1)
                k, v = k.strip().lower(), v.strip()
                st[k] = float(v) if k in ('lat', 'lon', 'tz') else v
            continue
        p = ln.split()
        if p[0] in ('HW', 'LW'):
            ev.append((p[0], dt.datetime.strptime(p[1] + ' ' + p[2], '%Y-%m-%d %H:%M'), float(p[3])))
        elif p[0] == 'CONST':
            hc[p[1].upper()] = (float(p[2]), float(p[3]))
        elif p[0] == 'Z0':
            z0 = float(p[1])
        else:
            hourly.append((dt.datetime.strptime(p[0] + ' ' + p[1], '%Y-%m-%d %H:%M'), float(p[2])))
    return st, ev, hourly, hc, z0


def jd_local(t, tz):
    """A local time -> the JD (UT)."""
    return R.jd(t.year, t.month, t.day, t.hour + t.minute / 60 - tz)


RAYLEIGH = 0.9          # the separation kept: 0.9 / T (1 / T is the classical rule; the tables are a clean prediction,
                        # so a year of 8 760 hours, 0.1 % short of SA's period, still gives SA and SSA)


def rayleigh(names, days):
    """The constituents (in PRIORITY order) that a record of `days` separates: each at least RAYLEIGH / T from the
    others kept."""
    w = dict(zip([c[0] for c in R.CONS], R.speeds()))
    need = RAYLEIGH * 360.0 / (days * 24)                    # deg / hour: RAYLEIGH cycles over the record
    keep = []
    for n in PRIORITY:
        if n in names and all(abs(w[n] - w[k]) >= need for k in keep):
            keep.append(n)
    return keep


def analyse(st, heights, extremes=()):
    """Least squares with Tide 47's own astronomy (tide47ref: V + u and f each day, the speeds within it), unknowns
    Z0 and H cos g, H sin g of each constituent the record separates:
      a height h at t:          Z0 + sum f (Hc cos(V + u + w t) + Hs sin(V + u + w t)) = h
      a high / low water at t:  the same, and h'(t) = sum f w (-Hc sin + Hs cos) = 0 (weight 1 hour)
    heights / extremes: [(JD UT, metres)]. -> ({name: (H, g)}, Z0, the constituents, days)."""
    import numpy as np
    allt = [j for j, _ in heights] + [j for j, _ in extremes]
    days = max(allt) - min(allt)
    use = rayleigh([c[0] for c in R.CONS], days)
    idx = [[c[0] for c in R.CONS].index(n) for n in use]
    W = np.array(R.speeds())[idx]
    cache = {}

    def args(j):
        d = math.floor(j - 0.5) + 0.5                         # the UT day's start (0h)
        if d not in cache:
            vf = R.vector(d)
            cache[d] = (np.radians([vf[i][0] for i in idx]), np.array([vf[i][1] for i in idx]))
        vu, f = cache[d]
        return vu + np.radians(W * (j - d) * 24), f
    rows, rhs = [], []
    for j, h in list(heights) + list(extremes):
        a, f = args(j)
        rows.append(np.concatenate(([1.0], f * np.cos(a), f * np.sin(a)))); rhs.append(h)
    for j, h in extremes:
        a, f = args(j)
        r = f * np.radians(W)
        rows.append(np.concatenate(([0.0], -r * np.sin(a), r * np.cos(a)))); rhs.append(0.0)
    x, *_ = np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)
    k = len(use)
    hc = {n: (round(float(math.hypot(x[1 + i], x[1 + k + i])), 4),
              round(math.degrees(math.atan2(x[1 + k + i], x[1 + i])) % 360, 2)) for i, n in enumerate(use)}
    return hc, round(float(x[0]), 3), use, days


def main():
    args = [a for a in sys.argv[1:]]
    split = None
    if '--rayleigh' in args:
        global RAYLEIGH
        i = args.index('--rayleigh'); RAYLEIGH = float(args[i + 1]); del args[i:i + 2]
    if '--test-from' in args:
        i = args.index('--test-from'); split = dt.datetime.strptime(args[i + 1], '%Y-%m-%d'); del args[i:i + 2]
    folder = args[0] if args else os.path.join(ROOT, 'private', 'aramco')
    files = sorted(f for f in os.listdir(folder) if f.endswith('.txt'))
    if not files:
        raise SystemExit('no station files in %s (see the header of this tool)' % folder)
    ports = []
    for f in files:
        st, ev, hourly, hc, z0 = read_station(os.path.join(folder, f))
        if hc:
            how = 'constants from the tables (%d)' % len(hc)
            hc = {n: v for n, v in hc.items() if n in [c[0] for c in R.CONS]}
            z0 = z0 or 0.0
        else:
            keep = lambda t: split is None or t < split
            hts = [(jd_local(t, st['tz']), v) for t, v in hourly if keep(t)]
            ext = [(jd_local(t, st['tz']), v) for _, t, v in ev if keep(t)] if not hourly else []
            fit = hts or ext
            if not fit:
                print('%-22s no rows yet: left out' % st['name'])
                continue
            if len(fit) < 60:
                raise SystemExit('%s: %d heights to fit, too few (at least a month of tables)' % (f, len(fit)))
            hc, z0, use, days = analyse(st, hts, ext)
            how = '%d %s over %.0f days -> %d constituents' % (len(fit), 'hourly heights' if hourly else
                                                                'high / low waters', days, len(use))
        ports.append(dict(name=st['name'][:22], lat=st['lat'], lon=st['lon'], tz=st['tz'], dst='', datum=st['datum'],
                          z0=z0, src=st.get('source', 'Aramco tables')[:24], hc=hc))
        print('%-22s %s; Z0 %.3f m; M2 %.3f m %.1f deg, K1 %.3f m %.1f deg' % (
            st['name'], how, z0, hc.get('M2', (0, 0))[0], hc.get('M2', (0, 0))[1], hc.get('K1', (0, 0))[0],
            hc.get('K1', (0, 0))[1]))
    if not ports:
        raise SystemExit('no station with rows yet in %s' % folder)
    out = ['"""stations_private.py - the private region ARAMCO (written by tools/make_private.py from private/aramco/;',
           'never in git: the constants come from Saudi Aramco\'s tide tables, Aramco\'s copyright)."""', '',
           'SPLIT = %r' % (split.strftime('%Y-%m-%d') if split else None),
           'FOLDER = %r' % os.path.abspath(folder), '',
           'REGIONS = [', "    ('AR', 'TIDEAR', 'ARAMCO: PRIVATE', ["]
    for p in ports:
        out.append('        %r,' % p)
    out += ['    ]),', ']']
    open(os.path.join(ROOT, 'python', 'stations_private.py'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('python/stations_private.py: %d stations; next: python3 tools/build_tide47.py --private, '
          'python3 tools/compare_tables.py' % len(ports))


if __name__ == '__main__':
    main()
