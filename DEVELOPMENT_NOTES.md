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

## Oct 26, 2026 - the data programs found at the start (branch claude/tide47-probe)

- Victor: one TIDE47 that works with whichever data programs are loaded (only TIDEAR, to save memory), with a version
  check. LBL :PROBE: (end of INIT, a block a region written by the build, REM ==== PROBE): 0 STO 93 STO 96, LBL?
  "TIDEME" (new: the firmware's fnCheckLabel, item 1503), XEQ "TIDEME" with X = 0; R96 set: loaded; R93 = the number
  of constituents (the data programs now set it at X = 0; older ones do not): this version. R79 = the sum of
  2^(region - 1); + skips the others (LBL :HAS:); an older one: OLD DATA, REBUILD: TIDEUS for 3 s; none: NO TIDE DATA
  PROGRAM LOADED, then the usual end. The --regions build stays (a smaller TIDE47).
- c47sim: LBL? as a test (marked tide47); tide47sim.run(progs=). tests: TIDEUS alone, TIDEME + TIDELA, an older TIDEUS,
  TIDE47 alone; by hand: the private TIDE47 with TIDEAR alone opens on ARAMCO.

## Oct 26, 2026 - the forum files for new users (branch claude/tide47-forum)

- The forum asked contributors for plain-English instructions in the .p47u ('@' lines, not '#': rejig makes a '#'
  line a REM step) and local labels. tools/build_forum.py (from Chess 47's), run by the build: build/forum/TIDE47.p47u
  (the '@' metadata, tools/forum/TIDE47.txt, the source's header as technical notes, the comment blocks as '@' lines,
  label names after ';') and one file per data program (tools/forum/DATA.txt with its region and ports, each port's
  LBL named after ';'); with --private also private/build/forum/TIDEAR.p47u (git-ignored).
- tools/build_p47.py (with rejig on Victor's computer): build/p47/*.p47, each checked against the plain listing's;
  --private: private/build/p47/ (TIDE47 of the private build from its plain listing). tests/test_forum.py.

## Oct 25, 2026 - v0.2.0: tidal streams (branch claude/tide47-streams, from claude/tide47-aramco)

- Victor: tidal flow at the Aramco fields, as accurate as possible; the data from GEOSA's Saudi Tidal Currents Tables
  (private, as Aramco's tide tables), all the Gulf fields. TICON-3 and NOAA have no Gulf stream station.
- Two kinds of station: rectilinear (NOAA's, and tables of slack and max flood / ebb: the speed along the flood axis,
  + flood, - ebb, with NOAA's flood and ebb sets, not always opposite) and rotary (u east, v north). R28 = DST bit
  + 2 rotary / + 4 rectilinear (:TZ: takes R28 MOD 2); R79 = flood + ebb / 1000, or V0; HV the north matrix.
- One event finder for both: g = u u' + v v' (= s s') changes sign in the hour, four Newton steps g / g',
  g' = u'^2 + v'^2 + u u'' + v v'' (u' = -AW . SIN, u'' = -AW2 . COS as for the tides): a maximum when g' < 0, a
  minimum (a slack on a rectilinear station) when g' > 0; at most 8 a day into the matrix EV (time, value, set,
  kind), read with INDEX / RCLEL / J+ (the registers R60-R77 hold only 6). The set: ->POL of (v, u) (Y = u, X = v:
  atan2(u, v)); rectilinear: the flood or ebb set by the sign of u (a slack's set is not shown: u is 1E-15 there).
- Refactored without changing the tides' numbers: LBL :UNPK: (a port's matrix -> G, LH), LBL :VEC: (G, LH -> P A AW
  AW2 from VU = DM AV + UM BV and EL = EM LF, the same sums in the same order). Tests 3: still identical to the twin.
- The curve: LBL :VAL: (the value without derivatives: 4.8 s a stream day instead of 5.1); the scale steps 0.5 / 1 / 2
  (2 over a range of 6: Deception Pass, 13 kn); 0 always in a stream's range.
- The stream variables are made at the start (0 STO "HV" ...) so the end's DELITM never meets a missing one (c47sim
  does not check that; the firmware might). "C" renamed "CZ" (not to be confused with the lettered register C).
- tools/make_streams.py: 7 NOAA current stations (knots; Hell Gate is knots^2, hydraulic: left out) -> TIDECU.
- tools/make_private_streams.py: least squares as make_private.py; rectilinear: SLACK s = 0, FLOOD / EBB s = +-speed
  and s' = 0 (weight 1 h), timed speeds signed by the set; rotary: u = sp sin set, v = sp cos set and at MAX / MIN
  u_obs u' + v_obs v' = 0 (linear). The axis from the header or the principal axis of the sets. --test-from compares
  the rows it left out (private/STREAMS_COMPARE.md).
- tests/synth_streams.py: tables from Pollock Rip's real constants (clock moved to UTC+3) and from a synthetic rotary
  station (invented constants, labelled so): a year fitted, the next predicted: rect 0.3 min / 0.03 kn rms, rot
  1.0 min / 0.03 kn (the tables' 0.1 kn rounding). Tests 5 also run the rotary station on the C47 through a
  private-style build (identical to the twin: 4E-9 s, 3E-13 kn, 5E-12 deg).

## Oct 26, 2026 - v0.3 speed (branch claude/tide47-streams)

- Victor: TIDE47 is very slow on the calculator. The step counts hid the work: one COS of a 60-vector is one step but
  60 34-digit cosines; v0.2 did about 8 000 element cosines / sines a day (73 curve points, 25 hourly h', 4 Newton
  steps x 2 an event).
- Only the port's constituents: the data programs carry the non-zero ones (packed: number in the 60 x 1E11 + H x 1E5 +
  g / 100; NK of them); LBL :SEL: makes the selection matrix S (NK x 60) and WK = S x W, LWK = S x LW; each day
  VU = S x (DM AV + UM BV), EL = S x EM x LF. Exact: the dropped ones are zero. 15-40 of 60.
- One exact evaluation an hour (LBL :HOURS:: :UV: gives u u' u'' from one COS and one SIN, v likewise): HR 25 x 8 with
  the event function F, F' (LBL :FF:: a tide h', h''; a stream g = u u' + v v', g'). LBL :FIND: / :ROOT:: where F
  changes sign, the Hermite cubic of F (F and F' at the two hours), three Newton steps on it, then ONE exact Newton
  step; the value at the event u + u' dx. Kind: F' < 0 a maximum (both modes).
- The curve: HS = B1 x (HR x E1) + B2 x (HR x E2), B1 B2 constant 73 x 25 Hermite weights (made at the start), E1 E2
  pick columns; a rotary stream: v likewise, the speed with ->POL in the min / max loop.
- Against the exact v0.2 method (kept as tide47ref.day_exact / sday_exact, tests 3a): tides 0.06 s and 2E-6 m, the
  curve 0.8 mm; streams 1 s (16 s worst over 60 days), 0.0004 kn. The C47 = the twin as before (tests 3, 5).
- Work a day: Bahrain 2 320 element trig (from 8 040), Boston 1 680 (7 500); steps 22 500 (20 000).

## Oct 26, 2026 - FLOW47: the tidal stream atlas at a position (branch claude/tide47-streams)

- Victor sent "Arabian Gulf Tidal Flow" (Mermaid Asiana 2022, a copy of a Saudi document, source unknown): 13 charts
  HW-6 ... HW+6, Safaniya to Dammam, the spring speed as five colour bands; the reference port not named. Victor:
  take Ras Tanura (the Aramco constants of the private build); a program: lat / lon -> 13 rows (set, knots, arrows)
  in a split view; the wind correction.
- tools/digitize_atlas.py: pages at 200 dpi; upside-down pages found by where the white land and legend are (the
  tick fit first chosen wrongly: spurious ticks); graticule from the frame lines (Hough) and the ticks (darkness
  just outside), Mercator fit 2.8-4.9 px rms; arrows: dark against the local median (and g < 125 for the thick
  brown ones, saturated: first missed), not blue text / red pipelines, 3x3 dilation joins faint shafts, PCA axis,
  head = the wider third; neighbour consensus turns heads read backwards. Speed: the background colour, nearest of
  the band colours in Lab (white: from neighbours). 420-555 arrows a chart.
- The charts are one cycle with a daily inequality: HW-6 and HW+6 correlate 0.32 only (mean speed 0.18 vs 0.55 kn);
  consecutive hours 0.6-0.87. Used as they are (Admiralty practice), the range scaling for the size only.
- tools/make_flow.py: a 10' grid (19 x 13, 192 sea), Gaussian-weighted arrows within 7.5', sea where half the charts
  have an arrow near; u, v rounded to 0.05 kn, packed 2 digits each (+50), 7 hours in one number (28 digits), 6 in a
  second: the data program TIDEFL (matrix FL, 247 x 2; about 13 KB).
- FLOW47 (LBL "FLOW47" in TIDE47.txt; LBL :DAY: split into :DAYC: + :SCREEN:; the end in LBL :END:): INPUT LAT LON
  (DD.MMm, Almanac 47's variables) WDIR WKN; :ATLAS: bilinear over the sea corners (:CORN: :DEC: unpack from the
  right); :SPRNG: 2 (H M2 + H S2); :PICK: the HW nearest an hour (6.2 h rule to the next / previous day), :FNEXT:
  :FPREV:, :CYC: the factor range / spring range; the screen: header, 13 rows (tiny font, :GLYPH: :ARROW: :LINE:),
  the rose (rings, cross, the 13-point curve, the bold NOW arrow). Bugs found in the simulator: FLOOR uses R90 (the
  NOW flag) -> ceil and the marker without it; :FNOWV: overwrote R55 (pixels a knot) -> kept in R58; :GLYPH: uses
  R56 -> the marker from R58.
- Tests 6: a synthetic atlas (tests/synth_flow.py), Mina Salman as the reference: the C47 = tide47ref.flow_* through
  the keys (2E-9), land and outside give "no atlas", the end clean. The first screen 62 000 steps, a new HW 27 000.

## Oct 26, 2026 - streams, v0.3 speed and FLOW47 merged with the probe and the forum (branch claude/tide47-flow)

- From claude/tide47-v01 (the probe, the forum files) with claude/tide47-streams merged. Conflicts: R79 (the probe's
  bitmask of the data programs found vs the streams' directions / V0) -> the streams' value in the variable SDIR;
  R93: the data version DATAVER = 3060 (v0.3's packed format x 1000 + 60 constituents; an older data program is left
  out: OLD DATA, REBUILD). TIDE47.txt v0.3.0.
- FLOW47 built apart (Victor): its entry and routines between REM ==== FLOW { / }, stripped by every build but
  --flow, which writes private/build_flow/ (TIDE47 with FLOW47, TIDEFL, all the data programs). FLOW47 checks the
  reference's data program is loaded (LBL :HAS:), else FLOW47: LOAD TIDEAR.
- The rose's cost (Victor asked): a new High Water 26 700 steps with it, 18 000 without (the hodograph's lines are
  most of it, pixel by pixel); the vector trig of LBL :DAYC: is the same either way.

## Plans

- Tidal streams: done (v0.2.0). Next: the GEOSA tables (Victor) -> private/streams/; the vessel's own DP / ADCP
  current logs could be fitted the same way (hourly rows: speed and set).
- More ports: TICON-3 has 3 363 gauges; a region program per area.
- The tide at a given time (key 7), the next high / low water from now, spring / neap (the M2 - S2 phase).
- Free42 / DM42 build later.
