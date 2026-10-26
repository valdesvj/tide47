# Tide 47: working rules

- Work on a new branch; Victor creates and merges the PRs. Never force-push or rewrite history.
- Commit author: "Victor Valdes" <valdesvj@users.noreply.github.com>.
- Never commit binaries (.p47 files made by rejig).
- Edit the program in programs_rem/TIDE47.txt (commented source), then run python3 tools/build_tide47.py:
  it writes programs/, build/ and listings/ (TIDE47 and the data programs TIDEME TIDEUS TIDELA TIDECU). Never edit those by hand.
- The build fills REM ==== CONS / NCONS and the {NAME} constants from python/tide47ref.py; the data programs come from
  python/stations.py, written by tools/make_stations.py (XTide's text and TICON_3.txt), and python/streams.py, written by
  tools/make_streams.py (XTide's text); never edit stations.py or streams.py by hand.
- STRUCT as Elements 47: IF / ELSE / ENDIF, DO / WHILE / ENDDO, indented, no numbers in the source; a test
  right before IF / WHILE; never a test before ELSE, ENDIF, DO, ENDDO. TIDE47 is for the C47 / R47 / DM42n
  (255 IF / DO a program). Named labels LBL :NAME: (1-7 letters or digits).
- The engine has a twin: python/tide47ref.py (day() and sday() for the streams, the same steps). A change to the engine goes in both;
  tests/test_tide47.py compares them and checks the astronomy against NOAA (tests/xtide_tables.json).
- Text on the C47 screen: ATEXT in GRFNT 21 (GRFNT 10 for the small text). Restore GRFNT 20 and GRMOD 0 before
  the program ends. GRMOD and GRFNT take X: write `21 GRFNT`.
- Key waits: DO / PAUSE 50 / KEY? 98 / WHILE / ENDDO (as Elements 47).
- Only commands already run on a C47 in Almanac 47, Elements 47, Zones 47 or Logic 47, except LN: say so in the README
  until Victor has run it; a new command: ask Victor to try it.
- Check every change in the simulator (python3 python/tide47sim.py writes docs/*.png) and with
  python3 tests/test_tide47.py.
- python/c47sim.py, stdfont.py, tinyfont.py come from Almanac 47 (LN and e^x added here, marked tide47): a fix is
  made there first, then copied here.
- The data's terms (NOTICE): NOAA public domain (attribution), TICON-3 CC-BY 4.0. No Admiralty (UKHO) or Aramco data in
  the repo: private stations stay in private/ and python/stations_private.py, python/streams_private.py (git-ignored;
  docs/ARAMCO.md, docs/STREAMS.md). No GEOSA data in the repo either, nor the tidal stream atlas of FLOW47
  (private/atlas/, python/flow_private.py, TIDEFL: docs/FLOW.md); its pictures in docs/ use a synthetic atlas.
- TIDE47.txt holds two programs' entries, LBL "TIDE47" and LBL "FLOW47", sharing the engine (LBL :DAYC:).
- Work in one repository at a time (this one); the other 47 repositories are for reference only.
- Ask before anything that can't be undone. Pull requests only for tide47.
