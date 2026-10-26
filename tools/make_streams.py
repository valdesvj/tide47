#!/usr/bin/env python3
"""make_streams.py - writes python/streams.py, the public tidal-stream stations of Tide 47 (the region US STREAMS).

Source: NOAA CO-OPS current stations (public domain), from XTide's harmonics-dwf-20191229-free (Debian package
xtide-data; restore_tide_db gives the text). NOAA's current constants are rectilinear: the speed along the flood
direction (knots, + flood, - ebb) with its mean (the "datum" line), and the flood and ebb directions (max_direction,
min_direction, deg true). Hydraulic stations (knots^2) are left out.

A stream station (python/tide47ref.py sday): kind 'rect', hc the along-axis constants, z0 the mean (knots), flood,
ebb (integer degrees: the C47 packs them as flood + ebb / 1000 in R79).
  python3 tools/make_streams.py XTIDE_TEXT"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'python'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import tide47ref as R
from make_stations import xtide

# name on the C47 (at most 22 characters), XTide's name, time zone (standard), DST
CU = [
    ('Pollock Rip Channel MA', 'Pollock Rip Channel (Butler Hole), Massachusetts Current', -5, 'US'),
    ('Charleston Harbor SC', 'Charleston Harbor (off Fort Sumter), South Carolina Current', -5, 'US'),
    ('Tampa Bay entrance FL', 'Tampa Bay entrance (Egmont Channel), Florida Current (15d)', -5, 'US'),
    ('Bolivar Roads TX', 'Bolivar Roads, Texas Current (14d)', -6, 'US'),
    ('San Diego Bay ent. CA', 'San Diego Bay entrance, California Current', -8, 'US'),
    ('Admiralty Inlet WA', 'Admiralty Inlet (off Bush Point) (Depth 29ft), Washington Current', -8, 'US'),
    ('Deception Pass WA', 'Deception Pass (Narrows) (Depth 17.6ft), Rosario Strait, Washington Current', -8, 'US'),
]


def main():
    xt = xtide(sys.argv[1])
    names = [c[0] for c in R.CONS]
    ports = []
    for label, key, tz, dst in CU:
        hot, z0, unit, cons = xt[key]
        assert unit == 'knots', (key, unit)
        hc = {n: (round(H, 4), round(g, 2)) for n, (H, g) in cons.items() if n in names and H > 0}
        ports.append(dict(name=label, lat=float(hot['latitude']), lon=float(hot['longitude']), tz=tz, dst=dst,
                          kind='rect', flood=int(hot['max_direction']), ebb=int(hot['min_direction']),
                          z0=round(z0, 3), v0=0.0, datum='FLOOD %03d° EBB %03d°' % (int(hot['max_direction']),
                                                                                  int(hot['min_direction'])),
                          src='NOAA ' + hot['station_id'].split('_')[0], hc=hc, hv={}))
    out = ['"""streams.py - the tidal-stream stations of Tide 47 (written by tools/make_streams.py; never edit by hand).',
           'NOAA CO-OPS current stations (public domain) from XTide\'s harmonics-dwf-20191229-free. A station: kind',
           "'rect' (the speed along the flood direction, knots: hc, its mean z0; flood, ebb deg true) or 'rot' (hc the",
           'east component u, hv the north v, z0 v0 their means); see python/tide47ref.py sday."""', '',
           'REGIONS = [', "    ('CU', 'TIDECU', 'US STREAMS: NOAA', ["]
    for p in ports:
        out.append('        %r,' % p)
    out += ['    ]),', ']']
    open(os.path.join(ROOT, 'python', 'streams.py'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    for p in ports:
        print('%-22s flood %03d ebb %03d  z0 %+.3f kn  M2 %.3f kn  %d constituents' % (
            p['name'], p['flood'], p['ebb'], p['z0'], p['hc'].get('M2', (0, 0))[0], len(p['hc'])))


if __name__ == '__main__':
    main()
