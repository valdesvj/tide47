#!/usr/bin/env python3
"""digitize_atlas.py - read the arrows of a tidal stream atlas (a scanned PDF: one chart an hour, HW-6 ... HW+6) into
private/atlas/arrows.json, for tools/make_flow.py and FLOW47. Written for the 'Arabian Gulf Tidal Flow' charts
(Safaniya to Dammam, 26-29 N, 48 45-50 45 E, Mercator, the speed as five colour bands of the spring tide), whose data
may not be published: everything it writes stays in private/ (git-ignored).

The steps, per chart:
  1. the page at 200 dpi (pdftoppm); an upside-down page is found (the land and the legend, white, belong in the
     lower left) and turned;
  2. the graticule: the frame's four lines (Hough), the tick marks just outside them, the ticks every 15' (labels
     48 45 E ... 50 45 E along the top, 29 00 N ... 26 00 N down the sides) -> a Mercator fit pixel = R (sx lon,
     -sy merc lat) + t (5 parameters and the frame's latitude / longitudes; 3-4 px rms, about 0.4 nm);
  3. the arrows: dark pixels against the local background (not the blue labels, not the red pipelines), joined by a
     3 x 3 dilation; each component of the right size and elongation is an arrow; its axis by PCA, its head the
     wider end; its bearing through the fit (true degrees, where the stream goes);
  4. the speed: the background colour around the arrow, the nearest of the five legend bands in Lab (0.13 0.38 0.63
     0.88 1.25 kn: the bands' middles); white (land around a coastal arrow): left for the neighbours;
  5. the neighbours' consensus: an arrow 135+ deg from its neighbours' mean had its head read at the wrong end
     (turned), 70-135 deg off is dropped; the legend box and the compass rose (on land) are left out.
  python3 tools/digitize_atlas.py ATLAS.pdf [--first-page 2] [--out private/atlas/arrows.json]
Needs opencv-python, numpy, scipy and pdftoppm (poppler)."""
import json, os, subprocess, sys, tempfile
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOURS = list(range(-6, 7))
PAL = [((176, 207, 197), 0.13), ((210, 223, 199), 0.38), ((226, 222, 163), 0.63), ((215, 201, 157), 0.88),
       ((200, 163, 144), 1.25), ((232, 234, 234), None)]
TOP_LON, LEFT_LAT, STEP_LON, STEP_LAT = 48.75, 29.0, 0.25, 0.25     # the first meridian / parallel ticked, 15'
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 26.0, 29.0, 48.75, 50.75


def merc(lat):
    return np.degrees(np.log(np.tan(np.radians(45 + np.asarray(lat) / 2))))


def unmerc(m):
    return np.degrees(2 * np.arctan(np.exp(np.radians(m)))) - 90


# ---- the graticule ----
def frame_lines(g):
    import cv2
    dark = (g < 110).astype(np.uint8) * 255
    L = cv2.HoughLinesP(dark, 1, np.pi / 1800, 400, minLineLength=600, maxLineGap=60).reshape(-1, 4)
    ang = np.degrees(np.arctan2(L[:, 3] - L[:, 1], L[:, 2] - L[:, 0]))
    H = [l for l, a in zip(L, ang) if abs(a) < 10]
    V = [l for l, a in zip(L, ang) if abs(a) > 80]
    mid = lambda l, ax: (l[ax] + l[ax + 2]) / 2
    return (min(H, key=lambda l: mid(l, 1)), min(V, key=lambda l: mid(l, 0)), max(V, key=lambda l: mid(l, 0)))


