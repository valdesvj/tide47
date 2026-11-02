#!/usr/bin/env python3
"""test_web.py - the web app's engine (web/tide47.js, in node) against the Python twin (python/tide47ref.py).

1. vector(): V + u and f of all the constituents at a few dates, the same to 1E-9 degree / 1E-12;
2. day(): every public station (tides and streams), 20 days: the same events as the twin's exact method found finely
   (tests/test_tide47.py truth()): the count, the kinds, the times (s) and the values; the curve against the exact
   heights.
  python3 tests/test_web.py      (needs node; runs tools/make_web_data.py first)"""
import json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'python'), os.path.join(ROOT, 'tests')]
import tide47ref as R          # noqa: E402
import stations, streams       # noqa: E402
import test_tide47 as T        # noqa: E402

FAIL = []


def check(ok, what):
    print('  %s  %s' % ('ok  ' if ok else 'FAIL', what), flush=True)
    if not ok:
        FAIL.append(what)


JS = r"""
require(process.argv[2] + '/data/cons.js'); require(process.argv[2] + '/data/public.js');
require(process.argv[2] + '/tide47.js');
const q = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const out = {vec: q.vec.map(j => T47.vector(j)), days: []};
for (const [ri, si, n] of q.days) {
  const st = T47PUBLIC[ri].stations[si];
  const d = T47.day(st, n);
  out.days.push({ev: d.events, curve: d.curve.filter((_, k) => k % 4 === 0).map(p => p[1])});
}
globalThis.T47FLOW = q.atlas;
const ref = T47PUBLIC[0].stations[0];
out.flow = q.flow.map(([n, h, lat, lon, wdir, wkn]) => {
  const [nn, m] = T47.flowPick(ref, n, h);
  const c = T47.flowCycle(ref, nn, m);
  const cell = T47.flowCell(q.atlas, lat, lon);
  const nx = T47.flowStep(ref, nn, m, 1), pv = T47.flowStep(ref, nn, m, -1);
  return {n: nn, m, t: c.t, f: c.f, cell, rows: cell ? T47.flowRows(cell, c.f, wdir, wkn) : null, next: nx, prev: pv};
});
process.stdout.write(JSON.stringify(out));
"""


def main():
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'make_web_data.py')], check=True, capture_output=True)
    regs = stations.REGIONS + streams.REGIONS
    n0 = R.jdn(2026, 1, 1)
    days = [(ri, si, n0 + 17 * d) for ri, (_, _, _, ps) in enumerate(regs) for si in range(len(ps)) for d in range(20)]
    vec = [R.jd(2026, 1, 1), R.jd(2030, 6, 15, 7.5), R.jd(2019, 3, 3)]
    import synth_flow
    atlas = synth_flow.atlas()
    ref = stations.REGIONS[0][3][0]
    flow = [(n0 + 11 * d, (d * 5.3) % 24, 26.0 + (d % 7) * 0.45, 48.7 + (d % 9) * 0.27, (d * 40) % 360, d % 4 * 5)
            for d in range(40)]
    js = os.path.join(ROOT, 'web', '_t.js')
    open(js, 'w').write(JS)
    try:
        r = subprocess.run(['node', js, os.path.join(ROOT, 'web')], input=json.dumps(dict(vec=vec, days=days, atlas=atlas, flow=flow)),
                           capture_output=True, text=True, check=True)
    finally:
        os.remove(js)
    out = json.loads(r.stdout)
    print('1. the constituents\' V + u and f')
    wv = wf = 0
    for j, got in zip(vec, out['vec']):
        for (a, fa), (b, fb) in zip(R.vector(j), got):
            wv = max(wv, abs((a - b + 180) % 360 - 180)); wf = max(wf, abs(fa - fb))
    check(wv < 1e-9 and wf < 1e-12, 'the same to %.1g degree, %.1g' % (wv, wf))
    print('2. the days: %d station-days against the twin (exact, every 5 minutes, bisected)' % len(days))
    wt = wh = wc = 0
    bad = []
    for (ri, si, n), got in zip(days, out['days']):
        st = regs[ri][3][si]
        stream = 'kind' in st
        tr = T.truth(st, n, stream)
        ev = got['ev']
        if len(tr) != len(ev) or any(a[2] != b['kind'] for a, b in zip(tr, ev)):
            bad.append('%s day %d: %d / %d events' % (st['name'], n, len(tr), len(ev)))
            continue
        for a, b in zip(tr, ev):
            wt = max(wt, abs(a[0] - b['t']) * 3600)
            wh = max(wh, abs(a[1] - (abs(b['value']) if st.get('kind') == 'rot' else b['value'])))
        if not stream:
            tz = st['tz'] + R.dst(st, n)
            E = R.comp(st, n - 0.5 - tz / 24, st['hc'])
            wc = max([wc] + [abs(v - R.evaluate(E, st['z0'], k / 3)[0]) for k, v in enumerate(got['curve'])])
    for b in bad[:5]:
        check(False, b)
    check(not bad and wt < 2 and wh < 1e-6 and wc < 1e-9,
          'the same events: times within %.2f s, values within %.1g; the curve within %.1g m' % (wt, wh, wc))
    print('3. FLOW: the High Water picked, the cycle\'s factor, the atlas at a position (synthetic atlas, Mina Salman)')
    ok, wt, wf, wr = True, 0, 0, 0
    for (n, h, lat, lon, wdir, wkn), got in zip(flow, out['flow']):
        nn, m = R.flow_pick(ref, n, h)
        t, _, _, f = R.flow_cycle(ref, nn, m)
        cell = R.flow_cell(atlas, lat, lon)
        ok = ok and (got['n'], got['m']) == (nn, m) and (cell is None) == (got['cell'] is None)
        ok = ok and tuple(got['next']) == R.flow_step(ref, nn, m, 1) and tuple(got['prev']) == R.flow_step(ref, nn, m, -1)
        wt, wf = max(wt, abs(t - got['t']) * 3600), max(wf, abs(f - got['f']))
        if cell:
            for (a, b), (c, d) in zip(R.flow_rows(cell, f, wdir, wkn), got['rows']):
                wr = max(wr, abs(a - c), abs(b - d))
    check(ok and wt < 60 and wf < 2e-3 and wr < 2e-3, '%d positions and times: the same High Waters, steps and atlas '
          'cells; times within %.1f s, factors within %.1g, streams within %.1g kn (the twin uses the C47\'s quintic '
          'engine)' % (len(flow), wt, wf, wr))
    print('ALL OK' if not FAIL else '%d FAILED' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
