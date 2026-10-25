#!/usr/bin/env python3
"""tide47ref.py - the tide engine of Tide 47 in Python: the same method as the C47 program, step for step.

The harmonic method of NOAA and the Admiralty (Schureman, "Manual of Harmonic Analysis and Prediction of Tides",
US Coast and Geodetic Survey Special Publication 98, 1958):

    h(t) = Z0 + sum_k f_k H_k cos(V_k(t) + u_k - g_k)

  H_k, g_k   the station's harmonic constants: amplitude (m) and phase lag on Greenwich (degrees, UT);
  V_k(t)     the equilibrium argument: an integer combination (the Doodson numbers) of the astronomical angles
             tau (mean lunar time), s (Moon), h (Sun), p (lunar perigee), N' = -N (the Moon's node), p1 (solar
             perigee), plus a multiple of 90 degrees;  V = D a  (D the Doodson matrix, a the angles);
  f_k, u_k   the nodal corrections (the 18.6-year cycle of the Moon's node): u_k a combination of xi, nu, nu',
             2nu'', Q, R (u = U b), f_k a product of eleven basic factors (log f = E log fb).

On the C47 the same three matrix products (V = D a, u = U b, log f = E log fb) give the vectors once per block, and a
block of times is one COS of a matrix:  heights = A' COS(W T' + P 1') with W the speeds, T the times (hours),
P = V + u - g at the block start, A = f H.  High and low waters: Newton on h'(t) = 0 with SIN and DOT.

    python3 python/tide47ref.py [port] [yyyy-mm-dd]     the high and low waters of a day (the port: part of its name)
"""
import math, os

D2R = math.pi / 180