def tick_peaks(g, l):
    """the tick marks just outside a frame line: the darkness 4-13 px outside, along the line; its peaks"""
    x1, y1, x2, y2 = [float(v) for v in l]
    d = np.array([x2 - x1, y2 - y1]); d /= np.hypot(*d)
    nrm = np.array([-d[1], d[0]])
    c = np.array([g.shape[1] / 2, g.shape[0] / 2]); m = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
    if np.dot(nrm, m - c) < 0:
        nrm = -nrm
    P0 = np.array([x1, y1])
    T = np.arange(-1500, 2500)
    pts = P0[None, :] + d[None, :] * T[:, None]
    v = np.zeros(len(T))
    for o in range(4, 14):
        q = np.rint(pts + nrm * o).astype(int)
        ok = (q[:, 0] >= 0) & (q[:, 0] < g.shape[1]) & (q[:, 1] >= 0) & (q[:, 1] < g.shape[0])
        v[ok] += g[q[ok, 1], q[ok, 0]] < 120
    pk = [int(T[i]) for i in range(1, len(v) - 1) if v[i] >= 6 and v[i] >= v[i - 1] and v[i] > v[i + 1]]
    groups = []
    for t in pk:
        if groups and t - groups[-1][-1] <= 6:
            groups[-1].append(t)
        else:
            groups.append([t])
    return [P0 + d * np.mean(c_) for c_ in groups]


def regular(pts, axis, step_guess):
    """the longest chain of points on a regular spacing (the ticks)"""
    pts = sorted(pts, key=lambda p: p[axis])
    best, bst = [], step_guess
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            s = pts[j][axis] - pts[i][axis]
            for k in range(1, 14):
                st = s / k
                if abs(st - step_guess) > 12:
                    continue
                chain = [p for p in pts if abs((p[axis] - pts[i][axis]) / st - round((p[axis] - pts[i][axis]) / st)) < 0.08]
                if len(chain) > len(best):
                    best, bst = chain, st
    return best, bst


def georef(g):
    from scipy.optimize import least_squares
    top, left, right = frame_lines(g)
    tp, stx = regular(tick_peaks(g, top), 0, 134.6)
    lp, sty = regular(tick_peaks(g, left), 1, 153.5)
    rp, _ = regular(tick_peaks(g, right), 1, 153.5)
    xl = (left[0] + left[2]) / 2
    i0 = min(range(len(tp)), key=lambda i: abs(tp[i][0] - (xl + 150)))
    lons = [TOP_LON + STEP_LON * round((p[0] - tp[i0][0]) / stx) for p in tp]
    yt = (top[1] + top[3]) / 2
    j0 = min(range(len(lp)), key=lambda i: abs(lp[i][1] - (yt + 55)))
    lats_l = [LEFT_LAT - STEP_LAT * round((p[1] - lp[j0][1]) / sty) for p in lp]
    k0 = min(range(len(rp)), key=lambda i: abs(rp[i][1] - lp[j0][1] - (rp[i][0] - lp[j0][0]) * np.tan(np.radians(2))))
    lats_r = [LEFT_LAT - STEP_LAT * round((p[1] - rp[k0][1]) / sty) for p in rp]
    keep = lambda P, L: [(p, l) for p, l in zip(P, L) if LAT_MIN - 1e-9 <= l <= LAT_MAX + 1e-9]
    lp, lats_l = map(list, zip(*keep(lp, lats_l)))
    rp, lats_r = map(list, zip(*keep(rp, lats_r)))

    def px(p, lo, la):
        th, sx, sy, tx, ty = p[:5]
        X = sx * (lo - 49.75); Y = -sy * (merc(la) - merc(27.5))
        return np.array([np.cos(th) * X - np.sin(th) * Y + tx, np.sin(th) * X + np.cos(th) * Y + ty])

    def res(p):
        latT, lonL, lonR = p[5:8]
        r = []
        for q, lo in zip(tp, lons):
            r += list(px(p, lo, latT) - q)
        for q, la in zip(lp, lats_l):
            r += list(px(p, lonL, la) - q)
        for q, la in zip(rp, lats_r):
            r += list(px(p, lonR, la) - q)
        return np.array(r)
    s = least_squares(res, [0.035, 538, 600, 850, 1150, 29.1, 48.6, 50.9])
    r = res(s.x).reshape(-1, 2)
    return dict(th=float(s.x[0]), sx=float(s.x[1]), sy=float(s.x[2]), tx=float(s.x[3]), ty=float(s.x[4]),
                rms=float(np.sqrt((r ** 2).mean())), ticks=[len(tp), len(lp), len(rp)])


