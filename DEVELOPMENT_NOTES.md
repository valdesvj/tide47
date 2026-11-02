

## Nov 1, 2026 - v0.4 speed (branch claude/tide47-speed2)

- The engine: an exact evaluation every 2 hours (13 a day, was 25 + one an event): the value and its first three
  derivatives (AW3 = AW2 x the speeds, one more DOT). Between two nodes the quintic (Hermite) through the values,
  slopes, curvatures: QA QB (3 x 7, integers with STEP = 2 in them, written by the build at REM ==== CONS) turn the
  nodes' rows into the coefficients of s^0..s^5 of all 12 intervals at once: CF = (S0 x HR x GF) x QA + (S1 x HR x GF)
  x QB (S0 S1 pick the intervals' starts and ends). QW = CF x SPW: F at s = 0 1/4 1/2 3/4 1 (the ends exact): a sign
  change -> 4 Newton steps on the quintic (Horner, R40-R45), no exact evaluation. The values at the events from CU (CV).
- Streams: rectilinear: the maxima from u' (as a tide's h'), the slacks from u itself (QU = CU x SPW; both in one
  quarter: the earlier first); rotary: g = u u' + v v' (s' = g / s was tried: bad where the speed nearly vanishes).
- Accuracy against the events found finely (exact, every 5 minutes, bisected; tests 3a): tides 2835 events, median
  0.3 s, 99 % 10 s, worst 27 s, heights 0.9 mm; NOAA streams median 0.6 s, 99 % 33 s, worst 68 s, 0.006 kn; the
  synthetic rotary median 1.9 s, 99 % 27 s. v0.2/v0.3 missed close high / low pairs (Chabahar, Djibouti, Galveston):
  found now. The curve within 0.9 mm.
- The chart: PY = CU x SPX x R83 (12 x 30): the quintic at every column, 10 steps a dot (was 26, straight lines).
- FLOW47 / ARTF47: LBL :RDAYC: keeps the reference station's day (REVR, RVD): the High Water keys no longer reload and
  recompute it; ATIDE gets the nearest station's events back from REVH when HR is still its. LBL :LINE: by steps
  (11 a pixel, was 24): it was 45-55 % of a FLOW / ARTF key.
- Steps (simulator): a TIDE47 day 22 466 -> 16 288; an ARTF47 High Water key 43 117 -> 30 450; FLOW47 21 188 ->
  17 774. Element cosines / sines a day 2 320 -> 1 040. The start is unchanged (about 52 000 steps, half of it LBL
  :ROW: unpacking DM UM EM; a whole-matrix MOD unpacking was tried and left: the 20-digit packed numbers need the
  C47's real34 elements, the simulator's matrices keep doubles).
- T47TIME (programs_rem/T47TIME.txt; build_tide47.py writes build/ programs/): the firmware's times on the calculator.
- v0.4.1 (Victor's C47: "not enough memory for such a matrix" in TIDE47, FLOW47, ARTF47): the curve's weights B0 B1
  B2 (3 x 73 x 13) and E1-E6 gone; LBL :CRV6: makes the 73 values from CU x SP6 (12 x 6, SP6 7 x 6) with a copy loop
  (about 600 steps). Matrix elements at a key wait: TIDE47 6 776 (v0.3: 8 831, v0.4.0 about 9 000), ARTF47 7 084
  (v0.3: 9 294). The largest left: S (NK x 60, 2 400 for 40 constituents).
- v0.4.1 (Victor's c47 simulator, an Aramco station with 50 constituents: "Out of range" storing the selection matrix S,
  50 x 60): S gone; LBL :GATH: picks the port's NK constituents out of a 60-vector with a loop (VU, EL a day; WK, LWK
  a port). Matrix elements at a key wait: TIDE47 4 416, ARTF47 4 724 (v0.3: 8 831 and 9 294). Not measured by
  c47sim (it has no memory limit): the C47's own simulator is the check.
- FV is the C47's reserved TVM variable (future value, a real only): ARTF47 stopped at STO "FV" with "Invalid input
  data type for this operation" (Victor's c47 simulator, step 3771). The atlas's 13 streams are STU STV now; the build
  refuses the reserved names (FV PV PMT ACC NPPER I%/a ... STATS HISTO Mat_A ...: build_tide47.RESERVED).
- The cost of LBL :GATH: (no S): a TIDE47 day 21 415 steps in the simulator (v0.4.0 16 288, v0.3 22 466); the element
  cosines and sines stay at 1 040 a day (v0.3: 2 320).

## Nov 1, 2026 - speed3 (branch claude/tide47-speed3)

- Victor's C47: T47PLOT's pixel loop (360 dots, about 22 steps each) took 25 ticks: about 0.3 ms a step on the
  calculator (the simulator's model says 0.17).
- One gather loop for two vectors (LBL :PAIR: makes [a b] 60 x 2 with C1 C2; LBL :GATH: copies the port's rows; K1 K2
  take the columns apart): VU and EL a day, WK and LWK a port.
- ARTF47's tide panel: the curve as dots from CU x SPX (every other column of PY), not 72 LINEs.
- The chart's dotted grid every 12 pixels (was 6), the panel's time axis every 4 (was 2).
- Steps (simulator): a TIDE47 day 21 415 -> 16 994; the start 53 600 -> 50 272; an ARTF47 High Water key 33 838 ->
  25 199.
- Refactoring: LBL :HSMM: (the curve's lowest and highest, read in order with J+) shared by the chart and ARTF's panel;
  LBL :HSROT: (a rotary stream's speed from HS HSV) apart. A day 16 994 -> 16 125 steps, an ARTF key 25 199 -> 24 549.

## Nov 2, 2026 - the web app (branch claude/tide47-web)

- web/tide47.js: the twin's astronomy line for line, exact evaluation (the event function every 5 minutes, bisected);
  data from tools/make_web_data.py (cons.js from tide47ref.CONS and K: one source; public.js; private.js git-ignored).
- web/index.html + app.js: regions, stations, the day's curve (SVG sized to the screen), events, now, the nearest
  station to a position, a file picker for private.js; light and dark.
- tests/test_web.py: 640 station-days against the twin: the same events within 0.01 s, curve 1E-14 m.
