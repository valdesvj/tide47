#!/usr/bin/env python3
"""make_flow.py - the tidal stream atlas on a grid for FLOW47: private/atlas/arrows.json (tools/digitize_atlas.py)
-> python/flow_private.py (git-ignored, as the atlas: its data may not be published).

The grid: every 10' of latitude and longitude over the charts (26-29 N, 48 45-50 45 E: 19 x 13 nodes). At a node,
each hour's arrows within 7.5' (a Gaussian weight, 4.5' wide) give the stream east and north (u, v; the spring
speeds of the bands), a missing speed (an arrow on white) the median of its neighbours'. A node is sea when it has
an arrow within 7.5' on half the charts or more. On the C47 a node is 13 hours x (u, v), each u and v rounded to
0.05 kn and packed as two digits (+ 50): hours HW-6 ... HW 0 in one number, HW+1 ... HW+6 in a second.
  python3 tools/make_flow.py [--ref "Ras Tanura"] [--step 10] [--in private/atlas/arrows.json]
--ref: the tide station of the charts' High Water (part of its name; the station must be in a region of the private
build: python/stations_private.py)."""
import json, math, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAT0, LAT1, LON0, LON1 = 26.0, 29.0, 48.75, 50.75
Q = 0.05                                  # kn: the packing step of u and v


def grid(charts, step_min=10):
    step = step_min / 60
    nlat = int(round((LAT1 - LAT0) / step)) + 1
    nlon = int(round((LON1 - LON0) / step)) + 1
    R = step * 0.75
    cl = math.cos(math.radians(27.5))
    U = np.zeros((13, nlat, nlon)); V = np.zeros_like(U); N = np.zeros_like(U)
    for k, ch in enumerate(charts):
        arr = ch['arrows']
        lo = np.array([a['lon'] for a in arr]); la = np.array([a['lat'] for a in arr])
        b = np.radians([a['brg'] for a in arr])
        sp = np.array([a['kn'] if a['kn'] is not None else np.nan for a in arr])
        for i in np.nonzero(np.isnan(sp))[0]:
            d = np.hypot((lo - lo[i]) * cl, la - la[i]); j = (d < 0.15) & ~np.isnan(sp)
            sp[i] = np.median(sp[j]) if j.any() else 0.13
        u, v = sp * np.sin(b), sp * np.cos(b)
        for i in range(nlat):
            for j in range(nlon):
                y, x = LAT0 + i * step, LON0 + j * step
                d = np.hypot((lo - x) * cl, la - y); m = d < R
                N[k, i, j] = m.sum()
                if m.any():
                    w = np.exp(-(d[m] / (R * 0.6)) ** 2)
                    U[k, i, j] = (w * u[m]).sum() / w.sum(); V[k, i, j] = (w * v[m]).sum() / w.sum()
    sea = np.median(N, 0) >= 1
    code = lambda x: int(min(max(round(x / Q) + 50, 1), 99))
    cells = []
    for i in range(nlat):
        for j in range(nlon):
            cells.append([(code(U[k, i, j]), code(V[k, i, j])) for k in range(13)] if sea[i, j] else None)
    return dict(lat0=LAT0, lon0=LON0, step_min=step_min, nlat=nlat, nlon=nlon, q=Q, cells=cells)


def main():
    args = sys.argv[1:]
    ref, step, src = 'Ras Tanura', 10, os.path.join(ROOT, 'private', 'atlas', 'arrows.json')
    if '--ref' in args:
        i = args.index('--ref'); ref = args[i + 1]; del args[i:i + 2]
    if '--step' in args:
        i = args.index('--step'); step = int(args[i + 1]); del args[i:i + 2]
    if '--in' in args:
        i = args.index('--in'); src = args[i + 1]; del args[i:i + 2]
    A = json.load(open(src))
    G = grid(A['charts'], step)
    G.update(ref=ref, source='%s (%s)' % ('Arabian Gulf Tidal Flow', A.get('source', '')))
    out = ['"""flow_private.py - the tidal stream atlas on a grid (written by tools/make_flow.py from %s;' % os.path.basename(src),
           'never in git: the charts\' data may not be published). cells: row by row from the south-west corner (latitude',
           'LAT0 + i STEP, longitude LON0 + j STEP), each None (land) or 13 hours HW-6 ... HW+6 of (u, v) codes:',
           'u = (code - 50) x Q kn east, v north; the spring speeds of the charts."""', '', 'FLOW = %r' % G]
    open(os.path.join(ROOT, 'python', 'flow_private.py'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    sea = sum(c is not None for c in G['cells'])
    print('python/flow_private.py: %d x %d nodes every %d\', %d sea; the reference station: %s' % (
        G['nlat'], G['nlon'], step, sea, ref))


if __name__ == '__main__':
    main()
