#!/usr/bin/env python3
"""aramco_pdf.py - the station files of private/aramco/ from Saudi Aramco's tide tables PDF (Arabian Gulf, the
"Tide Calendar Graphs / Hourly Tide Level Predictions" edition): its hourly predictions (cm above LAT, local standard
time UTC+3) and the station coordinates are read from the PDF's text (pdftotext -layout, poppler-utils). Each month
must give exactly 24 heights a day, else the tool stops. The tables are Aramco's: the files stay in private/ (not in git).
  python3 tools/aramco_pdf.py TABLES.pdf [YEAR]       -> private/aramco/NN_station.txt
then: python3 tools/make_private.py; python3 tools/compare_tables.py; python3 tools/build_tide47.py --private"""
import calendar, collections, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    pdf = sys.argv[1]
    year = int(sys.argv[2]) if len(sys.argv) > 2 else None
    txt = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True, check=True).stdout
    L = txt.split('\n')
    if year is None:
        m = re.search(r'Arabian Gulf \| (\d{4})', txt) or re.search(r' - January (\d{4})', txt)
        year = int(m.group(1))
    months = {m: i for i, m in enumerate(calendar.month_name) if m}
    hdr = re.compile(r"^(.+?) - (%s) %d$" % ('|'.join(months), year))
    dayre = re.compile(r"^\s*\d\d\s+(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b")
    data, cur = collections.OrderedDict(), None
    for ln in L:
        m = hdr.match(ln.strip()) if (' - ' in ln and ' %d' % year in ln and len(ln.strip()) < 60) else None
        if m:
            cur = (m.group(1).strip(), months[m.group(2)])
            data.setdefault(cur, [])
            continue
        if cur is None:
            continue
        tok = dayre.sub('', ln).split()
        if len(tok) == 12 and all(re.fullmatch(r'-?\d+', t) for t in tok):
            data[cur].append([int(t) for t in tok])
    st = collections.OrderedDict()
    for (name, mon), rows in data.items():
        nd = calendar.monthrange(year, mon)[1]
        if len(rows) != 2 * nd:
            raise SystemExit('%s %s %d: %d lines of 12 heights, %d expected' % (name, calendar.month_name[mon], year,
                                                                              len(rows), 2 * nd))
        st.setdefault(name, {})[mon] = rows
    coord = {}
    for ln in L:
        m = '°' in ln and 'cm' in ln and re.match(r"^\s*(.+?)\s{2,}(\d+)°(\d+)'([\d.]+)\"\s+(\d+)°(\d+)'([\d.]+)\"\s+(\d+) cm", ln)
        if m:
            g = m.groups()
            coord[g[0].strip()] = (int(g[1]) + int(g[2]) / 60 + float(g[3]) / 3600,
                                   int(g[4]) + int(g[5]) / 60 + float(g[6]) / 3600, int(g[7]))

    def key(s):
        return re.sub(r'[^a-z0-9]', '', s.lower().replace('safaniyah', 'safaniya').replace('pier', ''))
    ck = {key(k): v for k, v in coord.items()}
    out_dir = os.path.join(ROOT, 'private', 'aramco')
    os.makedirs(out_dir, exist_ok=True)
    for i, (name, mons) in enumerate(st.items(), 1):
        if len(mons) != 12:
            raise SystemExit('%s: %d months' % (name, len(mons)))
        nm = name.replace("'", '').replace('’', '')
        if nm == 'Juaymah':
            nm = 'Juaymah Pier'
        la, lo, msl = ck.get(key(nm), (0.0, 0.0, 0))
        out = ['# name: %s' % nm, '# lat: %.5f' % la, '# lon: %.5f' % lo, '# tz: 3', '# datum: LAT',
               '# source: Aramco %d' % year, '# MSL-LAT in the tables: %d cm' % msl]
        if nm.startswith('Qurrayah'):
            out.append('# compare: Mina Salman, Bahrain')         # the nearest public port (TICON-3)
        n = 0
        for mon in range(1, 13):
            rows = mons[mon]
            for d in range(len(rows) // 2):
                for h, v in enumerate(rows[2 * d] + rows[2 * d + 1]):
                    out.append('%d-%02d-%02d %02d:00 %.2f' % (year, mon, d + 1, h, v / 100)); n += 1
        fn = os.path.join(out_dir, '%02d_%s.txt' % (i, re.sub(r'[^a-z0-9]+', '_', nm.lower()).strip('_')))
        open(fn, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
        print('%-22s %5d hours  %s' % (nm, n, os.path.relpath(fn, ROOT)) + ('' if la else '   (no coordinates found)'))


if __name__ == '__main__':
    main()