def to_lonlat(o, x, y):
    th = o['th']
    X = np.cos(th) * (x - o['tx']) + np.sin(th) * (y - o['ty'])
    Y = -np.sin(th) * (x - o['tx']) + np.cos(th) * (y - o['ty'])
    return X / o['sx'] + 49.75, float(unmerc(-Y / o['sy'] + merc(27.5)))


# ---- the arrows ----
def arrows(im, o):
    import cv2
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.int16)
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    bg = cv2.medianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), 31).astype(np.int16)
    blue = (hsv[..., 0] > 95) & (hsv[..., 0] < 135) & (hsv[..., 1] > 60)
    red = ((hsv[..., 0] > 140) | (hsv[..., 0] < 6)) & (hsv[..., 1] > 55)
    dark = ((g < 125) & ~blue & ~red) | (((bg - g) > 32) & (g < 165) & (hsv[..., 1] < 100) & ~blue & ~red)
    m = dark.astype(np.uint8)
    nlab, lab, stats, _ = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((3, 3), np.uint8)), 8)
    lab = lab * m
    out = []
    for i in range(1, nlab):
        x, y, w, h, a = stats[i]
        if a < 20 or a > 1600:
            continue
        ys, xs = np.nonzero(lab[y:y + h, x:x + w] == i)
        P = np.stack([xs + x, ys + y], 1).astype(float)
        c = P.mean(0); Q = P - c
        ev, evec = np.linalg.eigh(Q.T @ Q / len(Q))
        L = 4 * np.sqrt(ev[1]); W = 4 * np.sqrt(max(ev[0], 1e-6))
        if L < 14 or L > 80 or L / W < 1.6:
            continue
        t = Q @ evec[:, 1]; perp = Q @ evec[:, 0]
        lo, hi = t.min(), t.max(); span = hi - lo
        a1 = t < lo + span * 0.35; a2 = t > hi - span * 0.35
        s1 = (np.ptp(perp[a1]) if a1.sum() > 2 else 0) + a1.sum() * 0.05
        s2 = (np.ptp(perp[a2]) if a2.sum() > 2 else 0) + a2.sum() * 0.05
        if abs(s1 - s2) < 0.6:
            continue
        d = evec[:, 1] if s2 > s1 else -evec[:, 1]
        lon, lat = to_lonlat(o, c[0], c[1])
        th = o['th']
        X = np.cos(th) * d[0] + np.sin(th) * d[1]; Y = -np.sin(th) * d[0] + np.cos(th) * d[1]
        brg = float(np.degrees(np.arctan2(X / o['sx'], -Y / o['sy'])) % 360)
        r = int(L * 0.9) + 6; x0, y0 = int(c[0]), int(c[1])
        win = im[max(0, y0 - r):y0 + r, max(0, x0 - r):x0 + r].reshape(-1, 3)
        gw = g[max(0, y0 - r):y0 + r, max(0, x0 - r):x0 + r].reshape(-1)
        bgc = np.median(win[gw > 150], 0)[::-1] if (gw > 150).sum() > 20 else None
        out.append(dict(lon=float(lon), lat=lat, brg=brg, kn=speed(bgc), x=float(c[0]), y=float(c[1])))
    return out


def speed(rgb):
    import cv2
    if rgb is None:
        return None
    lab = cv2.cvtColor(np.uint8([[c for c, _ in PAL]]), cv2.COLOR_RGB2LAB)[0].astype(float)
    l = cv2.cvtColor(np.uint8([[rgb]]), cv2.COLOR_RGB2LAB)[0, 0].astype(float)
    return PAL[int(((lab - l) ** 2).sum(1).argmin())][1]


