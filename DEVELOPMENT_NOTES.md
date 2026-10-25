# Tide 47 development notes

## Oct 25, 2026 - v0.1.0: the engine, 25 ports (branch claude/tide47-v01)

- Method: Schureman (SP 98), as NOAA: h = Z0 + sum f H cos(V + u - g). V from the Doodson numbers in the tau basis
  (tau = T + h - s, T = 15 UT + 180: the mean sun's hour angle), s h p N p1 from Meeus' polynomials; u and f from
  Schureman's formulas (I, nu, xi, nu', 2nu'', P, Q, R; f eqs. 73-78, 197/207, 213/215, 227, 235). M1 as NOAA:
  speed tau + p, V + u = tau - 90 + xi - nu + Q (u has -p; XTide's tables confirm it).
- Checked against XTide's harmonics-dwf-20191229-free tables (V0 + u at January 1, f at mid-year, 1970-2100): all 37
  within 0.3 deg and 0.003 in f except M1 (0.4 deg, f 0.04: XTide's yearly approximation of Q). The diurnals first
  came out 180 deg off: T needs the + 180.
- UTide (pip utide 0.4.0) analysing a year of the twin's hourly heights: the constants back within 5 mm, 0.3 deg.
  UTide's SA has V = h - p1 (not NOAA's h), hence its 77 deg.
- Data: NOAA's US stations from the Debian package xtide-data (restore_tide_db -> text; the shell cannot reach NOAA).
  TICON-3 (attached by Victor; PANGAEA is not reachable from the session). TICON against NOAA at six US gauges: the
  same phase convention (M2 S2 N2 K1 O1 P1 K2 within 1-4 deg) except SA (+73 to +93 deg: the solar perigee, V = h -
  p1): converted by + 283.1. TICON has no Dubai, Jeddah, Kuwait or Saudi gauges; the Gulf: Mina Salman.
- LAT for the TICON ports: the lowest of 19 years (2020-2038) hourly, the 40 lowest hours refined to the minute.
- The C47 engine (proven commands of Almanac 47): M x M, M + M, M - M, M x r, M MOD r, COS / SIN / e^x of a matrix,
  DOT; new: LN (and IP of a matrix: firmware list in Almanac 47's tools/navmat.py). f x H without an element-wise
  product: A = e^(EM x LF + LH), LH = LN(H + 1E-40) from the port's data, so a missing constituent is e^-92 = 0.
  A port: HG, one number a constituent (H in 0.1 mm x 100000 + g in 0.01 deg), unpacked with IP / x / -.
- The constant matrices DM UM EM: one number a row (two digits a value + 50), LBL :ROW: unpacks them (the source
  stays short: 135 numbers).
- Events: h' at every hour 0-24; a sign change: the straight line between the two hours, then 4 Newton steps
  clamped to the hour; the kind from h''. The twin does exactly that (tide47ref.day).
- The curve: a height every 20 minutes (73), straight between them, one PIXEL a column; the scale 0.5 m (1 m over
  3 m of range). Labels of the high / low waters above / below their cross, beside it when they would leave the chart.
- Times in the simulator: the start 40 000 steps (6.8 s), a day 19 000 (3.3 s), a port 21 000 (3.5 s).
- c47sim: LN (a number, a matrix) and e^x of a number added (marked tide47): to be taken into Almanac 47.

## Oct 25, 2026 - a private region: Aramco's stations (branch claude/tide47-aramco)

- Saudi Aramco's tide tables are Aramco's copyright and TICON-3 has no Saudi gauge: the constants are worked out on
  Victor's computer from the typed tables (private/aramco/*.txt), never in git (private/, python/stations_private.py).
- tools/make_private.py: least squares with tide47ref's astronomy (no convention to convert): unknowns Z0, H cos g,
  H sin g; a high / low water gives its height and h' = 0 at its time (weight 1 h). The constituents the record
  separates (Rayleigh 1, in NOAA's order). UTide on the heights alone was tried first: 58 min / 10 cm rms on the
  months left out; with h' = 0: 5 min / 4 cm with 9 months; two years: 2 min rms (worst 9) and 0.9 cm rms on the
  third year (a synthetic table from Mina Salman, rounded to the minute and the cm).
- tools/compare_tables.py: each table event against Tide 47's of the same kind that day (tide47ref.day = the C47's
  numbers); --test-from in make_private.py keeps the compared rows out of the fit. private/COMPARE.md.
- The build: REM ==== REGIONS and NREG from the regions (public 3; --private adds stations_private's) ->
  private/build/TIDE47.txt and TIDEAR.txt. The public build is unchanged (the same steps). Checked in c47sim: + four
  times reaches ARAMCO.

- The 2026 Aramco tables (Arabian Gulf, 13 stations, attached by Victor): their hourly predictions (cm above LAT,
  UTC+3) read from the PDF text (pdftotext -layout: two lines of 12 a day, the day label anywhere; every month
  exactly 2 x its days), private/aramco/*.txt with the tables' coordinates. The fit on the whole year (8 760 hours =
  364.96 days: Rayleigh 0.9 so that SA and SSA stay) left 2.3-3.2 cm rms; the residual's periodogram: the terannual
  STA (2 cm), TAU1, PSI1, SO1, M2 - SSA, MSN2, PHI1, MSM, SIG1 (Aramco analysed longer records with more
  constituents). Added to the engine (54 constituents; M2 + SSA is MKS2): 0.7-1.9 cm rms, worst 2.4-6.3 cm, for all
  13. Held out Oct-Dec with a Jan-Sep fit (no SA / SSA): 3.4-6.5 cm rms (the seasonal level).
- The C47 with 54: the start 44 000 steps (7.5 s), a day and a port unchanged (3.3-3.5 s).
- To the tables' rounding: all 92 other standard constituents (UTide's list) gave little (Ras Tanura 1.17 -> 0.89 cm),
  nor did the nodal corrections held for the year (NOAA's way) or none; the residual was smooth (autocorrelation
  0.94 at 1 h, 0.88 at 24 h, -0.49 at 7 days): the seasonal sidebands of the diurnals, O1 + SA (13.9841 deg/h, 1.7 cm)
  first, not in the standard lists. make_private's PRIORITY also missed MA2 MB2 MTM MSQM S3 (never fitted): fixed.
  Added O1 + SA, O1 - SA, Q1 + SA, 4 SA, MF + SA, MTM + SA (60): all 13 stations 0.4-0.6 cm rms, worst 1.2-2.2 cm (the
  tables in whole cm: 0.3 cm rms is the floor). Candidates on the frequency of a constituent already there (S2 - SA =
  T2, M2 + SA = MB2, O1 + 2SA = TAU1) only cancel each other: the engine checks there are none. The start 8.0 s.

## Plans

- Tidal streams (a branch of its own): harmonic analysis of the vessel's own ADCP / current-meter logs (least squares,
  the same constituents, major / minor axes), then the C47 predicts speed and direction with the same engine.
- More ports: TICON-3 has 3 363 gauges; a region program per area.
- The tide at a given time (key 7), the next high / low water from now, spring / neap (the M2 - S2 phase).
- Free42 / DM42 build later.
