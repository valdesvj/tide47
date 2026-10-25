# AI Assistance Policy

## How this project uses AI

This project was **developed with the help of AI**: Claude (by Anthropic) wrote the engine of v0.1.0 with me. AI assisted with the tide method, the program structure, the RPN listing and the documentation, but I reviewed all output, validate the results against independent references and the C47 simulator, and take full responsibility for the work and any mistakes.

## Responsible use

- ✅ **I check the results** - The astronomy is checked against NOAA's tables (as in XTide), the predictions against an independent harmonic analysis (UTide), and the C47 program against `python/tide47ref.py` step for step
- ✅ **I maintain domain expertise** - As a Master Mariner in offshore operations I guide what is shown, the ports and the datums
- ✅ **I take full responsibility** - The work is mine; any errors are mine to fix
- ✅ **I'm transparent** - This file documents how AI was used

## Testing & Validation

- tests/test_tide47.py: the astronomy against NOAA (XTide's tables 2020-2040), the twin against UTide, the C47 program in the Python C47 simulator (from Almanac 47) against the twin for every port on three days
- To be tested on real C47 / R47 hardware before each release, and compared with official tide tables

## License

This does not affect the GNU GPL-3.0 license. All code remains open-source and fully accessible.

---

*For more details, see the development notes as they are added.*
