#!/usr/bin/env python3
"""make_private_streams.py - a private tidal-stream region for Tide 47 (GULF STREAMS): the harmonic constants of
current stations whose tables may not be published (GEOSA's Saudi Tidal Currents Tables, for one), worked out on your
computer and kept out of git, as tools/make_private.py does for Aramco's tide tables.

Input: one text file a station in private/streams/ (any name ending .txt), from the tables:
    # name: Safaniya field              the name on the C47 (at most 22 characters)
    # lat: 28.0                          degrees, + north (shown; not needed for the fit)
    # lon: 48.8                          degrees, + east
    # tz: 3                              the tables' time zone (hours, + east of Greenwich)
    # source: GEOSA 2027                 shown on the C47
    # kind: rect                         rect (flood / ebb along an axis) or rot (rotary); default: rect when the
                                         rows are SLACK / FLOOD / EBB or a flood direction is given, else rot
    # flood: 135                         the flood and ebb sets (deg true, where the stream goes): a rectilinear
    # ebb: 315                           station's; left out, they come from the rows' sets
    then the rows, in the tables' local time, knots, sets in degrees true:
    SLACK 2027-01-01 03:40              slack water (a rectilinear station: the speed along the axis is 0 then)
    FLOOD 2027-01-01 06:55 1.8          the maximum flood (its speed; the set: the flood direction)
    EBB 2027-01-01 13:10 1.6            the maximum ebb
    MAX 2027-01-01 06:55 1.8 132        a maximum with its speed and set (either kind)
    MIN 2027-01-01 03:40 0.2 41         a minimum (rotary) with its speed and set
    2027-01-01 04:00 1.2 135            a speed and set at a time (hourly tables)
    CONST M2 0.95 120.0 0.62 300.0      constants if the tables print them: rect "CONST M2 H g", rot "CONST M2 Hu gu
    Z0 0.05 [V0 -0.02]                  Hv gv" (east u, north v; knots, deg Greenwich), the means
The least squares uses Tide 47's own astronomy (tide47ref: V + u and f each day): unknowns the means and H cos g,
H sin g of each constituent the record separates (Rayleigh, as make_private.py). A rectilinear station: one series s
(knots along the flood axis, + flood, - ebb): a slack gives s = 0; a flood / ebb gives s = +- the speed and s' = 0
(weight 1 hour); a timed speed gives +- the speed. A rotary station: u = speed sin(set), v = speed cos(set), and at
a MAX / MIN the speed's turning point u u' + v v' = 0 (linear with the observed u, v; weight 1 hour).

Output (never in git): python/streams_private.py (the region GULF STREAMS, data program TIDEGS), then
    python3 tools/build_tide47.py --private     -> private/build/TIDE47.txt and TIDEGS.txt (with TIDEAR if any)
  python3 tools/make_private_streams.py [--test-from YYYY-MM-DD] [--rayleigh 0.9] [folder]
  --test-from: the rows from that date are left out of the fit and compared with Tide 47's predictions:
  private/STREAMS_COMPARE.md (slack and max times in minutes, speeds in knots)."""
import datetime as dt, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'python'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import tide47ref as R
import make_private as MP

T = '%Y-%m-%d %H:%M'


def read_station(fn):
    st = dict(name=os.path.basename(fn)[:-4], lat=0.0, lon=0.0, tz=3.0, source='GEOSA tables')
    rows, hc, means = [], {}, {}
    for ln in open(fn, encoding='utf-8'):
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith('#'):
            if ':' in ln:
                k, v = ln[1:].split(':', 1)
                k, v = k.strip().lower(), v.strip()
                st[k] = float(v) if k in ('lat', 'lon', 'tz', 'flood', 'ebb') else v
            continue
        p = ln.split()
        w = p[0].upper()
        if w in ('SLACK', 'FLOOD', 'EBB', 'MAX', 'MIN'):
            t = dt.datetime.strptime(p[1] + ' ' + p[2], T)
            sp = float(p[3]) if len(p) > 3 else None
            d = float(p[4]) if len(p) > 4 else None
            rows.append((w, t, sp, d))
        elif w == 'CONST':
            hc[p[1].upper()] = tuple(float(x) for x in p[2:])
        elif w == 'Z0':
            means['z0'] = float(p[1])
            if len(p) > 2:
                means['v0'] = float(p[2])
        elif w == 'V0':
            means['v0'] = float(p[1])
        else:
            rows.append(('AT', dt.datetime.strptime(p[0] + ' ' + p[1], T), float(p[2]), float(p[3])))
    kind = st.get('kind')
    if kind not in ('rect', 'rot'):
        kind = 'rect' if 'flood' in st or any(r[0] in ('SLACK', 'FLOOD', 'EBB') for r in rows) else 'rot'
    st['kind'] = kind
    return st, rows, hc, means