# ---- the constituents: name, Doodson numbers (tau, s, h, p, N', p1), the phase in units of 90 degrees, u (a dict of
# the basics xi nu nup nupp2 Q R), f (a dict of the basic factors and their powers). The first 37 in NOAA's order
# (CO-OPS: M2 S2 N2 K1 M4 O1 M6 MK3 S4 MN4 NU2 S6 MU2 2N2 OO1 LAM2 S1 M1 J1 MM SSA SA MSF MF RHO Q1 T2 R2 2Q1 P1 2SM2 M3
# L2 2MK3 K2 M8 MS4), then the ones TICON adds. ----
UM2 = {'xi': 2, 'nu': -2}
UO1 = {'xi': 2, 'nu': -1}
CONS = [
    ('M2',   (2, 0, 0, 0, 0, 0), 0, UM2, {'M2': 1}),
    ('S2',   (2, 2, -2, 0, 0, 0), 0, {}, {}),
    ('N2',   (2, -1, 0, 1, 0, 0), 0, UM2, {'M2': 1}),
    ('K1',   (1, 1, 0, 0, 0, 0), -1, {'nup': -1}, {'K1': 1}),
    ('M4',   (4, 0, 0, 0, 0, 0), 0, {'xi': 4, 'nu': -4}, {'M2': 2}),
    ('O1',   (1, -1, 0, 0, 0, 0), 1, UO1, {'O1': 1}),
    ('M6',   (6, 0, 0, 0, 0, 0), 0, {'xi': 6, 'nu': -6}, {'M2': 3}),
    ('MK3',  (3, 1, 0, 0, 0, 0), -1, {'xi': 2, 'nu': -2, 'nup': -1}, {'M2': 1, 'K1': 1}),
    ('S4',   (4, 4, -4, 0, 0, 0), 0, {}, {}),
    ('MN4',  (4, -1, 0, 1, 0, 0), 0, {'xi': 4, 'nu': -4}, {'M2': 2}),
    ('NU2',  (2, -1, 2, -1, 0, 0), 0, UM2, {'M2': 1}),
    ('S6',   (6, 6, -6, 0, 0, 0), 0, {}, {}),
    ('MU2',  (2, -2, 2, 0, 0, 0), 0, UM2, {'M2': 1}),
    ('2N2',  (2, -2, 0, 2, 0, 0), 0, UM2, {'M2': 1}),
    ('OO1',  (1, 3, 0, 0, 0, 0), -1, {'xi': -2, 'nu': -1}, {'OO1': 1}),
    ('LAM2', (2, 1, -2, 1, 0, 0), 2, UM2, {'M2': 1}),
    ('S1',   (1, 1, -1, 0, 0, 0), 0, {}, {}),
    ('M1',   (1, 0, 0, 1, 0, 0), -1, {'xi': 1, 'nu': -1, 'Q': 1, 'p': -1}, {'M1': 1}),
    ('J1',   (1, 2, 0, -1, 0, 0), -1, {'nu': -1}, {'J1': 1}),
    ('MM',   (0, 1, 0, -1, 0, 0), 0, {}, {'Mm': 1}),
    ('SSA',  (0, 0, 2, 0, 0, 0), 0, {}, {}),
    ('SA',   (0, 0, 1, 0, 0, 0), 0, {}, {}),
    ('MSF',  (0, 2, -2, 0, 0, 0), 0, {'xi': -2, 'nu': 2}, {'M2': 1}),
    ('MF',   (0, 2, 0, 0, 0, 0), 0, {'xi': -2}, {'Mf': 1}),
    ('RHO1', (1, -2, 2, -1, 0, 0), 1, UO1, {'O1': 1}),
    ('Q1',   (1, -2, 0, 1, 0, 0), 1, UO1, {'O1': 1}),
    ('T2',   (2, 2, -3, 0, 0, 1), 0, {}, {}),
    ('R2',   (2, 2, -1, 0, 0, -1), 2, {}, {}),
    ('2Q1',  (1, -3, 0, 2, 0, 0), 1, UO1, {'O1': 1}),
    ('P1',   (1, 1, -2, 0, 0, 0), 1, {}, {}),
    ('2SM2', (2, 4, -4, 0, 0, 0), 0, {'xi': -2, 'nu': 2}, {'M2': 1}),
    ('M3',   (3, 0, 0, 0, 0, 0), 0, {'xi': 3, 'nu': -3}, {'M2': 1.5}),
    ('L2',   (2, 1, 0, -1, 0, 0), 2, {'xi': 2, 'nu': -2, 'R': -1}, {'L2': 1}),
    ('2MK3', (3, -1, 0, 0, 0, 0), 1, {'xi': 4, 'nu': -4, 'nup': 1}, {'M2': 2, 'K1': 1}),
    ('K2',   (2, 2, 0, 0, 0, 0), 0, {'nupp2': -1}, {'K2': 1}),
    ('M8',   (8, 0, 0, 0, 0, 0), 0, {'xi': 8, 'nu': -8}, {'M2': 4}),
    ('MS4',  (4, 2, -2, 0, 0, 0), 0, UM2, {'M2': 1}),
    # TICON's others (above 0.3 cm in the Gulf)
    ('EPS2', (2, -3, 2, 1, 0, 0), 0, UM2, {'M2': 1}),
    ('MKS2', (2, 0, 2, 0, 0, 0), 0, {'xi': 2, 'nu': -2, 'nupp2': -1}, {'M2': 1, 'K2': 1}),
    ('MA2',  (2, 0, -1, 0, 0, 0), 0, UM2, {'M2': 1}),
    ('MB2',  (2, 0, 1, 0, 0, 0), 0, UM2, {'M2': 1}),
    ('MTM',  (0, 3, 0, -1, 0, 0), 0, {'xi': -2}, {'Mf': 1}),
    ('MSQM', (0, 4, -2, 0, 0, 0), 0, {'xi': -2}, {'Mf': 1}),
    ('N4',   (4, -2, 0, 2, 0, 0), 0, {'xi': 4, 'nu': -4}, {'M2': 2}),
    ('S3',   (3, 3, -3, 0, 0, 0), 0, {}, {}),
    # nine more for the Aramco tables (their year of hourly heights: the terannual tide, the satellites of O1 and K1,
    # the seasonal sideband M2 - SSA (M2 + SSA is MKS2); Foreman's speeds; the nodal factors of their parents)
    ('STA',  (0, 0, 3, 0, 0, -1), 0, {}, {}),
    ('MSM',  (0, 1, -2, 1, 0, 0), 0, {}, {'Mm': 1}),
    ('SIG1', (1, -3, 2, 0, 0, 0), 1, UO1, {'O1': 1}),
    ('TAU1', (1, -1, 2, 0, 0, 0), 1, UO1, {'O1': 1}),
    ('PSI1', (1, 1, 1, 0, 0, -1), -1, {}, {}),
    ('PHI1', (1, 1, 2, 0, 0, 0), -1, {}, {}),
    ('SO1',  (1, 3, -2, 0, 0, 0), -1, {'xi': -2, 'nu': 1}, {'O1': 1}),
    ('MSSA2', (2, 0, -2, 0, 0, 0), 0, UM2, {'M2': 1}),
    ('MSN2', (2, 3, -2, -1, 0, 0), 0, {}, {'M2': 2}),
]
NOAA37 = 37                                                        # the first 37: NOAA's set
UB = ['xi', 'nu', 'nup', 'nupp2', 'Q', 'R', 'p']                   # the columns of U (p: NOAA's M1, below)
FB = ['Mm', 'Mf', 'O1', 'K1', 'J1', 'OO1', 'M2', 'K2', 'L2', 'M1']  # the columns of E
SPEED = (14.4920521, 0.5490165, 0.0410686, 0.0046418, 0.0022064, 0.0000020)   # deg / hour: tau s h p N' p1

