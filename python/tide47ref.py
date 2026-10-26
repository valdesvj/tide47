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

    python3 python/tide47ref.py [port] [yyyy-mm-dd]     the high and low waters of a day (the port: part of its name);
                                                        a stream station: its slacks and maxima (sday, below)
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
    # the seasonal sidebands (+- SA) of O1, Q1, MF, MTM and 4 SA: in the Aramco tables' residual (O1 + SA 1.7 cm)
    ('O1SA', (1, -1, 1, 0, 0, 0), 1, UO1, {'O1': 1}),
    ('O1SB', (1, -1, -1, 0, 0, 0), 1, UO1, {'O1': 1}),
    ('Q1SA', (1, -2, 1, 1, 0, 0), 1, UO1, {'O1': 1}),
    ('SA4',  (0, 0, 4, 0, 0, 0), 0, {}, {}),
    ('MFSA', (0, 2, 1, 0, 0, 0), 0, {'xi': -2}, {'Mf': 1}),
    ('MTSA', (0, 3, 1, -1, 0, 0), 0, {'xi': -2}, {'Mf': 1}),
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


# ---- the C47's day, step for step (LBL :DAY:, :HOURS:, :FIND:, :ROOT:, :CURVE:) ----
# v0.3 (speed): only the port's constituents (the non-zero ones: the selection matrix S on the C47), one exact
# evaluation an hour (COS and SIN of the same phases give the value, its first and second derivatives), the events
# from the cubic (Hermite) of the event function F between the hours, then one exact Newton step; the curve from
# the hourly values and slopes (Hermite). The v0.2 method (an exact sum at every curve point, four exact Newton steps)
# stays as day_exact / sday_exact: tests/test_tide47.py checks the two agree (seconds, millimetres).
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


def port_index(st):
    """The constituents a port carries (the C47's IX): the non-zero ones of hc (and hv), in CONS order (1-based)."""
    names = [k[0] for k in CONS]
    have = set(n for n, v in st['hc'].items() if v[0] > 0) | set(n for n, v in st.get('hv', {}).items() if v[0] > 0)
    return [i + 1 for i, n in enumerate(names) if n in have]


def comp(st, j0, hc, ix=None):
    """P (deg) and A AW AW2 of one component over the port's constituents (LBL :VEC:), and their speeds W (deg/h)."""
    ix = ix or port_index(st)
    W = speeds()
    vf = vector(j0)
    P, A, AW, AW2, Wk = [], [], [], [], []
    for i in ix:
        name = CONS[i - 1][0]
        vu, f = vf[i - 1]
        H, g = hc.get(name, (0.0, 0.0))
        a = f * (H + 1e-40)
        r = W[i - 1] * D2R
        P.append((vu - g) % 360); A.append(a); AW.append(a * r); AW2.append(a * r * r); Wk.append(W[i - 1])
    return P, A, AW, AW2, Wk


def evaluate(C, z0, t):
    """One component at the hour t (LBL :UV:): (value, first, second derivative)."""
    P, A, AW, AW2, Wk = C
    z = [(p + w * t) * D2R for p, w in zip(P, Wk)]
    c = [math.cos(x) for x in z]
    s_ = [math.sin(x) for x in z]
    return (z0 + sum(a * x for a, x in zip(A, c)), -sum(a * x for a, x in zip(AW, s_)),
            -sum(a * x for a, x in zip(AW2, c)))


def herm(f0, d0, f1, d1, s):
    """The cubic (Hermite) on [0, 1] through f0, f1 with slopes d0, d1 (an interval of 1 hour): (value, slope)."""
    s2, s3 = s * s, s * s * s
    v = (2 * s3 - 3 * s2 + 1) * f0 + (s3 - 2 * s2 + s) * d0 + (-2 * s3 + 3 * s2) * f1 + (s3 - s2) * d1
    dv = (6 * s2 - 6 * s) * f0 + (3 * s2 - 4 * s + 1) * d0 + (-6 * s2 + 6 * s) * f1 + (3 * s2 - 2 * s) * d1
    return v, dv


