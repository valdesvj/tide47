// app.js - the Tide 47 web app: regions and stations, a day's curve and its high and low waters (or slacks and
// maxima), now, the station nearest a position. The engine is tide47.js; the data data/*.js (tools/make_web_data.py).
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const DAYS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
  const pad = x => String(x).padStart(2, '0');
  const hhmm = t => { const m = Math.round(t * 60); return pad(Math.floor(m / 60) % 24) + ':' + pad(m % 60); };
  const store = {
    get(k) { try { return JSON.parse(localStorage.getItem('t47.' + k)); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem('t47.' + k, JSON.stringify(v)); } catch (e) { /* no storage */ } },
  };

  let regions = [];
  const S = { r: 0, s: 0, n: null, pos: null };

  function loadRegions() {
    const priv = (globalThis.T47PRIVATE || []).map(r => Object.assign({}, r, { private: true }));
    regions = priv.concat(globalThis.T47PUBLIC || []);
    $('region').innerHTML = regions.map((r, i) =>
      `<option value="${i}">${r.private ? '★ ' : ''}${r.title}${r.stream ? '' : ''} (${r.stations.length})</option>`).join('');
    $('datanote').innerHTML = priv.length
      ? `Private stations loaded: ${priv.map(r => r.title + ' (' + r.stations.length + ')').join(', ')}.`
      : '<span class="warn">No private stations:</span> run <code>python3 tools/make_web_data.py</code> on your ' +
        'computer (it writes web/data/private.js from python/stations_private.py), or use “Private data…”.';
  }

  function fillStations() {
    const r = regions[S.r];
    $('region').value = S.r;
    $('station').innerHTML = r.stations.map((st, i) => `<option value="${i}">${st.name}</option>`).join('');
    $('station').value = S.s;
  }

  function station() { return regions[S.r].stations[S.s]; }

  function setDateInput() {
    const [y, m, d] = T47.cal(S.n);
    $('date').value = `${y}-${pad(m)}-${pad(d)}`;
  }

  function fmtPos(lat, lon) {
    const f = (v, p, n) => { const a = Math.abs(v); const d = Math.floor(a); return `${d}°${(60 * (a - d)).toFixed(1).padStart(4, '0')}′${v >= 0 ? p : n}`; };
    return f(lat, 'N', 'S') + ' ' + f(lon, 'E', 'W');
  }

  // "27.2 49.7", "27 12.0N 49 42.0E", "27°12.0'N 049°42.0'E", "-12.5 44.9"
  function parsePos(s) {
    const t = s.toUpperCase().replace(/[°′'″"]/g, ' ').replace(/([NSEW])/g, ' $1 ').trim().split(/[\s,;]+/);
    const parts = []; let cur = [];
    for (const x of t) {
      if ('NSEW'.includes(x) && x.length === 1) { cur.push(x); parts.push(cur); cur = []; } else if (x) cur.push(x);
    }
    if (cur.length) parts.push(cur);
    let vals;
    if (parts.length === 1 && parts[0].length === 2) vals = parts[0].map(x => [x]);
    else if (parts.length === 1 && parts[0].length === 4) vals = [parts[0].slice(0, 2), parts[0].slice(2)];
    else vals = parts;
    if (vals.length !== 2) return null;
    const conv = p => {
      let sign = 1; const nums = [];
      for (const x of p) { if (x === 'S' || x === 'W') sign = -1; else if (x === 'N' || x === 'E') ; else nums.push(parseFloat(x)); }
      if (!nums.length || nums.some(isNaN)) return NaN;
      const v = Math.abs(nums[0]) + (nums[1] || 0) / 60 + (nums[2] || 0) / 3600;
      return sign * (nums[0] < 0 ? -v : v);
    };
    const lat = conv(vals[0]), lon = conv(vals[1]);
    return isNaN(lat) || isNaN(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180 ? null : [lat, lon];
  }

  function nearest() {
    if (!S.pos) return null;
    let best = null;
    regions.forEach((r, ri) => {
      if (r.stream) return;
      r.stations.forEach((st, si) => {
        const d = T47.nm(S.pos[0], S.pos[1], st.lat, st.lon);
        if (!best || d < best.d) best = { ri, si, d };
      });
    });
    return best;
  }

  function render() {
    const st = station();
    const stream = !!st.kind;
    const [nNow, hNow] = T47.now(st);
    if (S.n === null) S.n = nNow;
    setDateInput();
    const day = T47.day(st, S.n);
    const [y, m, d] = T47.cal(S.n);
    $('name').textContent = st.name;
    $('dayname').textContent = `${DAYS[(S.n + 1) % 7]} ${pad(d)}-${pad(m)}-${y}`;
    const tz = 'UTC' + (day.tz >= 0 ? '+' : '') + day.tz + (T47.dst(st, S.n) ? ' (DST)' : '');
    $('meta').textContent = `${fmtPos(st.lat, st.lon)} · ${tz} · ${stream ? st.datum : 'datum ' + st.datum} · ${st.src}`;
    const chips = [];
    const isToday = S.n === nNow;
    if (isToday) {
      const v = day.value(hNow);
      chips.push(`<span class="chip now">NOW ${hhmm(hNow)} ${stream ? Math.abs(v.value).toFixed(2) + ' kn ' +
        String(Math.round(v.set)).padStart(3, '0') + '°' : v.value.toFixed(2) + ' m'}</span>`);
    }
    if (S.pos) {
      chips.push(`<span class="chip">${T47.nm(S.pos[0], S.pos[1], st.lat, st.lon).toFixed(1)} nm from ${fmtPos(S.pos[0], S.pos[1])}</span>`);
    }
    if (regions[S.r].private) chips.push('<span class="chip">★ private data</span>');
    $('chips').innerHTML = chips.join('');
    drawChart(day, stream, isToday ? hNow : null);
    drawTable(day, stream, isToday ? hNow : null);
    store.set('sel', { title: regions[S.r].title, name: st.name });
  }

  function drawChart(day, stream, hNow) {
    const cw = $('chart').getBoundingClientRect().width || 1000;     // the viewBox at the drawn size: text stays legible
    const W = Math.round(Math.max(340, Math.min(1100, cw))), H = Math.round(Math.max(240, Math.min(380, W * 0.42)));
    const L = 44, R = 18, T = 26, B = 32;
    $('chart').setAttribute('viewBox', `0 0 ${W} ${H}`);
    const vals = day.curve.map(p => p[1]);
    let lo = Math.min(...vals), hi = Math.max(...vals);
    if (stream) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
    const span = hi - lo;
    const stepv = span <= 1 ? 0.25 : span <= 3 ? 0.5 : span <= 6 ? 1 : 2;
    lo = Math.floor(lo / stepv) * stepv; hi = Math.ceil(hi / stepv) * stepv;
    if (hi - lo < stepv) hi = lo + stepv;
    const X = t => L + (W - L - R) * t / 24, Y = v => T + (H - T - B) * (hi - v) / (hi - lo);
    let s = '';
    for (let v = lo; v <= hi + 1e-9; v += stepv) {
      s += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--grid)"/>` +
        `<text x="${L - 8}" y="${Y(v) + 4}" text-anchor="end" font-size="13" fill="var(--soft)">${+v.toFixed(2)}</text>`;
    }
    for (let h = 0; h <= 24; h += 3) {
      s += `<line x1="${X(h)}" x2="${X(h)}" y1="${T}" y2="${H - B}" stroke="var(--grid)"/>` +
        `<text x="${X(h)}" y="${H - B + 20}" text-anchor="middle" font-size="13" fill="var(--soft)">${pad(h)}</text>`;
    }
    if (stream) s += `<line x1="${L}" x2="${W - R}" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--soft)" stroke-width="1"/>`;
    s += `<text x="${L - 8}" y="${T - 12}" text-anchor="end" font-size="12" fill="var(--soft)">${stream ? 'kn' : 'm'}</text>`;
    const path = day.curve.map((p, k) => (k ? 'L' : 'M') + X(p[0]).toFixed(1) + ' ' + Y(p[1]).toFixed(1)).join('');
    s += `<path d="${path}" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round"/>`;
    for (const e of day.events) {
      const cls = e.kind > 0 ? 'var(--high)' : 'var(--low)';
      const yv = Y(e.value);
      s += `<circle cx="${X(e.t)}" cy="${yv}" r="4.5" fill="${cls}"/>` +
        `<text x="${X(e.t)}" y="${e.kind > 0 ? yv - 10 : yv + 20}" text-anchor="middle" font-size="13" ` +
        `font-weight="600" fill="${cls}">${hhmm(e.t)}</text>`;
    }
    if (hNow !== null) {
      s += `<line x1="${X(hNow)}" x2="${X(hNow)}" y1="${T}" y2="${H - B}" stroke="var(--now)" stroke-dasharray="4 4" stroke-width="1.5"/>`;
    }
    $('chart').innerHTML = s;
  }

  function drawTable(day, stream, hNow) {
    const ev = day.events;
    const next = hNow === null ? -1 : ev.findIndex(e => e.t > hNow);
    let h = stream
      ? '<tr><th>Stream</th><th>Time</th><th class="num">Knots</th><th class="num">Set</th></tr>'
      : '<tr><th>Tide</th><th>Time</th><th class="num">Height</th><th class="num">Range</th></tr>';
    ev.forEach((e, i) => {
      const nx = i === next ? ' class="next"' : '';
      if (stream) {
        const label = e.kind > 0 ? (stream && regions[S.r].stations[S.s].kind === 'rect' ? (e.value >= 0 ? 'FLOOD' : 'EBB') : 'MAX')
          : (regions[S.r].stations[S.s].kind === 'rect' ? 'SLACK' : 'MIN');
        h += `<tr${nx}><td class="${e.kind > 0 ? 'hw' : 'lw'}">${label}</td><td>${hhmm(e.t)}</td>` +
          `<td class="num">${Math.abs(e.value).toFixed(2)}</td><td class="num">${label === 'SLACK' ? '' : String(Math.round(e.set)).padStart(3, '0') + '°'}</td></tr>`;
      } else {
        const rng = i ? Math.abs(e.value - ev[i - 1].value).toFixed(2) + ' m' : '';
        h += `<tr${nx}><td class="${e.kind > 0 ? 'hw' : 'lw'}">${e.kind > 0 ? 'HIGH' : 'LOW'}</td><td>${hhmm(e.t)}</td>` +
          `<td class="num">${e.value.toFixed(2)} m</td><td class="num">${rng}</td></tr>`;
      }
    });
    if (!ev.length) h += '<tr><td colspan="4">No turning point this day.</td></tr>';
    $('events').innerHTML = h;
  }

  function select(ri, si, keepDay) {
    S.r = ri; S.s = si;
    if (!keepDay) S.n = null;
    fillStations(); render();
  }

  function bind() {
    $('region').onchange = () => select(+$('region').value, 0, true);
    $('station').onchange = () => select(S.r, +$('station').value, true);
    $('prev').onclick = () => { S.n--; render(); };
    $('next').onclick = () => { S.n++; render(); };
    $('today').onclick = () => { S.n = null; render(); };
    $('date').onchange = () => {
      const [y, m, d] = $('date').value.split('-').map(Number);
      if (y) { S.n = T47.jdn(y, m, d); render(); }
    };
    $('nearest').onclick = () => {
      const p = parsePos($('pos').value);
      if (!p) { $('pos').style.borderColor = 'var(--now)'; return; }
      $('pos').style.borderColor = '';
      S.pos = p; store.set('pos', $('pos').value);
      const b = nearest();
      if (b) select(b.ri, b.si, true);
      if (globalThis.T47FLOWVIEW) T47FLOWVIEW.render();
    };
    $('pos').onkeydown = e => { if (e.key === 'Enter') $('nearest').click(); };
    $('loadpriv').onclick = () => $('privfile').click();
    $('privfile').onchange = async () => {
      const f = $('privfile').files[0];
      if (!f) return;
      try {
        const txt = await f.text();
        const json = txt.slice(txt.indexOf('['), txt.lastIndexOf(']') + 1);
        globalThis.T47PRIVATE = JSON.parse(json);
        loadRegions(); select(0, 0, true);
      } catch (e) { alertNote('That file is not a private.js from tools/make_web_data.py.'); }
    };
    document.addEventListener('keydown', e => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
      const st = regions[S.r].stations;
      if (e.key === 'ArrowLeft') { S.n--; render(); }
      else if (e.key === 'ArrowRight') { S.n++; render(); }
      else if (e.key === 'ArrowDown') { select(S.r, (S.s + 1) % st.length, true); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { select(S.r, (S.s - 1 + st.length) % st.length, true); e.preventDefault(); }
      else if (e.key === 't' || e.key === 'T') { S.n = null; render(); }
    });
  }

  function alertNote(msg) { $('datanote').innerHTML = `<span class="warn">${msg}</span>`; }

  loadRegions();
  const sel = store.get('sel');
  if (sel) {
    const ri = regions.findIndex(r => r.title === sel.title);
    if (ri >= 0) { S.r = ri; S.s = Math.max(0, regions[ri].stations.findIndex(s => s.name === sel.name)); }
  }
  const pos = store.get('pos');
  if (pos) { $('pos').value = pos; S.pos = parsePos(pos); }
  bind(); fillStations(); render();
  // shared with flow.js
  globalThis.T47APP = { $, store, hhmm, pad, fmtPos, parsePos, get regions() { return regions; }, S, DAYS };
  setInterval(() => { if (S.n === T47.now(station())[0]) render(); }, 60000);
  let rt = null;
  window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(render, 150); });
})();
