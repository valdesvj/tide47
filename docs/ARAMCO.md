# A private region: Aramco's stations

Saudi Aramco's tide tables (Ras Tanura, Ju'aymah, Tanajib, Safaniya, Manifa, Khursaniyah, Dammam, Yanbu, ...) are
Aramco's copyright, and TICON-3 has no gauge on the Saudi coast. So Tide 47 works their constants out on **your**
computer from the tables you type, and keeps them out of git (`private/` and `python/stations_private.py` are in
`.gitignore`). Nothing from the tables goes to GitHub.

## 1. Type the tables

One file a station in `private/aramco/`, e.g. `private/aramco/ras_tanura.txt`:

```
# name: Ras Tanura
# lat: 26.64
# lon: 50.16
# tz: 3
# datum: CD
# source: Aramco 2025-26
# compare: Mina Salman, Bahrain
HW 2025-01-01 04:12 2.05
LW 2025-01-01 10:31 0.62
HW 2025-01-01 16:40 1.88
LW 2025-01-01 22:58 0.71
...
```

(The values above only show the format.) The rows are the tables' local time and metres above their datum:

- `HW` / `LW` date time height: the high and low waters (the usual page of a tide table);
- or `date time height`: hourly heights, if the tables have them;
- or `CONST M2 0.5821 123.40` (H in m, g in degrees, Greenwich) and `Z0 1.234`, if they print harmonic constants.

`# compare:` (optional) also compares the tables with one of Tide 47's ports.

**How much to type:** two years of high and low waters give constants that predict the next year within a few
minutes and about 1 cm (a test with a synthetic table: 2 min rms, worst 9 min, 0.9 cm rms). Less than a year cannot
separate the seasonal tide SA from the mean level: the heights then drift by some centimetres over the seasons.

## 2. Work out the constants

```bash
python3 tools/make_private.py --test-from 2027-01-01
```

The least squares uses Tide 47's own astronomy (each high or low water gives two equations: its height, and h' = 0 at
its time) and keeps the constituents the record separates. `--test-from` leaves the rows from that date out of the fit,
for a fair comparison. It writes `python/stations_private.py`.

## 3. Compare with the tables

```bash
python3 tools/compare_tables.py
```

writes `private/COMPARE.md`: per station the number of high and low waters compared, and the time (minutes) and
height (cm) differences: mean, rms and the worst.

## 4. The calculator files

```bash
python3 tools/build_tide47.py --private
```

writes `private/build/TIDE47.txt` (the program with a 4th region, ARAMCO: + cycles MIDDLE EAST, USA, LATIN AMERICA,
ARAMCO) and `private/build/TIDEAR.txt`. Convert both with rejig and load them with TIDEME, TIDEUS and TIDELA from
`build/` (the private TIDE47 replaces the public one: it calls TIDEAR, so TIDEAR must be loaded).

Not for navigation: the official tables are the reference.
