"""Runs each boss's own attack block for a number of ticks and prints, per tick, where it fires bullets
(shootingOnPosition:) and lasers (laserShootOnPosition:), relative to the boss position.

usage: python tools/re/trace_boss_attacks.py [ticks]
"""
import io
import random
import re
import sys

sys.path.insert(0, 'tools/re')
from objc_trace import Tracer, u32f  # noqa: E402

TICKS = int(sys.argv[1]) if len(sys.argv) > 1 else 12
for code in range(1, 11):
    buf = io.StringIO()
    t = Tracer('decompiled/ipa/Payload/BEPiDGame.app/BEPiDGame', out=buf)
    scene = t.new_object('Chapter1Scene')
    t.send(scene, 'initWithSize:', u32f(320.0), u32f(568.0))
    t.send(scene, 'setIsActive:', 1)
    t.skip_impl.update({'shootingOnPosition:', 'laserShootOnPosition:', 'entranceAction', 'startingMove', 'defineBody'})
    boss = t.new_object('Boss')
    first = len(t.blocks)
    t.send(boss, 'initBoss:onParentScene:', code, scene)
    t.pos[boss] = (160.0, 568.0)
    w, h = t.sizes.get(boss, (0, 0))
    attack = next(i for i, b in enumerate(t.blocks) if i >= first and b[2] == 'runBlock:')
    rng = random.Random(code)
    t.rand_source = lambda: rng.getrandbits(32)
    print('== boss %d  size (%g, %g)' % (code, w, h))
    for k in range(TICKS):
        buf.seek(0); buf.truncate()
        t.run_block(attack)
        out = []
        for line in buf.getvalue().splitlines():
            m = re.search(r'(shootingOnPosition|laserShootOnPosition): \(([-\d.e]+), ([-\d.e]+)\)', line)
            if m:
                kind = 'shot' if m.group(1).startswith('shooting') else 'LASER'
                x, y = float(m.group(2)), float(m.group(3))
                out.append('%s(%+.2f, %+.2f)' % (kind, x - (160.0 if kind == 'shot' else 0), y - (568.0 if kind == 'shot' else 0)))
            elif 'arc4random' in line:
                out.append('rnd')
        print('  tick %2d: %s' % (k + 1, ' '.join(out)))
