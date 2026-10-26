"""synth_flow.py - a SYNTHETIC tidal stream atlas for the tests of FLOW47 (invented streams on the atlas grid, a corner
of land; not real data: the real atlas is private)."""
import math


def atlas(nlat=19, nlon=13):
    cells = []
    code = lambda x: int(min(max(round(x / 0.05) + 50, 1), 99))
    for i in range(nlat):
        for j in range(nlon):
            if i < 6 and j < 7 - i:                   # land in the south-west corner (a coast)
                cells.append(None)
                continue
            amp = 0.3 + 0.04 * i + 0.03 * j
            rot = math.radians(20 * j - 10 * i)
            row = []
            for k in range(13):
                ph = 2 * math.pi * (k - 6) / 12.42 + 0.2 * i
                a, b = amp * math.cos(ph), 0.35 * amp * math.sin(ph)
                row.append((code(a * math.sin(rot + 0.6) + b * math.cos(rot)),
                            code(a * math.cos(rot + 0.6) - b * math.sin(rot))))
            cells.append(row)
    return dict(lat0=26.0, lon0=48.75, step_min=10, nlat=nlat, nlon=nlon, q=0.05, cells=cells, ref='Mina Salman',
                source='synthetic')