def angdiff(a, b):
    return abs((a - b + 180) % 360 - 180)


def axis(st, rows):
    """The flood and ebb sets of a rectilinear station: the header's, else from the rows: the flood the mean set of
    the FLOOD rows (or of the strongest half of the sets), the ebb the mean of the others (each as a unit vector)."""
    if 'flood' in st and 'ebb' in st:
        return st['flood'] % 360, st['ebb'] % 360
    sets = [(r[2], r[3]) for r in rows if r[3] is not None and r[2] and r[0] != 'SLACK']
    if not sets:
        raise SystemExit('%s: no flood / ebb directions (give # flood: and # ebb:)' % st['name'])

    def mean(ds):
        x = sum(math.sin(math.radians(d)) for d in ds); y = sum(math.cos(math.radians(d)) for d in ds)
        return math.degrees(math.atan2(x, y)) % 360
    # the principal axis of the set vectors (doubled angles), then the two halves
    x = sum(s * s * math.sin(math.radians(2 * d)) for s, d in sets)
    y = sum(s * s * math.cos(math.radians(2 * d)) for s, d in sets)
    ax = math.degrees(math.atan2(x, y)) / 2 % 360
    a = [d for _, d in sets if angdiff(d, ax) <= 90]
    b = [d for _, d in sets if angdiff(d, ax) > 90]
    fl = st.get('flood', mean(a) if a else ax)
    eb = st.get('ebb', mean(b) if b else (fl + 180) % 360)
    if 'flood' not in st and 'ebb' in st:
        fl = mean(a) if angdiff(mean(a), eb) > 90 else mean(b)
    return round(fl) % 360, round(eb) % 360


def design(use, W):
    """args(j) -> (the phases V + u + w t in radians, f), cached a UT day (as make_private.analyse)."""
    import numpy as np
    idx = [[c[0] for c in R.CONS].index(n) for n in use]
    W = np.array(R.speeds())[idx]
    cache = {}

    def args(j):
        d = math.floor(j - 0.5) + 0.5
        if d not in cache:
            vf = R.vector(d)
            cache[d] = (np.radians([vf[i][0] for i in idx]), np.array([vf[i][1] for i in idx]))
        vu, f = cache[d]
        return vu + np.radians(W * (j - d) * 24), f
    return args, np.radians(W)


