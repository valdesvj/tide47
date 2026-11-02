// tide47.js - the Tide 47 engine in JavaScript: the harmonic method of python/tide47ref.py (Schureman, NOAA), exact.
//
//   h(t) = Z0 + sum f H cos(V + u - g + w t)
//
// The astronomy (astro, basics, vector) is the twin's line for line; the constituents and constants come from
// data/cons.js (written from tide47ref.py). A day is evaluated exactly: the event function (h', or for a stream
// g = u u' + v v') every 5 minutes, each sign change bisected to well under a second, the curve every 5 minutes.
// tests/test_web.py checks it against the Python twin. Works in a browser (file://) and in node.
(function (root) {
  'use strict';
  const D2R = Math.PI / 180;
  const C = root.T47CONS;
  const mod = (x, m) => ((x % m) + m) % m;

  function jdn(y, m, d) {
    const a = Math.floor((14 - m) / 12), yy = y + 4800 - a, mm = m + 12 * a - 3;
    return d + Math.floor((153 * mm + 2) / 5) + 365 * yy + Math.floor(yy / 4) - Math.floor(yy / 100) +
      Math.floor(yy / 400) - 32045;
  }

  function cal(n) {
    const a = n + 32044, b = Math.floor((4 * a + 3) / 146097), c = a - Math.floor(146097 * b / 4);
    const d = Math.floor((4 * c + 3) / 1461), e = c - Math.floor(1461 * d / 4), m = Math.floor((5 * e + 2) / 153);
    return [100 * b + d - 4800 + Math.floor(m / 10), m + 3 - 12 * Math.floor(m / 10),
      e - Math.floor((153 * m + 2) / 5) + 1];
  }

  // 1 when the day n is in US daylight time (second Sunday of March to the first Sunday of November)
  function dst(st, n) {
    if (st.dst !== 'US') return 0;
    const y = cal(n)[0], m1 = jdn(y, 3, 1), n1 = jdn(y, 11, 1);
    const start = m1 + mod(7 - mod(m1 + 1, 7), 7) + 7, end = n1 + mod(7 - mod(n1 + 1, 7), 7);
    return start <= n && n < end ? 1 : 0;
  }

  // the astronomical angles at the Julian Day j (UT), degrees: tau s h p N' p1, and N
  function astro(j) {
    const T = (j - 2451545.0) / 36525;
    const s = 218.3164477 + 481267.88123421 * T - 0.0015786 * T * T;
    const h = 280.46646 + 36000.76983 * T + 0.0003032 * T * T;
    const p = 83.3532465 + 4069.0137287 * T - 0.0103200 * T * T;
    const N = 125.04452 - 1934.136261 * T + 0.0020708 * T * T;
    const p1 = 282.93734 + 1.71946 * T + 0.00045688 * T * T;
    const ut = mod(j + 0.5, 1) * 360;
    const tau = ut + 180 + h - s;
    return [[tau, s, h, p, -N, p1].map(x => mod(x, 360)), mod(N, 360)];
  }

  // the u basics (deg) and f basics at the Julian Day j (Schureman)
  function basics(j) {
    const K = C.K;
    const [a, N] = astro(j);
    const n = N * D2R;
    const I = Math.acos(K.CICW - K.SISW * Math.cos(n));
    const A = Math.atan2(K.K1 * Math.sin(n / 2), Math.cos(n / 2));
    const B = Math.atan2(K.K2 * Math.sin(n / 2), Math.cos(n / 2));
    const nu = A - B, xi = n - A - B;
    const s2I = Math.sin(2 * I), sI = Math.sin(I), cI = Math.cos(I);
    const nup = Math.atan2(s2I * Math.sin(nu), s2I * Math.cos(nu) + 0.3347);
    const nupp2 = Math.atan2(sI ** 2 * Math.sin(2 * nu), sI ** 2 * Math.cos(2 * nu) + 0.0727);
    const P = a[3] * D2R - xi;
    const f = {};
    f.Mm = (2 / 3 - sI ** 2) / K.DMM;
    f.Mf = sI ** 2 / K.DMF;
    f.O1 = sI * Math.cos(I / 2) ** 2 / K.DO1;
    f.J1 = s2I / K.DJ1;
    f.OO1 = sI * Math.sin(I / 2) ** 2 / K.DOO1;
    f.M2 = Math.cos(I / 2) ** 4 / K.DM2;
    f.K1 = Math.sqrt(0.2523 * s2I ** 2 + 0.1689 * s2I * Math.cos(nu) + 0.0283) / K.DK1;
    f.K2 = Math.sqrt(0.2533 * sI ** 4 + 0.0367 * sI ** 2 * Math.cos(2 * nu) + 0.0013) / K.DK2;
    const t2 = Math.tan(I / 2) ** 2;
    f.L2 = f.M2 * Math.sqrt(1 - 12 * t2 * Math.cos(2 * P) + 36 * t2 * t2);
    const R = Math.atan2(Math.sin(2 * P), 1 / (6 * t2) - Math.cos(2 * P));
    const c2 = Math.cos(I / 2) ** 2;
    f.M1 = f.O1 * Math.sqrt(0.25 + 1.5 * cI / c2 * Math.cos(2 * P) + 2.25 * cI * cI / (c2 * c2));
    const Q = Math.atan2((5 * cI - 1) * Math.sin(P), (7 * cI + 1) * Math.cos(P));
    const u = { xi: xi / D2R, nu: nu / D2R, nup: nup / D2R, nupp2: nupp2 / D2R, Q: Q / D2R, R: R / D2R, p: a[3] };
    return [a, u, f];
  }

  // V + u (deg) and f of every constituent at the Julian Day j
  function vector(j) {
    const [a, ub, fb] = basics(j);
    return C.cons.map(([name, dd, k90, uc, fc]) => {
      let V = 90 * k90;
      for (let i = 0; i < 6; i++) V += dd[i] * a[i];
      let u = 0, lf = 0;
      for (const b of C.UB) u += (uc[b] || 0) * ub[b];
      for (const b of C.FB) if (fc[b]) lf += fc[b] * Math.log(fb[b]);
      return [mod(V + u, 360), Math.exp(lf)];
    });
  }

  const SPEEDS = C.cons.map(([, dd]) => dd.reduce((s, c, i) => s + c * C.speed[i], 0));

  // one component (hc or hv) of a station at the start j0 of its day: phases P (deg), amplitudes A, speeds W (deg/h)
  function comp(hc, vf) {
    const P = [], A = [], W = [];
    C.cons.forEach(([name], i) => {
      const k = hc[name];
      if (!k || !(k[0] > 0)) return;
      P.push(mod(vf[i][0] - k[1], 360)); A.push(vf[i][1] * k[0]); W.push(SPEEDS[i]);
    });
    return { P, A, W };
  }

  // the value and its slope (per hour) at the hour t
  function evalc(c, z0, t) {
    let v = z0, d = 0;
    for (let i = 0; i < c.P.length; i++) {
      const z = (c.P[i] + c.W[i] * t) * D2R;
      v += c.A[i] * Math.cos(z);
      d -= c.A[i] * c.W[i] * D2R * Math.sin(z);
    }
    return [v, d];
  }

  // the station's day n (JDN of the local date): {tz, events: [{t, value, set, kind}], curve: [[t, value]], fn}
  //   a tide: value = height (m), kind 1 high water, -1 low water
  //   a stream: value = signed speed along the flood axis (rect) or the speed (rot), set (deg), kind 1 maximum, -1 minimum
  function day(st, n, step) {
    step = step || 5 / 60;
    const stream = !!st.kind;
    const rot = st.kind === 'rot';
    const tz = st.tz + dst(st, n);
    const j0 = n - 0.5 - tz / 24;
    const vf = vector(j0);
    const E = comp(st.hc, vf);
    const N = rot ? comp(st.hv || {}, vf) : null;
    const z0 = st.z0 || 0, v0 = st.v0 || 0;
    const uv = t => [evalc(E, z0, t), rot ? evalc(N, v0, t) : [0, 0]];
    const F = t => {
      const [u, v] = uv(t);
      return stream ? u[0] * u[1] + v[0] * v[1] : u[1];
    };
    const value = t => {
      const [u, v] = uv(t);
      if (!stream) return { value: u[0], set: null };
      if (!rot) return { value: u[0], set: u[0] >= 0 ? st.flood : st.ebb };
      return { value: Math.hypot(u[0], v[0]), set: mod(Math.atan2(u[0], v[0]) / D2R, 360) };
    };
    const events = [];
    const steps = Math.round(24 / step);
    let t0 = 0, f0 = F(0);
    for (let k = 1; k <= steps; k++) {
      const t1 = k * step, f1 = F(t1);
      if (f0 * f1 < 0) {
        let a = t0, b = t1, fa = f0;
        for (let i = 0; i < 40; i++) {
          const m = (a + b) / 2, fm = F(m);
          if (fa * fm <= 0) b = m; else { a = m; fa = fm; }
        }
        const t = (a + b) / 2;
        events.push(Object.assign({ t, kind: f0 > 0 ? 1 : -1 }, value(t)));
      }
      t0 = t1; f0 = f1;
    }
    const curve = [];
    for (let k = 0; k <= steps; k++) curve.push([k * step, value(k * step).value]);
    return { tz, events, curve, value };
  }

  // the station's local date and hour now: [JDN, hour]
  function now(st, date) {
    date = date || new Date();
    const utc = date.getTime() / 864e5 + 2440587.5;            // the Julian Day now (UT)
    let n = Math.floor(utc + 0.5 + st.tz / 24);
    const tz = st.tz + dst(st, n);
    const local = utc + 0.5 + tz / 24;
    n = Math.floor(local);
    return [n, (local - n) * 24];
  }

  // the distance in nautical miles (as ARTF47: 60 x the hypotenuse of dlat and dlon x cos lat)
  function nm(lat1, lon1, lat2, lon2) {
    return 60 * Math.hypot(lat2 - lat1, (lon2 - lon1) * Math.cos(lat1 * D2R));
  }

  root.T47 = { jdn, cal, dst, astro, basics, vector, comp, evalc, day, now, nm, SPEEDS };
})(typeof window !== 'undefined' ? window : globalThis);