def _ff(u, v):
    """The event function F and F' from (u, u', u'') and (v, v', v''): tide F = h' (then v = 0 and F = u', F' = u'')
    is the same formula as the stream's g = u u' + v v' only for a stream; see engine()."""
    return u[0] * u[1] + v[0] * v[1], u[1] * u[1] + u[0] * u[2] + v[1] * v[1] + v[0] * v[2]


def engine(st, n, stream):
    """The day n at st, as the C47 does it: (tz, events [(t, value, set, kind)], curve 73, hourly rows)."""
    tz = st['tz'] + dst(st, n)
    j0 = n - 0.5 - tz / 24
    ix = port_index(st)
    E = comp(st, j0, st['hc'], ix)
    rot = stream and st.get('kind') == 'rot'
    N = comp(st, j0, st['hv'], ix) if rot else None
    z0, v0 = st['z0'], st.get('v0', 0.0)

    def uv(t):
        u = evaluate(E, z0, t)
        v = evaluate(N, v0, t) if rot else (0.0, 0.0, 0.0)
        if not stream:
            return u, v, u[1], u[2]                           # a tide: F = h', F' = h''
        F, Fp = _ff(u, v)
        return u, v, F, Fp
    HR = [uv(float(t)) for t in range(25)]
    ev = []
    most = 8 if stream else 6
    for k in range(1, 25):
        F0, D0 = HR[k - 1][2], HR[k - 1][3]
        F1, D1 = HR[k][2], HR[k][3]
        if F0 * F1 < 0 and len(ev) < most:
            s = F0 / (F0 - F1)
            for _ in range(3):
                p, dp = herm(F0, D0, F1, D1, s)
                s -= p / dp
                s = min(max(s, 0.0), 1.0)
            x0 = k - 1 + s
            u, v, F, Fp = uv(x0)
            x = min(max(x0 - F / Fp, k - 1.0), float(k))
            dx = x - x0
            uu, vv = u[0] + u[1] * dx, v[0] + v[1] * dx
            kind = 1 if Fp < 0 else -1
            if not stream:
                ev.append((x, uu, 0.0, kind))
            elif not rot:
                ev.append((x, uu, float(st['flood'] if uu >= 0 else st['ebb']), kind))
            else:
                ev.append((x, math.hypot(uu, vv), math.degrees(math.atan2(uu, vv)) % 360, kind))
    curve = []
    for k in range(73):
        t = k / 3
        i = min(int(t), 23)
        s = t - i
        a, b = HR[i], HR[i + 1]
        u = herm(a[0][0], a[0][1], b[0][0], b[0][1], s)[0]
        if rot:
            v = herm(a[1][0], a[1][1], b[1][0], b[1][1], s)[0]
            curve.append(math.hypot(u, v))
        else:
            curve.append(u)
    return tz, ev, curve, HR


def day(st, n):
    """The day n (JDN of the local date) at the station st: (tz, events [(t hours, height m, +1 HW / -1 LW)],
    the curve [the height every 20 minutes, 73 values]), as the C47 computes them."""
    tz, ev, curve, _ = engine(st, n, False)
    return tz, [(t, h, k) for t, h, _, k in ev], curve


def sday(st, n):
    """The day n at the stream station st: (tz, events [(t hours, value kn, set deg, +1 max / -1 min)], the curve
    [the value every 20 minutes, 73]): value = the signed speed along the flood axis (rect) or the speed (rot)."""
    tz, ev, curve, _ = engine(st, n, True)
    return tz, ev, curve


def stream_now(st, n, hour):
    """The value and set at the local hour of the day n (the C47's NOW: one exact evaluation)."""
    tz = st['tz'] + dst(st, n)
    j0 = n - 0.5 - tz / 24
    ix = port_index(st)
    u = evaluate(comp(st, j0, st['hc'], ix), st['z0'], hour)[0]
    if st['kind'] != 'rot':
        return u, (st['flood'] if u >= 0 else st['ebb'])
    v = evaluate(comp(st, j0, st['hv'], ix), st.get('v0', 0.0), hour)[0]
    return math.hypot(u, v), math.degrees(math.atan2(u, v)) % 360


