// flow.js - the Flow view: FLOW47 / ARTF47 in the browser. The 13 hours of the tidal stream atlas (HW-6 ... HW+6 of
// the reference station's High Water) at the position: a table with an arrow, the set and the knots each hour, and
// the atlas as a map at the hour chosen (speed bands and arrows, the position, the tide stations). The atlas
// (globalThis.T47FLOW) and its reference station come from the private data (tools/make_web_data.py).
(function () {
  'use strict';
  const A = globalThis.T47APP;
  const { $, store, hhmm, pad, fmtPos } = A;
  const BANDS = [[0.25, '#cfe6f5', '0.00-0.25'], [0.5, '#cfe9c8', '0.26-0.50'], [0.75, '#f6efa6', '0.51-0.75'],
    [1.0, '#f8c98a', '0.76-1.00'], [1e9, '#f2a0a0', '1.01 +']];
  const band = s => BANDS.find(b => s <= b[0]);
  const F = { n: null, m: null, hour: null, on: false };

  function atlas() { return globalThis.T47FLOW || null; }

  // the reference station: the atlas's "ref" by name among the loaded stations (private first)
  function refStation() {
    const fl = atlas();
    if (!fl) return null;
    const key = (fl.ref || 'Ras Tanura').toLowerCase();
    for (const r of A.regions) {
      if (r.stream) continue;
      const st = r.stations.find(s => s.name.toLowerCase().includes(key));
      if (st) return st;
    }
    return null;
  }

  function tideStations() {
    const out = [];
    for (const r of A.regions) if (!r.stream && r.private) out.push(...r.stations);
    return out;
  }

  function pickNow(ref) {
    const [n, h] = T47.now(ref);
    [F.n, F.m] = T47.flowPick(ref, n, h);
    F.hour = null;
  }

  function arrowSvg(x, y, u, v, len, color, width, head) {
    const s = Math.hypot(u, v);
    if (s < 0.03) return `<circle cx="${x}" cy="${y}" r="1.6" fill="${color}"/>`;
    const dx = u / s, dy = -v / s;
    const x0 = x - dx * len / 2, y0 = y - dy * len / 2, x1 = x + dx * len / 2, y1 = y + dy * len / 2;
    const hx = x1 - dx * head, hy = y1 - dy * head, px = -dy * head * 0.55, py = dx * head * 0.55;
    return `<line x1="${x0.toFixed(1)}" y1="${y0.toFixed(1)}" x2="${hx.toFixed(1)}" y2="${hy.toFixed(1)}" stroke="${color}" stroke-width="${width}" stroke-linecap="round"/>` +
      `<path d="M${x1.toFixed(1)} ${y1.toFixed(1)}L${(hx + px).toFixed(1)} ${(hy + py).toFixed(1)}L${(hx - px).toFixed(1)} ${(hy - py).toFixed(1)}Z" fill="${color}"/>`;
  }

  function render() {
    if (!F.on) return;
    const fl = atlas(), ref = refStation();
    if (!fl || !ref) {
      $('fname').textContent = 'No stream atlas loaded';
      $('fmeta').innerHTML = fl ? `The atlas's reference station (${fl.ref}) is not among the loaded stations.` :
        'The Flow view needs your private atlas: run <code>python3 tools/make_web_data.py</code> on your computer ' +
        '(it adds python/flow_private.py to web/data/private.js), or load that private.js with “Private data…”.';
      ['fdate', 'fchips', 'ftable', 'fnote', 'map', 'legend', 'hlabel'].forEach(id => { $(id).innerHTML = ''; });
      return;
    }
    if (F.n === null) pickNow(ref);
    const cyc = T47.flowCycle(ref, F.n, F.m);
    const [y, m, d] = T47.cal(F.n);
    const wdir = +$('wdir').value || 0, wkn = +$('wkn').value || 0;
    const pos = A.S.pos;
    const cell = pos ? T47.flowCell(fl, pos[0], pos[1]) : null;
    const rows = cell ? T47.flowRows(cell, cyc.f, wdir, wkn) : null;
    // now, from the High Water (hours), when within the cycle
    const [nNow, hNow] = T47.now(ref);
    const off = (nNow - F.n) * 24 + hNow - cyc.t;
    const inCycle = Math.abs(off) <= 6;
    if (F.hour === null) F.hour = inCycle ? Math.round(off) : 0;

    $('fname').textContent = pos ? 'Stream at ' + fmtPos(pos[0], pos[1]) : 'Stream: enter a position above';
    $('fdate').textContent = `${A.DAYS[(F.n + 1) % 7]} ${pad(d)}-${pad(m)}-${y}`;
    $('fmeta').textContent = `Reference: High Water at ${ref.name} ${hhmm(cyc.t)} (${cyc.h.toFixed(2)} m) · ` +
      `the 13 charts HW−6 … HW+6 · springs × ${cyc.f.toFixed(2)} (range ${cyc.range.toFixed(2)} m)`;
    const chips = [];
    if (rows && inCycle) {
      const [u, v] = T47.flowNow(rows, off);
      const [set, kn] = T47.setkn(u, v);
      chips.push(`<span class="chip now">NOW ${hhmm(hNow)} ${kn.toFixed(2)} kn ${String(Math.round(set) % 360).padStart(3, '0')}°</span>`);
    }
    chips.push(`<span class="chip">${wkn ? 'wind ' + String(wdir).padStart(3, '0') + '° ' + wkn + ' kn: + ' + (T47.WFAC * wkn).toFixed(2) + ' kn' : 'no wind'}</span>`);
    if (fl.source) chips.push(`<span class="chip">★ ${fl.source}</span>`);
    $('fchips').innerHTML = chips.join('');

    // the table
    if (!pos) {
      $('ftable').innerHTML = ''; $('fnote').innerHTML = 'Enter a position (Position, then Nearest) to see its 13 hours.';
    } else if (!rows) {
      $('ftable').innerHTML = '';
      $('fnote').innerHTML = '<span class="warn">No atlas here:</span> the position is outside the charts or on land. ' +
        'The map shows where the charts are.';
    } else {
      let h = '<tr><th>HW</th><th>Time</th><th></th><th class="num">Set</th><th class="num">Knots</th></tr>';
      rows.forEach(([u, v], k) => {
        const [set, kn] = T47.setkn(u, v);
        const t = cyc.t + k - 6;
        const cls = ['click', k - 6 === F.hour ? 'sel' : '', inCycle && Math.round(off) === k - 6 ? 'next' : ''].join(' ');
        h += `<tr class="${cls}" data-h="${k - 6}"><td>${k === 6 ? '<b>HW</b>' : (k > 6 ? '+' : '−') + Math.abs(k - 6)}</td>` +
          `<td>${hhmm(((t % 24) + 24) % 24)}</td><td class="arrow"><svg width="30" height="30" viewBox="-15 -15 30 30" style="margin:0">` +
          arrowSvg(0, 0, u, v, 26, 'var(--accent)', 2.2, 8) + `</svg></td>` +
          `<td class="num">${String(Math.round(set) % 360).padStart(3, '0')}°</td><td class="num"${kn >= 0.75 ? ' style="font-weight:600"' : ''}>${kn.toFixed(2)}</td></tr>`;
      });
      $('ftable').innerHTML = h;
      $('fnote').innerHTML = 'Spring speeds of the charts × the day\'s range' + (wkn ? ', + the wind\'s current' : '') +
        '. Times: the reference\'s High Water ± hours.';
      $('ftable').querySelectorAll('tr[data-h]').forEach(tr => { tr.onclick = () => { F.hour = +tr.dataset.h; render(); }; });
    }
    drawMap(fl, ref, cyc);
  }

  function drawMap(fl, ref, cyc) {
    const k = fl.step_min / 60;
    const lat1 = fl.lat0 + (fl.nlat - 1) * k, lon1 = fl.lon0 + (fl.nlon - 1) * k;
    const mlat = (fl.lat0 + lat1) / 2, cosl = Math.cos(mlat * Math.PI / 180);
    const W = Math.round(Math.max(320, Math.min(700, $('map').getBoundingClientRect().width || 600)));
    const pad_ = 34;
    const sx = (W - 2 * pad_) / ((lon1 - fl.lon0 + k) * cosl);
    const H = Math.round(2 * pad_ + (lat1 - fl.lat0 + k) * sx);
    $('map').setAttribute('viewBox', `0 0 ${W} ${H}`);
    const X = lon => pad_ + (lon - fl.lon0 + k / 2) * cosl * sx, Y = lat => pad_ + (lat1 - lat + k / 2) * sx;
    const cw = k * cosl * sx, ch = k * sx;
    const hi = F.hour + 6;
    let s = `<rect x="0" y="0" width="${W}" height="${H}" fill="var(--card)"/>`;
    let arrows = '';
    for (let i = 0; i < fl.nlat; i++) {
      for (let j = 0; j < fl.nlon; j++) {
        const lat = fl.lat0 + i * k, lon = fl.lon0 + j * k;
        const node = T47.flowNode(fl, i, j);
        if (!node) {
          s += `<rect x="${(X(lon) - cw / 2).toFixed(1)}" y="${(Y(lat) - ch / 2).toFixed(1)}" width="${cw.toFixed(1)}" height="${ch.toFixed(1)}" fill="#e9dfc7" opacity="0.55"/>`;
          continue;
        }
        const [u, v] = node[hi].map(x => x * cyc.f);
        const sp = Math.hypot(u, v);
        s += `<rect x="${(X(lon) - cw / 2).toFixed(1)}" y="${(Y(lat) - ch / 2).toFixed(1)}" width="${(cw + 0.5).toFixed(1)}" height="${(ch + 0.5).toFixed(1)}" fill="${band(sp)[1]}"/>`;
        arrows += arrowSvg(X(lon), Y(lat), u, v, Math.min(ch * 0.95, 6 + sp * ch * 0.9), '#1d232a', 1.4, 5);
      }
    }
    s += arrows;
    // graticule every 15'
    const g = W < 500 ? 0.5 : 0.25;
    for (let la = Math.ceil(fl.lat0 / g) * g; la <= lat1 + 1e-9; la += g) {
      s += `<line x1="${pad_}" x2="${W - pad_}" y1="${Y(la)}" y2="${Y(la)}" stroke="#7a8696" stroke-width="0.5" opacity="0.5"/>` +
        `<text x="${pad_ - 4}" y="${Y(la) + 4}" text-anchor="end" font-size="10" fill="var(--soft)">${Math.floor(la)}°${pad(Math.round((la % 1) * 60))}′</text>`;
    }
    for (let lo = Math.ceil(fl.lon0 / g) * g; lo <= lon1 + 1e-9; lo += g) {
      s += `<line x1="${X(lo)}" x2="${X(lo)}" y1="${pad_}" y2="${H - pad_}" stroke="#7a8696" stroke-width="0.5" opacity="0.5"/>` +
        `<text x="${X(lo)}" y="${H - pad_ + 14}" text-anchor="middle" font-size="10" fill="var(--soft)">${Math.floor(lo)}°${pad(Math.round((lo % 1) * 60))}′</text>`;
    }
    // the tide stations, the reference, the position
    for (const st of tideStations()) {
      if (st.lat < fl.lat0 - k || st.lat > lat1 + k || st.lon < fl.lon0 - k || st.lon > lon1 + k) continue;
      const isRef = st === ref;
      s += `<circle cx="${X(st.lon)}" cy="${Y(st.lat)}" r="${isRef ? 5 : 3.5}" fill="${isRef ? '#c0392b' : '#1f6fb2'}" stroke="#fff" stroke-width="1"/>` +
        `<text x="${X(st.lon) + (X(st.lon) > W * 0.6 ? -6 : 6)}" y="${Y(st.lat) - 5}" text-anchor="${X(st.lon) > W * 0.6 ? 'end' : 'start'}" font-size="10" fill="#1d232a" paint-order="stroke" stroke="#fff" stroke-width="3">${st.name.split(',')[0]}${isRef ? ' (ref)' : ''}</text>`;
    }
    const pos = A.S.pos;
    if (pos) {
      const px = X(pos[1]), py = Y(pos[0]);
      s += `<path d="M${px} ${py - 9}L${px + 8} ${py + 6}L${px - 8} ${py + 6}Z" fill="#c0392b" stroke="#fff" stroke-width="1.5"/>`;
    }
    s += `<rect x="${pad_}" y="${pad_}" width="${W - 2 * pad_}" height="${H - 2 * pad_}" fill="none" stroke="var(--line)"/>`;
    $('map').innerHTML = s;
    const t = cyc.t + F.hour;
    $('hlabel').textContent = `${F.hour === 0 ? 'HW' : 'HW' + (F.hour > 0 ? '+' : '−') + Math.abs(F.hour)} · ${hhmm(((t % 24) + 24) % 24)}`;
    $('hslider').value = F.hour + 6;
    $('legend').innerHTML = BANDS.map(b => `<span><i style="background:${b[1]}"></i>${b[2]} kn</span>`).join('') +
      '<span>× the day\'s range; no wind on the map</span>';
  }

  function show(on) {
    F.on = on;
    $('flowcard').hidden = !on; $('tidecard').hidden = on;
    $('tabFlow').classList.toggle('on', on); $('tabTide').classList.toggle('on', !on);
    store.set('view', on ? 'flow' : 'tide');
    if (on) render();
  }

  function step(d) {
    const ref = refStation();
    if (!ref) return;
    if (F.n === null) pickNow(ref);
    [F.n, F.m] = T47.flowStep(ref, F.n, F.m, d);
    F.hour = null; render();
  }

  $('tabTide').onclick = () => show(false);
  $('tabFlow').onclick = () => show(true);
  $('hwPrev').onclick = () => step(-1);
  $('hwNext').onclick = () => step(1);
  $('hwNow').onclick = () => { F.n = null; render(); };
  $('hPrev').onclick = () => { if (F.hour > -6) { F.hour--; render(); } };
  $('hNext').onclick = () => { if (F.hour < 6) { F.hour++; render(); } };
  $('hslider').oninput = () => { F.hour = +$('hslider').value - 6; render(); };
  $('wdir').onchange = $('wkn').onchange = () => { store.set('wind', [$('wdir').value, $('wkn').value]); render(); };
  const w = store.get('wind');
  if (w) { $('wdir').value = w[0]; $('wkn').value = w[1]; }
  document.addEventListener('keydown', e => {
    if (!F.on || e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (e.key === 'ArrowLeft') { if (F.hour > -6) { F.hour--; render(); } }
    else if (e.key === 'ArrowRight') { if (F.hour < 6) { F.hour++; render(); } }
    else if (e.key === 'ArrowUp' || e.key === 'PageUp') step(-1);
    else if (e.key === 'ArrowDown' || e.key === 'PageDown') step(1);
    else if (e.key === 'n' || e.key === 'N' || e.key === 't' || e.key === 'T') { F.n = null; render(); }
    else return;
    e.preventDefault(); e.stopImmediatePropagation();
  }, true);
  let rt = null;
  window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(render, 150); });
  globalThis.T47FLOWVIEW = { render, show };
  if (store.get('view') === 'flow') show(true);
})();
