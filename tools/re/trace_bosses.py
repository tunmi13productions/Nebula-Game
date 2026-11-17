import sys, os, io
sys.path.insert(0, sys.argv[1])
from objc_trace import Tracer
outdir = sys.argv[3]; os.makedirs(outdir, exist_ok=True)
NOISE = ('NSNotificationCenter', 'UserDefaults', 'objectForKey', 'setObject:forKey', 'NSBundle', 'NSURL', 'mainBundle',
         'initFileURL', 'physicsBody  ', 'setRestitution', 'setBlendMode', 'setColor', 'colorWith', 'NSNumber',
         'currentDevice', 'unarchiveObjectWithFile: set', 'setParticle', 'AurealAudioObject', 'prepareToPlay', 'setKeyName')
for code in range(1, 11):
    buf = io.StringIO()
    t = Tracer(sys.argv[2], out=buf)
    buf.truncate(0); buf.seek(0)
    scene = t.new_object('Chapter1Scene'); t.send(scene, 'setIsActive:', 1)
    boss = t.new_object('Boss')
    t.send(boss, 'initBoss:onParentScene:', code, scene)
    n = 0
    seen = set()
    while n < len(t.blocks) and n < 60:
        h, inv, label = t.blocks[n]
        if inv in seen and label == 'runBlock:': n += 1; continue
        seen.add(inv)
        for rv in (range(6) if n == 0 else (0,)):
            t.rand_value = rv
            if n == 0: t.log('-- random value %d' % rv)
            t.run_block(n)
        n += 1
    lines = [l for l in buf.getvalue().splitlines() if not any(k in l for k in NOISE)]
    open(os.path.join(outdir, 'boss_%02d.txt' % code), 'w').write('\n'.join(lines) + '\n')
    print(code, len(lines))