# ---- v0.2, exact at every point (kept for the tests: the reference the faster engine is checked against) ----
def day_exact(st, n):
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


# ---- tidal streams (the C47's LBL :SEVENTS:, :UV:, :SREF:, :VAL:): a stream station st has kind 'rect' or 'rot'
#   'rect' (rectilinear, NOAA's and most current tables'): hc the constants of the speed along the flood direction
#          (knots, + flood, - ebb), z0 its mean; flood and ebb the directions (deg true, the set: where it goes)
#   'rot'  (rotary): hc the east component u, hv the north component v (knots), z0 and v0 their means
# The events are the turning points of the speed: g = d(s^2)/dt / 2 = u u' + v v' changes sign (the hourly signs, then
# four Newton steps g / g', g' = u'^2 + v'^2 + u u'' + v v''): a maximum (g' < 0; flood or ebb, or MAX) or a minimum
# (slack: s = 0 on a rectilinear stream, MIN on a rotary one). ----
def _vecs(st, j0, hc):
    """P (deg) and A AW AW2 of one component, as LBL :DAY: makes them."""
    W = speeds()
    P, A, AW, AW2 = [], [], [], []
    for (name, *_), (vu, f), w in zip(CONS, vector(j0), W):
        H, g = hc.get(name, (0.0, 0.0))
        a = f * (H + 1e-40)
        r = w * D2R
        P.append((vu - g) % 360); A.append(a); AW.append(a * r); AW2.append(a * r * r)
    return P, A, AW, AW2


def sday_exact(st, n):
    """The day n (JDN of the local date) at the stream station st: (tz, events [(t hours, value kn, set deg,
    +1 max / -1 min)], the curve [the value every 20 minutes, 73]): value = the signed speed along the flood axis
    (rect) or the speed (rot), as the C47 computes them."""
    tz = st['tz'] + dst(st, n)
    j0 = n - 0.5 - tz / 24
    W = speeds()
    rot = st['kind'] == 'rot'
    E = _vecs(st, j0, st['hc'])
    N = _vecs(st, j0, st['hv']) if rot else None

    def comp(V, m, t):
        P, A, AW, AW2 = V
        z = [(p + w * t) * D2R for p, w in zip(P, W)]
        c = [math.cos(x) for x in z]; s = [math.sin(x) for x in z]
        return (m + sum(a * x for a, x in zip(A, c)), -sum(a * x for a, x in zip(AW, s)),
                -sum(a * x for a, x in zip(AW2, c)))

    def uv(t):
        u = comp(E, st['z0'], t)
        v = comp(N, st['v0'], t) if rot else (0.0, 0.0, 0.0)
        return u, v

    def g(t):
        (u, u1, _), (v, v1, _) = uv(t)
        return u * u1 + v * v1

    def val(t):
        (u, *_), (v, *_) = uv(t)
        if not rot:
            return u, (st['flood'] if u >= 0 else st['ebb'])
        return math.hypot(u, v), math.degrees(math.atan2(u, v)) % 360
    ev = []
    g1 = g(0.0)
    for k in range(1, 25):
        g2 = g(float(k))
        if g1 * g2 < 0 and len(ev) < 8:
            lo, hi = k - 1.0, float(k)
            x = lo + g1 / (g1 - g2)
            for _ in range(4):
                (u, u1, u2), (v, v1, v2) = uv(x)
                G = u * u1 + v * v1
                Gp = u1 * u1 + v1 * v1 + u * u2 + v * v2
                x -= G / Gp
                x = min(max(x, lo), hi)
            s, d = val(x)
            ev.append((x, s, d, -1 if Gp > 0 else 1))
        g1 = g2
    curve = [val(k / 3)[0] for k in range(73)]
    return tz, ev, curve


