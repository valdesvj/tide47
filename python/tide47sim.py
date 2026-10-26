"""tide47sim.py - run build/TIDE47.txt (with the data programs TIDEME TIDEUS TIDELA) in the C47 simulator
(c47sim.py, from Almanac 47) and turn its screens into pictures.
  run(keys, clock)   the screens shown while TIDE47 waits for a key, and the simulator (its registers, matrices);
                     clock = the calculator's date and time as a JD of the local time
  events(c)          the high and low waters the C47 found: [(hours, metres, +1 high / -1 low)]
  png(fn, pix)       a PNG of one screen (LCD colours, 3 pixels per C47 pixel)
  python3 python/tide47sim.py   writes the screens in docs/ and prints the step counts"""
import os, struct, sys, zlib
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import c47sim

PROGS = [os.path.join(ROOT, 'build', n + '.txt') for n in ('TIDE47', 'TIDEME', 'TIDEUS', 'TIDELA')]
W, H = 400, 240
LCD_BG, LCD_ON = (199, 205, 186), (34, 38, 30)
UP, DOWN, LEFT, RIGHT, TODAY, REGION, WEEKB, WEEKF, END = 53, 73, 62, 64, 63, 85, 72, 74, 82
STEP_MS = 0.17                                   # ms a step on the C47 (Almanac 47's measure)
CLOCK = 2461339.0 + 1 / 24                        # 2026-10-25 13:00 (c47sim's clock: a JD of the local time, .0 = noon)


def run(ks, clock=CLOCK, maxsteps=10 ** 9, progs=None):
    """progs: the programs loaded (default all four: TIDE47 and the three data programs)"""
    c = c47sim.load(progs or PROGS)
    c.s = [D(0)] * 4; c.pix = []; c.keys = list(ks) + [END]; c.steps = 0; c.clock = clock
    c.at_steps = []

    class F(list):
        def append(self, f): c.at_steps.append(c.steps); super().append(f)
    c.frames = F()
    c.ev = []                                     # the events at each key wait

    def hook(op, x):
        if op == 'KEY?' and (not c.ev or c.ev[-1][0] != len(c.frames)):
            c.ev.append((len(c.frames), events(c), int(c.reg.get('25', 0)), c.reg.get('26')))
    c.count = hook
    c.run('TIDE47', maxsteps=maxsteps)
    shots = [{(x, H - 1 - y) for y, x in f if 0 <= y < H and 0 <= x < W} for f in c.frames]
    return shots, c


def events(c):
    n = int(c.reg.get('78', 0))
    return [(float(c.reg['%d' % (60 + i)]), float(c.reg['%d' % (66 + i)]), int(c.reg['%d' % (72 + i)])) for i in range(n)]


def png(fn, pix, scale=3, border=12):
    w, h = W * scale + 2 * border, H * scale + 2 * border
    buf = bytearray(bytes(LCD_BG) * (w * h))
    dot = bytes(LCD_ON) * scale
    for x, r in pix:
        for dy in range(scale):
            o = ((border + r * scale + dy) * w + border + x * scale) * 3
            buf[o:o + len(dot)] = dot
    raw = b''.join(b'\x00' + bytes(buf[y * w * 3:(y + 1) * w * 3]) for y in range(h))

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    with open(fn, 'wb') as fh:
        fh.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                 + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def secs(steps):
    return steps * STEP_MS / 1000.0


if __name__ == '__main__':
    os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True)
    shots, c = run([])
    print('start: %d steps (%.1f s on the C47)' % (c.steps, secs(c.steps)))
    png(os.path.join(ROOT, 'docs', 'TIDE47_bahrain.png'), shots[0])
    shots, c = run([DOWN])
    png(os.path.join(ROOT, 'docs', 'TIDE47_muscat.png'), shots[-1])
    print('a port: %d steps (%.1f s)' % (c.at_steps[1] - c.at_steps[0], secs(c.at_steps[1] - c.at_steps[0])))
    shots, c = run([REGION])
    png(os.path.join(ROOT, 'docs', 'TIDE47_boston.png'), shots[-1])
    shots, c = run([REGION, REGION, DOWN, DOWN, DOWN])
    png(os.path.join(ROOT, 'docs', 'TIDE47_balboa.png'), shots[-1])
    print('docs/TIDE47_*.png written')
