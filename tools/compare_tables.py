#!/usr/bin/env python3
"""compare_tables.py - Tide 47 against the tide tables you typed (private/aramco/*.txt with HW / LW rows): every high
and low water of the tables matched to Tide 47's of the same kind on the same day (python/tide47ref.day: the C47's
numbers), the differences in time (minutes) and height (cm), per station and month. With make_private.py
--test-from, only the rows from that date (not used in the fit) are compared: a fair test of the prediction.
A station of the public regions can be compared too (# compare: Mina Salman in the station's file), e.g. to see how
far a nearby TICON gauge is from the tables.
  python3 tools/compare_tables.py            -> private/COMPARE.md (and a summary here)"""
import datetime as dt, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'python'), os.path.join(ROOT, 'tools')]
import tide47ref as R
import make_private as M


def stats(v):
    if not v:
        return 0, 0, 0
    return sum(v) / len(v), math.sqrt(sum(x * x for x in v) / len(v)), max(v, key=abs)


def compare(port, ev, split):
    """[(table event, Tide 47's)] for the table's high / low waters (from split, if given)."""
    pairs = []
    days = {}
    for kind, t, h in ev:
        if split and t < split:
            continue
        n = R.jdn(t.year, t.month, t.day)
        if n not in days:
            days[n] = R.day(port, n)[1]
        k = 1 if kind == 'HW' else -1
        cand = [(abs((x - (t.hour + t.minute / 60))), x, y) for x, y, kk in days[n] if kk == k]
        if cand:
            d, x, y = min(cand)
            if d < 3:
                pairs.append((kind, t, h, x, y))
    return pairs


def main():
    import stations_private as P, stations
    split = dt.datetime.strptime(P.SPLIT, '%Y-%m-%d') if P.SPLIT else None
    ports = {p['name']: p for p in P.REGIONS[0][3]}
    pub = {p['name']: p for _, _, _, ps in stations.REGIONS for p in ps}
    md = ['# Tide 47 against the tide tables', '',
          'The high and low waters of the tables (private/aramco/) against Tide 47 (the C47\'s numbers: '
          'python/tide47ref.day). Time: Tide 47 - tables (minutes); height: Tide 47 - tables (cm).',
          ('Only the rows from %s, not used to work out the constants.' % P.SPLIT) if split else
          '**The constants were worked out from these same rows**: this shows the fit, not a fair test (use '
          'make_private.py --test-from).', '']
    md += ['| station | compared | events | time mean / rms / worst (min) | height mean / rms / worst (cm) |',
           '|---|---|---|---|---|']
    for f in sorted(os.listdir(P.FOLDER)):
        if not f.endswith('.txt'):
            continue
        st, ev, hourly, hc, z0 = M.read_station(os.path.join(P.FOLDER, f))
        if st['name'][:22] not in ports:
            continue
        if hourly:                                         # hourly heights: Tide 47's (the C47's curve) at the hour
            port = ports[st['name'][:22]]
            days, dh = {}, []
            for t, h in hourly:
                if split and t < split:
                    continue
                n = R.jdn(t.year, t.month, t.day)
                if n not in days:
                    days[n] = R.day(port, n)[2]
                dh.append((days[n][3 * t.hour] - h) * 100)
            b = stats(dh)
            md.append('| %s | Tide 47, hourly heights | %d hours | | %+.1f / %.1f / %+.1f |' % (st['name'], len(dh), *b))
            print('%-22s %-34s %5d hours  height %+5.1f / %4.1f / %+5.1f cm' % (st['name'], 'Tide 47, hourly', len(dh), *b))
            if not ev:
                continue
        if not ev:
            continue
        targets = [('Tide 47 (%s)' % st['name'][:22], ports[st['name'][:22]])]
        if st.get('compare') and st['compare'] in pub:
            targets.append(('%s (%s)' % (st['compare'], pub[st['compare']]['src']), pub[st['compare']]))
        for label, port in targets:
            pairs = compare(port, ev, split)
            dtm = [(x - (t.hour + t.minute / 60)) * 60 for _, t, h, x, y in pairs]
            dh = [(y - h) * 100 for _, t, h, x, y in pairs]
            a, b = stats(dtm), stats(dh)
            line = '| %s | %s | %d | %+.0f / %.0f / %+.0f | %+.1f / %.1f / %+.1f |' % (st['name'], label, len(pairs), *a, *b)
            md.append(line)
            print('%-22s %-34s %4d events  time %+5.0f / %4.0f / %+5.0f min  height %+5.1f / %4.1f / %+5.1f cm'
                  % (st['name'], label, len(pairs), *a, *b))
    md += ['', 'Not for navigation: the official tables are the reference; Tide 47 gives the astronomical tide only.']
    os.makedirs(os.path.join(ROOT, 'private'), exist_ok=True)
    open(os.path.join(ROOT, 'private', 'COMPARE.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    print('private/COMPARE.md written')


if __name__ == '__main__':
    main()