OMEGA, INCL = 23.452, 5.145                                       # Schureman's obliquity and lunar inclination
_w, _i = OMEGA * D2R, INCL * D2R
# the constants of the nodal formulas, written into the C47 program by the build ({NAME} in the source)
K = dict(
    CICW=math.cos(_i) * math.cos(_w), SISW=math.sin(_i) * math.sin(_w),                   # cos I = CICW - SISW cos N
    K1=math.cos((_w - _i) / 2) / math.cos((_w + _i) / 2), K2=math.sin((_w - _i) / 2) / math.sin((_w + _i) / 2),
    DMM=(2 / 3 - math.sin(_w) ** 2) * (1 - 1.5 * math.sin(_i) ** 2),                    # eq. 73 (the mean values)
    DMF=math.sin(_w) ** 2 * math.cos(_i / 2) ** 4,                                         # eq. 74
    DO1=math.sin(_w) * math.cos(_w / 2) ** 2 * math.cos(_i / 2) ** 4,                      # eq. 75
    DJ1=math.sin(2 * _w) * (1 - 1.5 * math.sin(_i) ** 2),                                  # eq. 76
    DOO1=math.sin(_w) * math.sin(_w / 2) ** 2 * math.cos(_i / 2) ** 4,                     # eq. 77
    DM2=math.cos(_w / 2) ** 4 * math.cos(_i / 2) ** 4,                                     # eq. 78
    DK1=0.5305, DK2=0.1151)                                                                # eqs. 227, 235


def jd(y, m, d, hour=0.0):
    """The Julian Day (Gregorian calendar, UT)."""
    if m <= 2:
        y, m = y - 1, m + 12
    a = y // 100
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + 2 - a + a // 4 - 1524.5 + hour / 24


def speeds():
    return [sum(c * w for c, w in zip(dd, SPEED)) for _, dd, *_ in CONS]


