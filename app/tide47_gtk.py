#!/usr/bin/env python3
"""tide47_gtk.py - Tide 47 on the PC: a GTK 4 app with the calculator programs' four views, from the same engine
(python/tide47ref.py, the C47's twin: the same numbers as the calculator).

  TIDE  an Aramco station's day: the curve, the high and low waters, now
  FLOW  the tidal stream atlas at a position: HW-6 ... HW+6 of Ras Tanura's High Water, the set and knots, the rose
  ARTF  the stream table at the position and the tide of the Aramco station nearest it (ARTF47's screen)
  MAP   the atlas over the charts' area at any hour of the cycle, the stations, the position (click to move it)

The data are private and stay on your computer: python/stations_private.py (tools/make_private.py, the Aramco
tables) and python/flow_private.py (tools/make_flow.py, the atlas). Without them the app runs on public stand-ins
(the Middle East ports, a synthetic atlas) and says so in red.
  python3 app/tide47_gtk.py           (needs PyGObject with GTK 4 and pycairo: pacman -S python-gobject gtk4 python-cairo)
  python3 app/tide47_gtk.py --png DIR  the four views as PNG files (no window), for a check"""
import datetime as dt, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(ROOT, 'python'), os.path.join(ROOT, 'tests')]
import tide47ref as R                                                   # noqa: E402

D2R = math.pi / 180


# ======== the data ========
class Data:
    """The stations (Aramco's, or the Middle East ports), the atlas (or a synthetic one) and its reference station."""

    def __init__(self):
        self.notes = []
        try:
            import stations_private
            reg = [r for r in stations_private.REGIONS if r[0] == 'AR'] or stations_private.REGIONS
            self.region = reg[0]
        except ImportError:
            import stations
            self.region = stations.REGIONS[0]
            self.notes.append('no python/stations_private.py: the Middle East ports stand in for Aramco\'s')
        self.ports = self.region[3]
        try:
            import flow_private
            self.atlas = flow_private.FLOW
        except ImportError:
            import synth_flow
            self.atlas = synth_flow.atlas()
            self.notes.append('no python/flow_private.py: a SYNTHETIC atlas (not real streams)')
        key = self.atlas.get('ref', 'Ras Tanura').lower()
        self.ref = next((p for p in self.ports if key in p['name'].lower()), None)
        if self.ref is None:
            self.ref = next((p for p in self.ports if 'salman' in p['name'].lower()), self.ports[0])
            self.notes.append('the reference station %s is not among the stations: %s used' % (
                self.atlas.get('ref'), self.ref['name']))

    def now(self, st):
        """The station's local date (JDN) and hour now (UTC + its time zone)."""
        t = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(hours=st['tz'])
        return R.jdn(t.year, t.month, t.day), t.hour + t.minute / 60 + t.second / 3600


def height_fn(st, n):
    """An exact height function of the day n at st (hours -> m)."""
    tz = st['tz'] + R.dst(st, n)
    C = R.comp(st, n - 0.5 - tz / 24, st['hc'])
    return lambda t: R.evaluate(C, st['z0'], t)[0]


def parse_dm(text):
    """DD.MMm or DD MM.m or DD.ddd° -> degrees (S / W or a minus: negative)."""
    s = text.strip().upper().replace(',', '.')
    neg = s.startswith('-') or s.endswith('S') or s.endswith('W')
    s = s.strip('-NSEW ').replace('°', ' ').replace("'", ' ')
    p = s.split()
    if len(p) >= 2:
        v = float(p[0]) + float(p[1]) / 60
    elif s.endswith('D'):
        v = float(s[:-1])
    else:
        v = R.dm(float(p[0]))
    return -v if neg else v


def fmt_pos(lat, lon):
    def one(v, w, h):
        a = abs(v); d = int(a); m = (a - d) * 60
        if round(m, 1) >= 60:
            d, m = d + 1, 0.0
        return '%0*d°%04.1f\'%s' % (w, d, m, h[0] if v >= 0 else h[1])
    return one(lat, 2, 'NS') + ' ' + one(lon, 3, 'EW')


