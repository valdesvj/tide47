

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