def stream_now_exact(st, n, hour):
    """The value and set at the local hour of the day n (the C47's NOW)."""
    tz = st['tz'] + dst(st, n)
    j0 = n - 0.5 - tz / 24
    W = speeds()

    def one(hc, m):
        P, A, _, _ = _vecs(st, j0, hc)
        return m + sum(a * math.cos((p + w * hour) * D2R) for a, p, w in zip(A, P, W))
    u = one(st['hc'], st['z0'])
    if st['kind'] != 'rot':
        return u, (st['flood'] if u >= 0 else st['ebb'])
    v = one(st['hv'], st['v0'])
    return math.hypot(u, v), math.degrees(math.atan2(u, v)) % 360


# ---- FLOW47: a tidal stream atlas (charts HW-6 ... HW+6 of a reference station's High Water, spring speeds) at any
# position, as the C47 does it (LBL "FLOW47": :ATLAS:, :PICK:, :CYC:). fl: python/flow_private.py FLOW. ----
WFAC, WDEF = 0.025, 15.0          # the wind's surface current: 2.5 % of the wind speed, 15 deg to the right of downwind


def dm(x):
    """DD.MMm (degrees, minutes; - south / west) -> degrees."""
    a = abs(x)
    d = math.floor(a + 1e-12)
    return math.copysign(d + (a - d) * 100 / 60, x)


def flow_cell(fl, lat, lon):
    """The atlas at a position (degrees): 13 (u, v) spring values, bilinear between the four nodes around it (the
    land ones left out), or None outside the grid or on land."""
    k = 60.0 / fl['step_min']
    fi, fj = (lat - fl['lat0']) * k, (lon - fl['lon0']) * k
    if not (0 <= fi <= fl['nlat'] - 1 and 0 <= fj <= fl['nlon'] - 1):
        return None
    i, j = min(int(math.floor(fi)), fl['nlat'] - 2), min(int(math.floor(fj)), fl['nlon'] - 2)
    a, b = fi - i, fj - j
    FU, FV, sw = [0.0] * 13, [0.0] * 13, 0.0
    for di, dj, w in ((0, 0, (1 - a) * (1 - b)), (1, 0, a * (1 - b)), (0, 1, (1 - a) * b), (1, 1, a * b)):
        c = fl['cells'][(i + di) * fl['nlon'] + j + dj]
        if c is None or w <= 0:
            continue
        sw += w
        for h, (cu, cv) in enumerate(c):
            FU[h] += w * (cu - 50) * fl['q']; FV[h] += w * (cv - 50) * fl['q']
    if sw < 1e-9:
        return None
    return [x / sw for x in FU], [x / sw for x in FV]


def flow_spring(ref):
    """The mean spring range at the reference station: 2 (H M2 + H S2), H as the data program has it (0.1 mm)."""
    H = lambda n: int(round(ref['hc'].get(n, (0, 0))[0] * 1e4)) / 1e4
    return 2 * (H('M2') + H('S2'))


def flow_pick(ref, n, target):
    """The High Water of day n nearest the hour target (a High Water more than 6.2 h away: the next or previous
    day's): (n, the event's index in the day's list)."""
    ev = day(ref, n)[1]
    hw = [m for m, e in enumerate(ev) if e[2] > 0]
    if not hw:
        return flow_step(ref, n, -1, 1)
    if target - ev[hw[-1]][0] > 6.2:
        return flow_step(ref, n, hw[-1], 1)
    if ev[hw[0]][0] - target > 6.2:
        return flow_step(ref, n, hw[0], -1)
    m = min(hw, key=lambda m: abs(ev[m][0] - target))
    return n, m


def flow_step(ref, n, m, d):
    """The next (d = 1) or previous (d = -1) High Water after / before the event m of day n."""
    ev = day(ref, n)[1]
    hw = [k for k, e in enumerate(ev) if e[2] > 0 and (k > m if d > 0 else (m < 0 or k < m))]
    if hw:
        return n, (hw[0] if d > 0 else hw[-1])
    ev2 = day(ref, n + d)[1]
    hw2 = [k for k, e in enumerate(ev2) if e[2] > 0]
    return n + d, (hw2[0] if d > 0 else hw2[-1])


