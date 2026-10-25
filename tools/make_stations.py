#!/usr/bin/env python3
"""make_stations.py - writes python/stations.py, the ports of Tide 47 and their harmonic constants.

Sources (both free to publish, with attribution):
  US        NOAA CO-OPS (public domain), from XTide's harmonics-dwf-20191229-free (Debian package xtide-data):
            the 37 NOAA constituents, the datum MLLW (Z0 = mean sea level above MLLW), feet -> metres.
  ME, LA    TICON-3 (Hart-Davis, Dettmering, Seitz 2022, CC-BY 4.0, doi:10.1594/PANGAEA.951610): least-squares
            constants of the GESLA-3 gauges, cm, Greenwich lags. SA is phased with the solar perigee (V = h - p1,
            as UTide; checked against NOAA at six US gauges: +73..+93 deg, p1 = 283): converted by + p1. The datum
            is LAT, the Admiralty chart datum: the lowest height of the 19 years 2020-2038 (hourly, then the
            minimum refined), so Z0 = mean sea level above LAT.
  python3 tools/make_stations.py XTIDE_TEXT TICON_3.txt      (restore_tide_db's text, TICON_3.txt)"""
import math, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'python'))
import numpy as np
import tide47ref as R

# the ports: region, the label on the C47, the source key (XTide name / TICON lat lon source), the time zone (hours,
# standard time), DST ('US' or ''); names as on the C47 screen (at most 22 characters)
US = [
    ('Boston, MA', 'Boston, Boston Harbor, Massachusetts', -5, 'US'),
    ('New York (Battery)', 'The Battery, New York Harbor, New York', -5, 'US'),
    ('Charleston, SC', 'Charleston, Cooper River entrance, South Carolina', -5, 'US'),
    ('Key West, FL', 'Key West, Florida', -5, 'US'),
    ('Galveston, TX', 'Galveston Pier 21, Galveston Channel, Texas', -6, 'US'),
    ('San Diego, CA', 'San Diego, San Diego Bay, California', -8, 'US'),
    ('San Francisco, CA', 'San Francisco, San Francisco Bay, California', -8, 'US'),
    ('Seattle, WA', 'Seattle, Puget Sound, Washington', -8, 'US'),
    ('Honolulu, HI', 'Honolulu, Honolulu Harbor, Oahu Island, Hawaii', -10, ''),
    ('San Juan, PR', 'San Juan, La Puntilla, San Juan Bay, Puerto Rico', -4, ''),
]
ME = [
    ('Mina Salman, Bahrain', (26.233, 50.600, 'gesla.ncdem'), 3, ''),
    ('Mina Qaboos, Muscat', (23.628, 58.565, 'gesla.smhi'), 4, ''),
    ('Masirah, Oman', (20.687, 58.872, 'gesla.meds'), 4, ''),
    ('Salalah, Oman', (16.935, 54.007, 'gesla.usgs'), 4, ''),
    ('Chabahar, Iran', (25.297, 60.603, 'gesla.refmar'), 3.5, ''),
    ('Karachi, Pakistan', (24.812, 66.975, 'gesla.ispra'), 5, ''),
    ('Aden, Yemen', (12.788, 44.975, 'gesla.uhslc'), 3, ''),
    ('Djibouti', (11.608, 43.140, 'gesla.cmems'), 3, ''),
]
LA = [
    ('Cartagena, Colombia', (10.390, 284.468, 'gesla.cmems'), -5, ''),
    ('Santa Marta, Colombia', (11.235, 285.778, 'gesla.noaa'), -5, ''),
    ('Cristobal, Panama', (9.355, 280.085, 'gesla.meds'), -5, ''),
    ('Balboa, Panama', (8.965, 280.427, 'gesla.meds'), -5, ''),
    ('Buenaventura, Col.', (3.890, 282.938, 'gesla.noaa'), -5, ''),
    ('Tumaco, Colombia', (1.817, 281.270, 'gesla.meds'), -5, ''),
    ('La Libertad, Ecuador', (-2.200, 279.083, 'gesla.usgs'), -5, ''),
]
REGIONS = [('ME', 'TIDEME', 'MIDDLE EAST: TICON-3', ME), ('US', 'TIDEUS', 'USA: NOAA', US),
           ('LA', 'TIDELA', 'LATIN AMERICA: TICON-3', LA)]
TICON_NAMES = {'LM2': 'LAM2', 'MI2': 'MU2', 'NI2': 'NU2', 'EP2': 'EPS2', 'MKS': 'MKS2', 'MSQ': 'MSQM'}
P1_SA = 283.1                                        # the solar perigee (deg) of TICON's SA convention, 2010