def consensus(arr, R=0.13, it=3):
    lon = np.array([a['lon'] for a in arr]); lat = np.array([a['lat'] for a in arr])
    brg = np.array([a['brg'] for a in arr]); keep = np.ones(len(arr), bool)
    cl = np.cos(np.radians(27.5))
    for _ in range(it):
        nb = []
        for i in range(len(arr)):
            d = np.hypot((lon - lon[i]) * cl, lat - lat[i])
            j = np.nonzero((d < R) & (d > 1e-9) & keep)[0]
            if len(j) < 3:
                nb.append(None); continue
            w = 1 / (d[j] + 0.02)
            mx = (w * np.sin(np.radians(brg[j]))).sum(); my = (w * np.cos(np.radians(brg[j]))).sum()
            nb.append((np.degrees(np.arctan2(mx, my)) % 360, np.hypot(mx, my) / w.sum()))
        for i, v in enumerate(nb):
            if v is None or v[1] < 0.5:
                continue
            dd = abs((brg[i] - v[0] + 180) % 360 - 180)
            if dd > 135:
                brg[i] = (brg[i] + 180) % 360
            elif dd > 70:
                keep[i] = False
    for a, b in zip(arr, brg):
        a['brg'] = float(b)
    return [a for a, k in zip(arr, keep) if k]


def in_map(a):
    lo, la = a['lon'], a['lat']
    return (LON_MIN - 0.05 < lo < LON_MAX + 0.1 and LAT_MIN - 0.02 < la < LAT_MAX + 0.1
            and not (lo < 49.32 and la < 27.28) and not (lo < 49.6 and la < 26.45))   # the legend, the compass rose


def upright(im):
    """the chart's way up: the land and the legend (white, no shading) are in the lower left, the open Gulf in the
    upper right; a page the other way up has them turned"""
    import cv2
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY); hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    white = (g > 215) & (hsv[..., 1] < 25)
    H, W = g.shape
    ll = white[int(H * 0.55):int(H * 0.9), int(W * 0.12):int(W * 0.5)].mean()
    ur = white[int(H * 0.1):int(H * 0.45), int(W * 0.5):int(W * 0.88)].mean()
    return ll > ur


def page(fn):
    import cv2
    im = cv2.imread(fn)
    turn = not upright(im)
    if turn:
        im = cv2.rotate(im, cv2.ROTATE_180)
    o = georef(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY))
    arr = consensus([a for a in arrows(im, o) if in_map(a)])
    return arr, o, turn


def main():
    args = sys.argv[1:]
    out = os.path.join(ROOT, 'private', 'atlas', 'arrows.json')
    first = None
    if '--out' in args:
        i = args.index('--out'); out = args[i + 1]; del args[i:i + 2]
    if '--first-page' in args:
        i = args.index('--first-page'); first = int(args[i + 1]); del args[i:i + 2]
    pdf = args[0]
    tmp = tempfile.mkdtemp()
    subprocess.run(['pdftoppm', '-r', '200', '-png', pdf, os.path.join(tmp, 'p')], check=True)
    pages = sorted(f for f in os.listdir(tmp) if f.endswith('.png'))
    pages = pages[first - 1:first - 1 + 13] if first else pages[-13:]
    charts = []
    for h, f in zip(HOURS, pages):
        arr, o, turn = page(os.path.join(tmp, f))
        charts.append(dict(hour=h, page=f, turned=turn, georef=o, arrows=arr))
        print('HW%+d  %s%s  graticule %.1f px rms (ticks %s)  %d arrows' % (
            h, f, ' (turned)' if turn else '', o['rms'], o['ticks'], len(arr)))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(dict(source=os.path.basename(pdf), hours=HOURS, bands=[k for _, k in PAL if k], charts=charts),
              open(out, 'w'))
    print(out)


if __name__ == '__main__':
    main()