def flow_cycle(ref, n, m):
    """The High Water m of day n: (its hour, its height, the range: its height - the mean of the low waters next to
    it that day, the factor on the spring speeds: range / mean spring range (1 without a low water))."""
    ev = day(ref, n)[1]
    t, h = ev[m][0], ev[m][1]
    lows = [ev[k][1] for k in (m - 1, m + 1) if 0 <= k < len(ev) and ev[k][2] < 0]
    if not lows:
        return t, h, 0.0, 1.0
    rng = h - sum(lows) / len(lows)
    return t, h, rng, rng / flow_spring(ref)


def flow_rows(cell, f, wdir=0.0, wkn=0.0):
    """The 13 rows HW-6 ... HW+6: (u, v) = f x the atlas + the wind's current (WFAC x WKN, to WDIR + 180 + WDEF)."""
    wu = WFAC * wkn * math.sin(math.radians(wdir + 180 + WDEF))
    wv = WFAC * wkn * math.cos(math.radians(wdir + 180 + WDEF))
    FU, FV = cell
    return [(f * u + wu, f * v + wv) for u, v in zip(FU, FV)]


def flow_now(rows, off):
    """The stream at off hours from High Water (-6 ... 6): straight between the hours."""
    k = min(int(math.floor(off + 6)), 11)
    s = off + 6 - k
    (u0, v0), (u1, v1) = rows[k], rows[k + 1]
    return u0 + (u1 - u0) * s, v0 + (v1 - v0) * s


def art_nearest(ports, lat, lon):
    """ARTF47's tide station: the port nearest the position (degrees): (its number from 1, the distance in nm: 60 x the
    hypotenuse of the latitude difference and the longitude difference x cos latitude; the first of equals)."""
    best, k = 1e9, 1
    for i, p in enumerate(ports, 1):
        d = 60 * math.hypot(p['lat'] - lat, (p['lon'] - lon) * math.cos(math.radians(lat)))
        if d < best:
            best, k = d, i
    return k, best


def setkn(u, v):
    return math.degrees(math.atan2(u, v)) % 360, math.hypot(u, v)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import stations, streams
    regs = stations.REGIONS + streams.REGIONS
    for mod in ('stations_private', 'streams_private'):
        try:
            regs = regs + __import__(mod).REGIONS
        except ImportError:
            pass
    want = sys.argv[1] if len(sys.argv) > 1 else 'Mina Salman'
    y, m, d = map(int, (sys.argv[2] if len(sys.argv) > 2 else '2026-10-25').split('-'))
    st = [p for _, _, _, ports in regs for p in ports if want.lower() in p['name'].lower()][0]
    if st.get('kind') in ('rect', 'rot'):
        tz, ev, _ = sday(st, jdn(y, m, d))
        print('%s  %04d-%02d-%02d  UTC%+g  %s' % (st['name'], y, m, d, tz, st['datum']))
        for t, v, s, k in ev:
            mi = int(t * 60 + 0.5)
            kind = ('SLACK' if k < 0 else 'FLOOD' if v > 0 else 'EBB') if st['kind'] == 'rect' else ('MIN' if k < 0
                                                                                                   else 'MAX')
            print('  %-5s %02d:%02d  %5.2f kn  %s' % (kind, mi // 60, mi % 60, abs(v),
                                                    '' if kind == 'SLACK' else '%03.0f deg' % s))
        sys.exit(0)
    tz, ev, _ = day(st, jdn(y, m, d))
    print('%s  %04d-%02d-%02d  UTC%+g  heights above %s' % (st['name'], y, m, d, tz, st['datum']))
    for t, h, k in ev:
        mi = int(t * 60 + 0.5)
        print('  %-4s %02d:%02d  %6.2f m' % ('HIGH' if k > 0 else 'LOW', mi // 60, mi % 60, h))