def analyse(st, rows, split=None):
    """The least squares of the rows before `split` (a datetime or None). -> the port dict (without name etc.)."""
    import numpy as np
    jd = lambda t: MP.jd_local(t, st['tz'])
    fit = [r for r in rows if split is None or r[1] < split]
    if len(fit) < 60:
        raise SystemExit('%s: %d rows to fit, too few (at least a month of tables)' % (st['name'], len(fit)))
    tt = [jd(r[1]) for r in fit]
    days = max(tt) - min(tt)
    use = MP.rayleigh([c[0] for c in R.CONS], days)
    args, w = design(use, None)
    k = len(use)
    rot = st['kind'] == 'rot'
    if not rot:
        fl, eb = axis(st, fit)
    nc = 1 + 2 * k                                  # a series: the mean, H cos g, H sin g
    A, b = [], []

    def val(j):
        a, f = args(j)
        return np.concatenate(([1.0], f * np.cos(a), f * np.sin(a)))

    def der(j):
        a, f = args(j)
        return np.concatenate(([0.0], -f * w * np.sin(a), f * w * np.cos(a)))
    z = np.zeros(nc)
    for kind, t, sp, d in fit:
        j = jd(t)
        if not rot:
            if kind == 'SLACK':
                A.append(val(j)); b.append(0.0); continue
            if kind == 'FLOOD':
                s = sp
            elif kind == 'EBB':
                s = -sp
            else:                                   # MAX, MIN, AT: the sign from the set
                s = sp if d is None or angdiff(d, fl) <= angdiff(d, eb) else -sp
            A.append(val(j)); b.append(s)
            if kind in ('FLOOD', 'EBB', 'MAX'):
                A.append(der(j)); b.append(0.0)
            continue
        if d is None:
            raise SystemExit('%s: a rotary station needs the set of each row (%s %s)' % (st['name'], kind, t))
        u, v = sp * math.sin(math.radians(d)), sp * math.cos(math.radians(d))
        A.append(np.concatenate((val(j), z))); b.append(u)
        A.append(np.concatenate((z, val(j)))); b.append(v)
        if kind in ('MAX', 'MIN', 'FLOOD', 'EBB'):
            A.append(np.concatenate((u * der(j), v * der(j)))); b.append(0.0)
    x, *_ = np.linalg.lstsq(np.array(A), np.array(b), rcond=None)

    def consts(x0):
        return ({n: (round(float(math.hypot(x0[1 + i], x0[1 + k + i])), 4),
                     round(math.degrees(math.atan2(x0[1 + k + i], x0[1 + i])) % 360, 2)) for i, n in enumerate(use)},
                round(float(x0[0]), 3))
    hc, z0 = consts(x[:nc])
    out = dict(kind=st['kind'], z0=z0, hc=hc, use=use, days=days)
    if rot:
        out['hv'], out['v0'] = consts(x[nc:])
        out['flood'] = out['ebb'] = 0
    else:
        out.update(hv={}, v0=0.0, flood=fl, eb=eb, ebb=eb)
    return out


def compare(port, rows, split):
    """Tide 47 (tide47ref.sday: the C47's numbers) against the table rows from `split`: each event against Tide 47's
    nearest of the same kind (within 2 hours); timed speeds against the prediction at that time."""
    dts, dsp, dset, miss = [], [], [], 0
    test = [r for r in rows if r[1] >= split]
    days = {}
    for kind, t, sp, d in test:
        n = R.jdn(t.year, t.month, t.day)
        if n not in days:
            days[n] = R.sday(port, n)
        h = t.hour + t.minute / 60
        if kind == 'AT':
            v, s = R.stream_now(port, n, h)
            dsp.append(abs(v) - sp)
            if port['kind'] == 'rot' and sp > 0.3:
                dset.append((s - d + 180) % 360 - 180)
            continue
        want = -1 if kind in ('SLACK', 'MIN') else 1
        cand = [e for e in days[n][1] if e[3] == want]
        if port['kind'] == 'rect' and kind in ('FLOOD', 'EBB'):
            cand = [e for e in cand if (e[1] > 0) == (kind == 'FLOOD')]
        if not cand:
            miss += 1; continue
        e = min(cand, key=lambda e: abs(e[0] - h))
        if abs(e[0] - h) > 2:
            miss += 1; continue
        dts.append((e[0] - h) * 60)
        if sp is not None and kind != 'SLACK':
            dsp.append(abs(e[1]) - sp)
    rms = lambda v: math.sqrt(sum(x * x for x in v) / len(v)) if v else 0.0
    mx = lambda v: max((abs(x) for x in v), default=0.0)
    return dict(n=len(test), events=len(dts), miss=miss, t_rms=rms(dts), t_max=mx(dts), s_rms=rms(dsp), s_max=mx(dsp),
                set_rms=rms(dset))