def astro(j):
    """The astronomical angles at the Julian Day j (UT), degrees: tau s h p N' p1 (Meeus, as NOAA uses them)."""
    T = (j - 2451545.0) / 36525
    s = 218.3164477 + 481267.88123421 * T - 0.0015786 * T * T
    h = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    p = 83.3532465 + 4069.0137287 * T - 0.0103200 * T * T
    N = 125.04452 - 1934.136261 * T + 0.0020708 * T * T
    p1 = 282.93734 + 1.71946 * T + 0.00045688 * T * T
    ut = (j + 0.5) % 1 * 360                                    # 15 deg x the hours of UT: the mean sun from midnight
    tau = ut + 180 + h - s                                       # T = the mean sun's hour angle
    return [x % 360 for x in (tau, s, h, p, -N, p1)], N % 360


def basics(j):
    """The u basics (deg: xi nu nu' 2nu'' Q R p) and f basics (Mm Mf O1 K1 J1 OO1 M2 K2 L2 M1) at the Julian Day j:
    Schureman's formulas, as the C47's LBL :ASTRO: (the half-angle forms of nu and xi with ->POL there)."""
    a, N = astro(j)
    n = N * D2R
    I = math.acos(K['CICW'] - K['SISW'] * math.cos(n))
    A = math.atan2(K['K1'] * math.sin(n / 2), math.cos(n / 2))       # atan(K1 tan N/2), on the branch of N/2
    B = math.atan2(K['K2'] * math.sin(n / 2), math.cos(n / 2))
    nu, xi = A - B, n - A - B
    s2I, sI, cI = math.sin(2 * I), math.sin(I), math.cos(I)
    nup = math.atan2(s2I * math.sin(nu), s2I * math.cos(nu) + 0.3347)                           # eq. 224
    nupp2 = math.atan2(sI ** 2 * math.sin(2 * nu), sI ** 2 * math.cos(2 * nu) + 0.0727)         # eq. 232
    P = a[3] * D2R - xi                                                                          # P = p - xi
    f = {}
    f['Mm'] = (2 / 3 - sI ** 2) / K['DMM']
    f['Mf'] = sI ** 2 / K['DMF']
    f['O1'] = sI * math.cos(I / 2) ** 2 / K['DO1']
    f['J1'] = s2I / K['DJ1']
    f['OO1'] = sI * math.sin(I / 2) ** 2 / K['DOO1']
    f['M2'] = math.cos(I / 2) ** 4 / K['DM2']
    f['K1'] = math.sqrt(0.2523 * s2I ** 2 + 0.1689 * s2I * math.cos(nu) + 0.0283) / K['DK1']
    f['K2'] = math.sqrt(0.2533 * sI ** 4 + 0.0367 * sI ** 2 * math.cos(2 * nu) + 0.0013) / K['DK2']
    t2 = math.tan(I / 2) ** 2
    f['L2'] = f['M2'] * math.sqrt(1 - 12 * t2 * math.cos(2 * P) + 36 * t2 * t2)                  # eqs. 213, 215
    R = math.atan2(math.sin(2 * P), 1 / (6 * t2) - math.cos(2 * P))                             # eq. 214
    c2 = math.cos(I / 2) ** 2
    f['M1'] = f['O1'] * math.sqrt(0.25 + 1.5 * cI / c2 * math.cos(2 * P) + 2.25 * cI * cI / (c2 * c2))  # 197, 207
    Q = math.atan2((5 * cI - 1) * math.sin(P), (7 * cI + 1) * math.cos(P))                      # eq. 203
    u = {k: v / D2R for k, v in dict(xi=xi, nu=nu, nup=nup, nupp2=nupp2, Q=Q, R=R).items()}
    u['p'] = a[3]                     # NOAA's M1: tau + p at the speed, V + u = tau - 90 + xi - nu + Q (XTide's tables)
    return a, u, f