def hhmm(h):
    m = int(round(h * 60)) % 1440
    return '%02d:%02d' % (m // 60, m % 60)


def datestr(n):
    y, m, d = R.cal(n)
    return '%s %02d-%02d-%04d' % (('MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN')[(n) % 7], d, m, y)


# ======== the state: the position, the wind, the High Water of the cycle ========
class State:
    def __init__(self, data):
        self.d = data
        self.lat, self.lon = R.dm(28.24), R.dm(49.36)
        self.wdir, self.wkn = 0.0, 0.0
        self.station = data.ref
        self.tday = data.now(data.ref)[0]
        self.hour = 0                                   # the MAP's hour: HW + hour
        self.to_now()

    # the cycle (Ras Tanura's High Water)
    def to_now(self):
        n, h = self.d.now(self.d.ref)
        self.n, self.m = R.flow_pick(self.d.ref, n, h)

    def step(self, d):
        self.n, self.m = R.flow_step(self.d.ref, self.n, self.m, d)

    def day(self, d):
        t = R.flow_cycle(self.d.ref, self.n, self.m)[0]
        self.n, self.m = R.flow_pick(self.d.ref, self.n + d, t)

    def cycle(self):
        """(HW hour, height, range, factor, the 13 rows (u, v) or None, the offset of now from HW or None, now (u, v))"""
        t, h, rng, f = R.flow_cycle(self.d.ref, self.n, self.m)
        cell = R.flow_cell(self.d.atlas, self.lat, self.lon)
        rows = R.flow_rows(cell, f, self.wdir, self.wkn) if cell else None
        n0, h0 = self.d.now(self.d.ref)
        off = (n0 - self.n) * 24 + h0 - t
        nowuv = R.flow_now(rows, off) if rows and abs(off) <= 6 else None
        return t, h, rng, f, rows, (off if abs(off) <= 6 else None), nowuv

    def nearest(self):
        k, dnm = R.art_nearest(self.d.ports, self.lat, self.lon)
        return self.d.ports[k - 1], dnm


# ======== drawing (cairo): shared by the window and the PNG export ========
INK, SOFT, GRID, ACCENT, WARN, PAPER = (0.10, 0.12, 0.14), (0.45, 0.48, 0.52), (0.82, 0.84, 0.86), \
    (0.05, 0.38, 0.62), (0.75, 0.10, 0.10), (0.98, 0.98, 0.97)


def text(cr, x, y, s, size=12, bold=False, color=INK, align='l'):
    cr.select_font_face('Sans', 0, 1 if bold else 0)
    cr.set_font_size(size)
    w = cr.text_extents(s).x_advance
    cr.set_source_rgb(*color)
    cr.move_to(x - (w if align == 'r' else w / 2 if align == 'c' else 0), y)
    cr.show_text(s)
    return w


def arrow(cr, x, y, u, v, length, color=INK, width=1.6, head=5):
    """an arrow centred at x, y (screen y down) in the stream's direction, length pixels"""
    s = math.hypot(u, v)
    cr.set_source_rgb(*color); cr.set_line_width(width)
    if s < 0.03:
        cr.new_path(); cr.arc(x, y, 1.6, 0, 2 * math.pi); cr.fill(); return
    dx, dy = u / s, -v / s
    x0, y0, x1, y1 = x - dx * length / 2, y - dy * length / 2, x + dx * length / 2, y + dy * length / 2
    cr.move_to(x0, y0); cr.line_to(x1, y1); cr.stroke()
    for a in (150, -150):
        c, sn = math.cos(a * D2R), math.sin(a * D2R)
        cr.move_to(x1, y1); cr.line_to(x1 + head * (dx * c - dy * sn), y1 + head * (dx * sn + dy * c))
    cr.stroke()


def draw_tide(cr, x, y, w, h, st, n, now=None, bar=None, title=True):
    """a station's day: the curve (exact, every 10 minutes), the high and low waters marked and listed below, now,
    the 13 hours of a cycle as a bar (bar: (start, end) hours)"""
    tz, ev, _ = R.day(st, n)
    f = height_fn(st, n)
    H = [f(k / 6) for k in range(145)]
    lo, hi = math.floor(min(H) * 2) / 2, math.ceil(max(H) * 2) / 2
    hi = max(hi, lo + 0.5)
    top = y + (28 if title else 8); ch = h * 0.55; left = x + 34; cw = w - 44
    X = lambda t: left + cw * t / 24
    Y = lambda v: top + ch - (v - lo) / (hi - lo) * ch
    if title:
        text(cr, x, y + 16, st['name'], 15, True)
        text(cr, x + w, y + 16, '%s  UTC%+g  %s' % (datestr(n), tz, st['datum']), 11, color=SOFT, align='r')
    cr.set_line_width(1)
    v = lo
    while v <= hi + 1e-9:
        cr.set_source_rgb(*GRID); cr.move_to(left, Y(v)); cr.line_to(left + cw, Y(v)); cr.stroke()
        text(cr, left - 6, Y(v) + 4, ('%.1f' % v).rstrip('0').rstrip('.') if v % 1 else '%d' % v, 10, color=SOFT, align='r')
        v += 0.5
    for t in range(0, 25, 3):
        cr.set_source_rgb(*GRID); cr.move_to(X(t), top); cr.line_to(X(t), top + ch); cr.stroke()
        text(cr, X(t), top + ch + 14, '%02d' % t, 10, color=SOFT, align='c')
    if bar:
        cr.set_source_rgb(*ACCENT); cr.set_line_width(4)
        cr.move_to(X(max(0, bar[0])), top + ch + 22); cr.line_to(X(min(24, bar[1])), top + ch + 22); cr.stroke()
    cr.set_source_rgb(*INK); cr.set_line_width(2)
    for k, v in enumerate(H):
        (cr.move_to if k == 0 else cr.line_to)(X(k / 6), Y(v))
    cr.stroke()
    if now is not None:
        cr.set_source_rgb(*WARN); cr.set_line_width(1); cr.set_dash([3, 3])
        cr.move_to(X(now), top); cr.line_to(X(now), top + ch); cr.stroke(); cr.set_dash([])
    yy = top + ch + 44
    for t, hgt, k in ev:
        cr.set_source_rgb(*INK); cr.new_path(); cr.arc(X(t), Y(hgt), 3, 0, 2 * math.pi); cr.fill()
        text(cr, X(t), Y(hgt) + (-8 if k > 0 else 16), hhmm(t), 10, color=SOFT, align='c')
    for i, (t, hgt, k) in enumerate(ev):
        cx = x + 10 + (i % 3) * (w / 3); cy = yy + (i // 3) * 20
        text(cr, cx, cy, ('HW' if k > 0 else 'LW'), 12, True, ACCENT if k > 0 else SOFT)
        text(cr, cx + 30, cy, '%s   %.2f m' % (hhmm(t), hgt), 12)
    return ev


def draw_table(cr, x, y, w, rows, t, nowoff):
    """the 13 hours: HW, the clock time, an arrow, the set, the knots"""
    text(cr, x, y, 'HW', 11, True, SOFT); text(cr, x + 44, y, 'TIME', 11, True, SOFT)
    text(cr, x + w * 0.62, y, 'SET', 11, True, SOFT, 'r'); text(cr, x + w - 4, y, 'KN', 11, True, SOFT, 'r')
    rh = 22
    for k, (u, v) in enumerate(rows):
        yy = y + 22 + k * rh
        if nowoff is not None and int(nowoff + 6.5) == k:
            cr.set_source_rgb(0.90, 0.95, 1.0); cr.rectangle(x - 4, yy - 15, w + 4, rh); cr.fill()
        d, s = R.setkn(u, v)
        text(cr, x, yy, 'HW' if k == 6 else '%+d' % (k - 6), 12, k == 6)
        text(cr, x + 44, yy, hhmm(t + k - 6), 12)
        arrow(cr, x + w * 0.40, yy - 4, u, v, 14, ACCENT)
        text(cr, x + w * 0.62, yy, '%03.0f°' % d, 12, align='r')
        text(cr, x + w - 4, yy, '%.2f' % s, 12, s >= 0.75, align='r')


def draw_rose(cr, cx, cy, r, rows, nowuv):
    sp = [math.hypot(u, v) for u, v in rows] + ([math.hypot(*nowuv)] if nowuv else [])
    m = max(sp + [0.01])
    step = 0.25 if m <= 0.5 else 0.5 if m <= 2 else 1
    S = step * max(1, math.ceil(m / step - 1e-9))
    k = r / S
    cr.set_line_width(1)
    for i in range(1, int(round(S / step)) + 1):
        cr.set_source_rgb(*GRID); cr.new_path(); cr.arc(cx, cy, i * step * k, 0, 2 * math.pi); cr.stroke()
    cr.move_to(cx - r, cy); cr.line_to(cx + r, cy); cr.move_to(cx, cy - r); cr.line_to(cx, cy + r); cr.stroke()
    for lab, dx, dy in (('N', 0, -r - 6), ('S', 0, r + 16), ('E', r + 10, 4), ('W', -r - 10, 4)):
        text(cr, cx + dx, cy + dy, lab, 11, True, SOFT, 'c')
    text(cr, cx + r, cy + r + 16, 'rings %.2f kn' % step, 10, color=SOFT, align='r')
    cr.set_source_rgb(*ACCENT); cr.set_line_width(1.5)
    for i, (u, v) in enumerate(rows):
        (cr.move_to if i == 0 else cr.line_to)(cx + u * k, cy - v * k)
    cr.stroke()
    for i in (0, 6, 12):
        u, v = rows[i]
        cr.new_path(); cr.arc(cx + u * k, cy - v * k, 3, 0, 2 * math.pi); cr.fill()
        text(cr, cx + u * k + 6, cy - v * k - 4, ('-6', 'HW', '+6')[i // 6], 10, color=ACCENT)
    if nowuv:
        u, v = nowuv
        cr.set_source_rgb(*WARN); cr.set_line_width(3)
        cr.move_to(cx, cy); cr.line_to(cx + u * k, cy - v * k); cr.stroke()
        arrow(cr, cx + u * k, cy - v * k, u, v, 0.1, WARN, 3, 9)


def header(cr, w, st, cyc, note):
    t, h, rng, f, rows, off, nowuv = cyc
    text(cr, 16, 28, fmt_pos(st.lat, st.lon), 18, True)
    text(cr, w - 16, 28, datestr(st.n), 18, True, align='r')
    text(cr, 16, 50, '%s  HW %s   range %.2f m = %.2f x springs   %s' % (
        st.d.ref['name'], hhmm(t), rng, f, ('wind %03.0f° %.0f kn' % (st.wdir, st.wkn)) if st.wkn else 'no wind'),
        12, color=SOFT)
    if nowuv:
        d, s = R.setkn(*nowuv)
        text(cr, w - 16, 50, 'NOW  %.2f kn  %03.0f°' % (s, d), 13, True, WARN, 'r')
    if note:
        text(cr, 16, 68, note, 11, True, WARN)


def view_tide(cr, w, h, st):
    cr.set_source_rgb(*PAPER); cr.paint()
    s = st.station
    n0, h0 = st.d.now(s)
    draw_tide(cr, 16, 8, w - 32, h - 16, s, st.tday, h0 if n0 == st.tday else None)


def view_flow(cr, w, h, st, rose=True):
    cr.set_source_rgb(*PAPER); cr.paint()
    cyc = st.cycle()
    header(cr, w, st, cyc, ' · '.join(st.d.notes))
    t, _, _, _, rows, off, nowuv = cyc
    if rows is None:
        text(cr, 16, 120, 'No atlas here: outside the charts or on land.', 15, True, WARN)
        return cyc
    draw_table(cr, 16, 98, w * 0.42 if rose else w * 0.40, rows, t, off)
    if rose:
        draw_rose(cr, w * 0.73, 98 + (h - 98) / 2, min(w * 0.22, (h - 140) / 2), rows, nowuv)
    return cyc


def view_artf(cr, w, h, st):
    cyc = view_flow(cr, w, h, st, rose=False)
    t = cyc[0]
    s, dnm = st.nearest()
    n0, h0 = st.d.now(s)
    x0 = w * 0.46
    cr.set_source_rgb(*GRID); cr.set_line_width(1); cr.move_to(x0 - 10, 84); cr.line_to(x0 - 10, h - 10); cr.stroke()
    text(cr, x0, 98, '%s  (%.1f nm)' % (s['name'], dnm), 14, True)
    draw_tide(cr, x0, 104, w - x0 - 16, h - 120, s, st.n, h0 if n0 == st.n else None, bar=(t - 6, t + 6),
              title=False)


def view_map(cr, w, h, st):
    """the atlas at HW + st.hour (springs x the cycle's factor), the stations, the position"""
    cr.set_source_rgb(*PAPER); cr.paint()
    A = st.d.atlas
    t, hh, rng, f = R.flow_cycle(st.d.ref, st.n, st.m)
    lat0, lon0, step = A['lat0'], A['lon0'], A['step_min'] / 60
    lat1, lon1 = lat0 + (A['nlat'] - 1) * step, lon0 + (A['nlon'] - 1) * step
    cl = math.cos(math.radians((lat0 + lat1) / 2))
    top = 84
    sc = min((w * 0.6 - 60) / ((lon1 - lon0) * cl), (h - top - 24) / (lat1 - lat0))
    X = lambda lo: 40 + (lo - lon0) * cl * sc
    Y = lambda la: top + (lat1 - la) * sc
    st._map = (X, Y, sc, cl, lat1, lon0)
    text(cr, 16, 26, 'The atlas at HW %+d (%s), %s   (◀ ▶ or the arrow keys: the 13 charts)' % (
        st.hour, hhmm(t + st.hour), datestr(st.n)), 16, True)
    text(cr, 16, 46, 'spring speeds x %.2f; the wind is not added here; click to move the position' % f, 11, color=SOFT)
    if st.d.notes:
        text(cr, 16, 62, ' · '.join(st.d.notes), 11, True, WARN)
    cr.set_line_width(1)
    q = 0.25
    v = math.ceil(lat0 / q) * q
    while v <= lat1 + 1e-9:
        cr.set_source_rgb(*GRID); cr.move_to(X(lon0), Y(v)); cr.line_to(X(lon1), Y(v)); cr.stroke()
        text(cr, X(lon0) - 4, Y(v) + 4, '%d°%02d' % (int(v), round(v % 1 * 60)), 9, color=SOFT, align='r'); v += q
    v = math.ceil(lon0 / q) * q
    while v <= lon1 + 1e-9:
        cr.set_source_rgb(*GRID); cr.move_to(X(v), Y(lat0)); cr.line_to(X(v), Y(lat1)); cr.stroke()
        text(cr, X(v), Y(lat0) + 12, '%d°%02d' % (int(v), round(v % 1 * 60)), 9, color=SOFT, align='c'); v += q
    k = st.hour + 6
    # the gradient: the speed at every 3 pixels, the land white
    x0, x1, y0, y1 = X(lon0), X(lon1), Y(lat1), Y(lat0)
    B = 3
    yy = y0
    while yy < y1:
        la = lat1 - (yy + B / 2 - top) / sc
        xx = x0
        while xx < x1:
            lo = lon0 + (xx + B / 2 - 40) / (cl * sc)
            uv = field(A, k, f, la, lo)
            if uv is not None:
                cr.set_source_rgb(*band_colour(math.hypot(*uv)))
                cr.rectangle(xx, yy, B + 0.5, B + 0.5); cr.fill()
            xx += B
        yy += B
    cr.set_line_width(1)                               # the graticule over it
    v = math.ceil(lat0 / q) * q
    while v <= lat1 + 1e-9:
        cr.set_source_rgba(0, 0, 0, 0.12); cr.move_to(x0, Y(v)); cr.line_to(x1, Y(v)); cr.stroke(); v += q
    v = math.ceil(lon0 / q) * q
    while v <= lon1 + 1e-9:
        cr.set_source_rgba(0, 0, 0, 0.12); cr.move_to(X(v), y0); cr.line_to(X(v), y1); cr.stroke(); v += q
    # the arrows (as the charts: dark, longer and thicker when faster)
    for i in range(A['nlat']):
        for j in range(A['nlon']):
            c = A['cells'][i * A['nlon'] + j]
            if c is None:
                continue
            u, v = ((c[k][0] - 50) * A['q'] * f, (c[k][1] - 50) * A['q'] * f)
            s_ = math.hypot(u, v)
            arrow(cr, X(lon0 + j * step), Y(lat0 + i * step), u, v, 8 + 16 * min(s_, 1.5), (0.22, 0.20, 0.18),
                  1.2 + 1.6 * min(s_, 1.5), 4 + 2 * min(s_, 1.5))
    # the stations: a square and the name
    for p in st.d.ports:
        if lon0 - 0.3 < p['lon'] < lon1 + 0.3 and lat0 - 0.3 < p['lat'] < lat1 + 0.3:
            px, py = X(p['lon']), Y(p['lat'])
            cr.set_source_rgb(1, 1, 1); cr.rectangle(px - 4, py - 4, 8, 8); cr.fill()
            cr.set_source_rgb(*INK); cr.set_line_width(1.5); cr.rectangle(px - 4, py - 4, 8, 8); cr.stroke()
            text(cr, px + 7, py + 4, p['name'], 10, True, INK)
    # the position: a triangle
    px, py = X(st.lon), Y(st.lat)
    cr.new_path(); cr.move_to(px, py - 10); cr.line_to(px + 9, py + 6); cr.line_to(px - 9, py + 6); cr.close_path()
    cr.set_source_rgb(*WARN); cr.fill_preserve(); cr.set_source_rgb(1, 1, 1); cr.set_line_width(1.5); cr.stroke()
    # the legend
    lx, ly = X(lon1) + 60, h - 40
    text(cr, lx, ly - 10, 'knots', 10, True, SOFT)
    for i in range(160):
        cr.set_source_rgb(*band_colour(i / 160 * 1.75)); cr.rectangle(lx + i * 2, ly, 2.2, 12); cr.fill()
    for v_ in (0, 0.25, 0.5, 0.75, 1.0, 1.75):
        text(cr, lx + v_ / 1.75 * 320, ly + 26, ('%.2f' % v_).rstrip('0').rstrip('.') if v_ else '0', 9, color=SOFT,
             align='c')
    cyc = st.cycle()                                    # beside the map: the position's 13 hours
    x0 = X(lon1) + 60
    text(cr, x0, top + 4, fmt_pos(st.lat, st.lon), 13, True)
    if cyc[4]:
        draw_table(cr, x0, top + 30, w - x0 - 16, cyc[4], cyc[0], cyc[5])
    else:
        text(cr, x0, top + 30, 'no atlas here (outside or on land)', 12, True, WARN)


BANDS = [(0.0, (0.68, 0.84, 0.86)), (0.25, (0.70, 0.86, 0.80)), (0.5, (0.86, 0.90, 0.74)), (0.75, (0.95, 0.90, 0.55)),
         (1.0, (0.92, 0.74, 0.50)), (1.3, (0.88, 0.55, 0.52)), (1.75, (0.80, 0.38, 0.40))]


def band_colour(s):
    """the speed's colour: the atlas's bands (0.25 0.5 0.75 1.0 1.75 kn) as a smooth gradient"""
    if s <= BANDS[0][0]:
        return BANDS[0][1]
    for (a, ca), (b, cb) in zip(BANDS, BANDS[1:]):
        if s <= b:
            t = (s - a) / (b - a)
            return tuple(x + (y - x) * t for x, y in zip(ca, cb))
    return BANDS[-1][1]


def field(A, k, f, lat, lon):
    """the atlas's stream (u, v) at hour index k (0-12) x f at a position, bilinear over the sea nodes; None: land"""
    kk = 60.0 / A['step_min']
    fi, fj = (lat - A['lat0']) * kk, (lon - A['lon0']) * kk
    if not (0 <= fi <= A['nlat'] - 1 and 0 <= fj <= A['nlon'] - 1):
        return None
    i, j = min(int(fi), A['nlat'] - 2), min(int(fj), A['nlon'] - 2)
    a, b = fi - i, fj - j
    su = sv = sw = 0.0
    for di, dj, w in ((0, 0, (1 - a) * (1 - b)), (1, 0, a * (1 - b)), (0, 1, (1 - a) * b), (1, 1, a * b)):
        c = A['cells'][(i + di) * A['nlon'] + j + dj]
        if c is None or w <= 0:
            continue
        su += w * (c[k][0] - 50); sv += w * (c[k][1] - 50); sw += w
    if sw < 0.35:                                      # mostly land around: the coast
        return None
    return su / sw * A['q'] * f, sv / sw * A['q'] * f


VIEWS = [('Tide', view_tide), ('Flow', view_flow), ('ARTF', view_artf), ('Map', view_map)]


def export_png(folder, w=1000, h=680):
    import cairo
    st = State(Data())
    os.makedirs(folder, exist_ok=True)
    for name, fn in VIEWS:
        surf = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
        fn(cairo.Context(surf), w, h, st)
        surf.write_to_png(os.path.join(folder, 'app_%s.png' % name.lower()))
    print('written: %s' % ', '.join('app_%s.png' % n.lower() for n, _ in VIEWS))


# ======== the window ========
def main():
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk

    data = Data()
    st = State(data)

    class App(Gtk.Application):
        def do_activate(self):
            win = Gtk.ApplicationWindow(application=self, title='Tide 47')
            win.set_default_size(1100, 780)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            for m in ('top', 'bottom', 'start', 'end'):
                getattr(box, 'set_margin_' + m)(8)
            win.set_child(box)
            # the controls
            bar = Gtk.Box(spacing=6)
            box.append(bar)
            lat_e, lon_e = Gtk.Entry(width_chars=9), Gtk.Entry(width_chars=10)
            lat_e.set_text('%.2f' % (int(st.lat) + (st.lat % 1) * 0.6)); lon_e.set_text('%.2f' % (int(st.lon) + (st.lon % 1) * 0.6))
            wdir = Gtk.SpinButton.new_with_range(0, 359, 10); wkn = Gtk.SpinButton.new_with_range(0, 60, 5)
            for lab, wid in (('Lat (DD.MM)', lat_e), ('Lon', lon_e), ('Wind from', wdir), ('kn', wkn)):
                bar.append(Gtk.Label(label=lab)); bar.append(wid)
            names = Gtk.StringList()
            for p in data.ports:
                names.append(p['name'])
            stn = Gtk.DropDown(model=names)
            stn.set_selected(data.ports.index(st.station))
            bar.append(Gtk.Label(label='  Station')); bar.append(stn)
            nav = Gtk.Box(spacing=4)
            box.append(nav)
            buttons = [('◀ HW', lambda: st.step(-1)), ('HW ▶', lambda: st.step(1)), ('◀ day', lambda: st.day(-1)),
                       ('day ▶', lambda: st.day(1)), ('Now', st.to_now)]
            stack = Gtk.Notebook()
            areas = []

            def redraw():
                for a in areas:
                    a.queue_draw()
            for lab, fn in buttons:
                b = Gtk.Button(label=lab)
                b.connect('clicked', lambda _b, fn=fn: (fn(), setattr(st, 'tday', st.n), redraw()))
                nav.append(b)
            hlab = Gtk.Label(label='HW +0')

            def hour(d):
                st.hour = max(-6, min(6, st.hour + d))
                hlab.set_text('HW %+d' % st.hour)
                redraw()
            nav.append(Gtk.Label(label='     Map chart'))
            for lab, d in (('◀', -1), ('▶', 1)):
                b = Gtk.Button(label=lab)
                b.connect('clicked', lambda _b, d=d: hour(d))
                nav.append(b)
                if d < 0:
                    nav.append(hlab)
            keys = Gtk.EventControllerKey()

            def on_key(_c, keyval, _code, _state):
                from gi.repository import Gdk
                if keyval in (Gdk.KEY_Left, Gdk.KEY_Right) and stack.get_current_page() == 3:
                    hour(-1 if keyval == Gdk.KEY_Left else 1)
                    return True
                return False
            keys.connect('key-pressed', on_key)
            win.add_controller(keys)
            err = Gtk.Label(label='')
            nav.append(err)

            def apply(*_):
                try:
                    st.lat, st.lon = parse_dm(lat_e.get_text()), parse_dm(lon_e.get_text())
                    err.set_text('')
                except ValueError:
                    err.set_markup('<span foreground="red">  the position: DD.MM (28.24 = 28°24\')</span>')
                st.wdir, st.wkn = wdir.get_value(), wkn.get_value()
                redraw()
            for wdg in (lat_e, lon_e):
                wdg.connect('activate', apply)
            for wdg in (wdir, wkn):
                wdg.connect('value-changed', apply)
            stn.connect('notify::selected', lambda d, _p: (setattr(st, 'station', data.ports[d.get_selected()]),
                                                            redraw()))
            box.append(stack)
            stack.set_vexpand(True)
            for name, fn in VIEWS:
                a = Gtk.DrawingArea()
                a.set_draw_func(lambda area, cr, w, h, fn=fn: fn(cr, w, h, st))
                if name == 'Map':
                    click = Gtk.GestureClick()

                    def on_click(g, n, x, y):
                        if not hasattr(st, '_map'):
                            return
                        X, Y, sc, cl, lat1, lon0 = st._map
                        st.lon = lon0 + (x - 40) / (cl * sc); st.lat = lat1 - (y - 84) / sc
                        lat_e.set_text('%.2f' % (int(st.lat) + (st.lat % 1) * 0.6))
                        lon_e.set_text('%.2f' % (int(st.lon) + (st.lon % 1) * 0.6))
                        redraw()
                    click.connect('pressed', on_click)
                    a.add_controller(click)
                areas.append(a)
                stack.append_page(a, Gtk.Label(label=name))
            win.present()

    App(application_id='com.github.valdesvj.tide47').run([sys.argv[0]])


if __name__ == '__main__':
    if '--png' in sys.argv:
        export_png(sys.argv[sys.argv.index('--png') + 1])
    else:
        main()
