#!/usr/bin/env python3
"""make_web_data.py - the data files of the web app (web/): the engine's constants and the stations as JavaScript.

  web/data/cons.js     the constituents (python/tide47ref.py CONS: Doodson numbers, nodal u and f), the speeds of the
                       angles, the nodal formulas' constants K: one source for the Python twin and the web engine
  web/data/public.js   the public stations: python/stations.py (NOAA, TICON-3) and python/streams.py (NOAA currents)
  web/data/private.js  your private stations, when python/stations_private.py (Aramco) and python/streams_private.py
                       are there: git-ignored, never published (docs/ARAMCO.md)

They are plain scripts (globalThis.T47CONS, T47PUBLIC, T47PRIVATE), so index.html works opened as a file (file://).
  python3 tools/make_web_data.py"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'python'))
import tide47ref as R                                                                     # noqa: E402

OUT = os.path.join(ROOT, 'web', 'data')
KEYS = ('name', 'lat', 'lon', 'tz', 'dst', 'datum', 'z0', 'src', 'kind', 'flood', 'ebb', 'v0')


def station(p):
    s = {k: p[k] for k in KEYS if k in p}
    s['hc'] = {k: [round(v[0], 6), round(v[1], 3)] for k, v in p['hc'].items() if v[0] > 0}
    if p.get('hv'):
        s['hv'] = {k: [round(v[0], 6), round(v[1], 3)] for k, v in p['hv'].items() if v[0] > 0}
    return s


def regions(regs, stream=False):
    return [dict(code=c, label=l, title=t, stream=stream, stations=[station(p) for p in ps]) for c, l, t, ps in regs]


def write(name, var, obj, note):
    path = os.path.join(OUT, name)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('// %s - written by tools/make_web_data.py; do not edit\n' % note)
        fh.write('globalThis.%s = %s;\n' % (var, json.dumps(obj, ensure_ascii=False, separators=(',', ':'))))
    print('%-22s %7d bytes' % (os.path.relpath(path, ROOT), os.path.getsize(path)))


def main():
    os.makedirs(OUT, exist_ok=True)
    write('cons.js', 'T47CONS', dict(
        cons=[[n, list(dd), k90, uc, fc] for n, dd, k90, uc, fc in R.CONS], speed=list(R.SPEED), UB=R.UB, FB=R.FB,
        K=R.K), 'the constituents and constants of python/tide47ref.py')
    import stations, streams
    write('public.js', 'T47PUBLIC', regions(stations.REGIONS) + regions(streams.REGIONS, True),
          'public stations: NOAA (public domain), TICON-3 (CC-BY 4.0)')
    priv = []
    try:
        import stations_private
        priv += regions(stations_private.REGIONS)
    except ImportError:
        pass
    try:
        import streams_private
        priv += regions(streams_private.REGIONS, True)
    except ImportError:
        pass
    path = os.path.join(OUT, 'private.js')
    if priv:
        write('private.js', 'T47PRIVATE', priv, 'PRIVATE stations (Aramco and others): never publish this file')
    elif os.path.exists(path):
        print('no private stations: %s left as it is' % os.path.relpath(path, ROOT))
    else:
        print('no python/stations_private.py: no web/data/private.js (public stations only)')


if __name__ == '__main__':
    main()