def vector(j):
    """V + u (deg, 0-360) and f of every constituent at the Julian Day j: the three matrix products of the C47."""
    a, ub, fb = basics(j)
    out = []
    for name, dd, k90, uc, fc in CONS:
        V = sum(c * x for c, x in zip(dd, a)) + 90 * k90
        u = sum(uc.get(b, 0) * ub[b] for b in UB)
        f = math.exp(sum(fc.get(b, 0) * math.log(fb[b]) for b in FB))
        out.append(((V + u) % 360, f))
    return out


# ---- the C47's day, step for step (LBL :DAY:, :EVENTS:, :REFINE:, :CURVE:) ----
def jdn(y, m, d):
    a = (14 - m) // 12; yy = y + 4800 - a; mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def cal(n):
    """The JDN n -> (y, m, d)."""
    a = n + 32044; b = (4 * a + 3) // 146097; c = a - 146097 * b // 4
    d = (4 * c + 3) // 1461; e = c - 1461 * d // 4; m = (5 * e + 2) // 153
    return 100 * b + d - 4800 + m // 10, m + 3 - 12 * (m // 10), e - (153 * m + 2) // 5 + 1


def dst(st, n):
    """1 when the day n is in US daylight time (second Sunday of March to the first Sunday of November)."""
    if st['dst'] != 'US':
        return 0
    y = cal(n)[0]
    m1, n1 = jdn(y, 3, 1), jdn(y, 11, 1)
    start = m1 + (7 - (m1 + 1) % 7) % 7 + 7
    end = n1 + (7 - (n1 + 1) % 7) % 7
    return 1 if start <= n < end else 0


def day(st, n):
    """The day n (JDN of the local date) at the station st: (tz, events [(t hours, height m, +1 HW / -1 LW)],
    the curve [the height every 20 minutes, 73 values]), as the C47 computes them."""
    tz = st['tz'] + dst(st, n)
    j0 = n - 0.5 - tz / 24
    names = [c[0] for c in CONS]
    W = speeds()
    vf = vector(j0)
    P, A, AW, AW2 = [], [], [], []
    for (name, *_), (vu, f), w in zip(CONS, vf, W):
        H, g = st['hc'].get(name, (0.0, 0.0))
        a = f * (H + 1e-40)
        r = w * D2R
        P.append((vu - g) % 360); A.append(a); AW.append(a * r); AW2.append(a * r * r)
    def dot(v, fn, t):
        return sum(x * fn((p + w * t) * D2R) for x, p, w in zip(v, P, W))
    def der(t):
        return dot(AW, math.sin, t)                           # = -h'(t)
    ev = []
    d1 = der(0.0)
    for k in range(1, 25):
        d2 = der(float(k))
        if d1 * d2 < 0 and len(ev) < 6:
            lo, hi = k - 1.0, float(k)
            x = lo + d1 / (d1 - d2)
            for _ in range(4):
                S = dot(AW, math.sin, x); C2 = dot(AW2, math.cos, x)
                x -= S / C2
                x = min(max(x, lo), hi)
            ev.append((x, st['z0'] + dot(A, math.cos, x), 1 if C2 > 0 else -1))
        d1 = d2
    curve = [st['z0'] + dot(A, math.cos, k / 3) for k in range(73)]
    return tz, ev, curve


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import stations
    want = sys.argv[1] if len(sys.argv) > 1 else 'Mina Salman'
    y, m, d = map(int, (sys.argv[2] if len(sys.argv) > 2 else '2026-10-25').split('-'))
    st = [p for _, _, _, ports in stations.REGIONS for p in ports if want.lower() in p['name'].lower()][0]
    tz, ev, _ = day(st, jdn(y, m, d))
    print('%s  %04d-%02d-%02d  UTC%+g  heights above %s' % (st['name'], y, m, d, tz, st['datum']))
    for t, h, k in ev:
        mi = int(t * 60 + 0.5)
        print('  %-4s %02d:%02d  %6.2f m' % ('HIGH' if k > 0 else 'LOW', mi // 60, mi % 60, h))