def main():
    args = list(sys.argv[1:])
    split = None
    if '--rayleigh' in args:
        i = args.index('--rayleigh'); MP.RAYLEIGH = float(args[i + 1]); del args[i:i + 2]
    if '--test-from' in args:
        i = args.index('--test-from'); split = dt.datetime.strptime(args[i + 1], '%Y-%m-%d'); del args[i:i + 2]
    folder = args[0] if args else os.path.join(ROOT, 'private', 'streams')
    files = sorted(f for f in os.listdir(folder) if f.endswith('.txt')) if os.path.isdir(folder) else []
    if not files:
        raise SystemExit('no station files in %s (see the header of this tool, and docs/STREAMS.md)' % folder)
    ports, report = [], []
    for f in files:
        st, rows, hc, means = read_station(os.path.join(folder, f))
        if hc:
            names = [c[0] for c in R.CONS]
            hc = {n: v for n, v in hc.items() if n in names}
            if st['kind'] == 'rect':
                fl, eb = axis(st, rows)
                fit = dict(kind='rect', z0=means.get('z0', 0.0), v0=0.0, hc={n: v[:2] for n, v in hc.items()}, hv={},
                           flood=fl, ebb=eb)
            else:
                fit = dict(kind='rot', z0=means.get('z0', 0.0), v0=means.get('v0', 0.0), flood=0, ebb=0,
                           hc={n: v[:2] for n, v in hc.items()}, hv={n: v[2:4] for n, v in hc.items()})
            how = 'constants from the tables (%d)' % len(hc)
        else:
            if not rows:
                print('%-22s no rows yet: left out' % st['name'])
                continue
            fit = analyse(st, rows, split)
            how = '%d rows over %.0f days -> %d constituents' % (
                len([r for r in rows if split is None or r[1] < split]), fit['days'], len(fit['use']))
        port = dict(name=st['name'][:22], lat=st['lat'], lon=st['lon'], tz=st['tz'], dst='', kind=fit['kind'],
                    flood=int(fit['flood']), ebb=int(fit['ebb']), z0=fit['z0'], v0=fit['v0'],
                    datum=('FLOOD %03d° EBB %03d°' % (fit['flood'], fit['ebb'])) if fit['kind'] == 'rect'
                    else 'ROTARY, KNOTS',
                    src=st.get('source', 'GEOSA tables')[:24], hc=fit['hc'], hv=fit['hv'])
        ports.append(port)
        m2 = port['hc'].get('M2', (0, 0))[0]
        print('%-22s %s; %s%s; M2 %.3f kn' % (st['name'], how, port['kind'],
                                            ' flood %03d ebb %03d' % (port['flood'], port['ebb'])
                                            if port['kind'] == 'rect' else '', m2))
        if split is not None and not hc:
            c = compare(port, rows, split)
            report.append((port['name'], c))
            print('    from %s: %d rows, %d events compared (%d not found): time %.1f min rms (worst %.0f), '
                  'speed %.2f kn rms (worst %.2f)%s' % (split.date(), c['n'], c['events'], c['miss'], c['t_rms'],
                                                       c['t_max'], c['s_rms'], c['s_max'],
                                                       ', set %.0f deg rms' % c['set_rms'] if c['set_rms'] else ''))
    if not ports:
        raise SystemExit('no station with rows yet in %s' % folder)
    out = ['"""streams_private.py - the private region GULF STREAMS (written by tools/make_private_streams.py from',
           'private/streams/; never in git: the constants come from current tables that may not be published)."""', '',
           'SPLIT = %r' % (split.strftime('%Y-%m-%d') if split else None), 'FOLDER = %r' % os.path.abspath(folder), '',
           'REGIONS = [', "    ('GS', 'TIDEGS', 'GULF STREAMS: PRIVATE', ["]
    for p in ports:
        out.append('        %r,' % p)
    out += ['    ]),', ']']
    if folder == os.path.join(ROOT, 'private', 'streams') or os.environ.get('TIDE47_WRITE_PRIVATE'):
        open(os.path.join(ROOT, 'python', 'streams_private.py'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
        print('python/streams_private.py: %d stations; next: python3 tools/build_tide47.py --private' % len(ports))
    if report:
        os.makedirs(os.path.join(ROOT, 'private'), exist_ok=True)
        md = ['# Tide 47 against the current tables (rows from %s, left out of the fit)' % split.date(), '',
              '| station | rows | events | not found | time rms (min) | worst | speed rms (kn) | worst | set rms |',
              '|---|---|---|---|---|---|---|---|---|']
        md += ['| %s | %d | %d | %d | %.1f | %.0f | %.2f | %.2f | %s |' % (
            n, c['n'], c['events'], c['miss'], c['t_rms'], c['t_max'], c['s_rms'], c['s_max'],
            '%.0f' % c['set_rms'] if c['set_rms'] else '') for n, c in report]
        open(os.path.join(ROOT, 'private', 'STREAMS_COMPARE.md'), 'w').write('\n'.join(md) + '\n')
    return ports, report


if __name__ == '__main__':
    main()