def xtide(fn):
    """The harmonic stations of restore_tide_db's text: name -> (hot comments, datum (value, unit), {const: (H, g)})."""
    L = open(fn, encoding='latin-1').read().split('\n')
    i = 0

    def nxt():
        nonlocal i
        while L[i].startswith('#') or not L[i].strip():
            i += 1
        i += 1
        return L[i - 1]
    n = int(nxt())
    names = [nxt().split()[0] for _ in range(n)]
    nxt()
    for _ in range(2):                                         # the year tables
        ny = int(nxt())
        for _ in range(n):
            vals = len(nxt().split()) - 1
            while vals < ny:
                vals += len(nxt().split())
        assert nxt().strip() == '*END*'
    out = {}
    while i < len(L):
        hot = {}
        while i < len(L) and (L[i].startswith('#') or not L[i].strip()):
            m = re.match(r'# !?(\w+): (.*)', L[i])
            if m:
                hot[m.group(1)] = m.group(2).strip()
            i += 1
        if i >= len(L):
            break
        name, tz, datum = L[i], L[i + 1], L[i + 2]
        i += 3
        cons = {}
        for k in range(n):
            p = L[i].split(); i += 1
            if p[0] != 'x':
                cons[p[0]] = (float(p[1]), float(p[2]))
        v, unit = datum.split()
        out[name] = (hot, float(v), unit, cons)
    return out


def ticon(fn):
    st = {}
    for ln in open(fn, encoding='latin-1'):
        p = ln.split()
        if len(p) >= 14:
            st.setdefault((float(p[0]), float(p[1]), p[12]), {})[TICON_NAMES.get(p[2], p[2])] = (float(p[3]) / 100, float(p[4]))
    return st


def lat_offset(hc):
    """The mean sea level above LAT (m): minus the lowest tide of 2020-2038 (19 years), hourly in numpy, then the
    minimum refined to the minute around the lowest hours."""
    names = [c[0] for c in R.CONS]
    w = np.radians(np.array(R.speeds()))
    H = np.array([hc.get(n, (0, 0))[0] for n in names]); G = np.radians([hc.get(n, (0, 0))[1] for n in names])
    t = np.arange(24.0)
    lows = []
    for d in range(int(R.jd(2020, 1, 1)), int(R.jd(2039, 1, 1)) + 1):
        vf = R.vector(d + 0.5)
        A = H * np.array([f for _, f in vf]); P = np.radians([v for v, _ in vf]) - G
        h = (A[:, None] * np.cos(P[:, None] + w[:, None] * t[None, :])).sum(0)
        lows.append((h.min(), d + 0.5, t[h.argmin()]))
    lows.sort()
    best = 0
    for hmin, j, t0 in lows[:40]:                       # refine the 40 lowest hours
        vf = R.vector(j)
        A = H * np.array([f for _, f in vf]); P = np.radians([v for v, _ in vf]) - G
        tt = np.arange(t0 - 1, t0 + 1, 1 / 60)
        best = min(best, (A[:, None] * np.cos(P[:, None] + w[:, None] * tt[None, :])).sum(0).min())
    return -best


def main():
    xt, tc = xtide(sys.argv[1]), ticon(sys.argv[2])
    names = [c[0] for c in R.CONS]
    out = ['"""stations.py - the ports of Tide 47 (written by tools/make_stations.py; never edit by hand).',
           'Each station: name, lat, lon, tz (hours, standard time), dst (\'US\' or \'\'), datum, z0 (m: mean sea level',
           'above the datum), source, hc {constituent: (H m, g deg Greenwich)}."""', '', 'REGIONS = [']
    for code, label, title, rows in REGIONS:
        out.append('    (%r, %r, %r, [' % (code, label, title))
        for nm, key, tz, dst in rows:
            if code == 'US':
                hot, z0, unit, cons = xt[key]
                k = 0.3048 if unit == 'feet' else 1.0
                hc = {}
                for n in names:
                    xn = {'LAM2': 'LDA2'}.get(n, n)
                    if xn in cons and cons[xn][0] > 0:
                        hc[n] = (round(cons[xn][0] * k, 4), cons[xn][1])
                la, lo = float(hot['latitude']), float(hot['longitude'])
                datum, z = 'MLLW', round(z0 * k, 3)
                src = 'NOAA %s' % hot['station_id']
            else:
                cons = tc[key]
                hc = {n: (round(cons[n][0], 4), round((cons[n][1] + (P1_SA if n == 'SA' else 0)) % 360, 2))
                      for n in names if n in cons and cons[n][0] > 0}
                dropped = sorted(((v[0], n) for n, v in cons.items() if n not in names), reverse=True)
                la, lo = key[0], round((key[1] + 180) % 360 - 180, 3)
                datum, z = 'LAT', round(float(lat_offset(hc)), 3)
                src = 'TICON-3 %s' % key[2]
                print('%-22s %2d constituents, LAT %.3f m below MSL, left out %s' % (
                    nm, len(hc), z, ', '.join('%s %.1f cm' % (n, a * 100) for a, n in dropped[:3]) or '-'))
            out.append('        dict(name=%r, lat=%r, lon=%r, tz=%r, dst=%r, datum=%r, z0=%r, src=%r,' % (
                nm, la, lo, tz, dst, datum, z, src))
            out.append('             hc=%r),' % hc)
        out.append('    ]),')
    out.append(']')
    open(os.path.join(ROOT, 'python', 'stations.py'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('python/stations.py: %d ports' % sum(len(r[3]) for r in REGIONS))


if __name__ == '__main__':
    main()
