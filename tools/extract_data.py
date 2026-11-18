"""Builds the game data tables in data/ from the original bundle.

- ships.json: every enemy type's stats, read by running the original constructor in the emulator.
- ship_sounds.json: ShipSounds.plist (engine loop per ship code).
- textures.json: texture sizes from the gameTextures atlas, which hitbox and position maths depend on.
- bosses.json: per boss, from running initBoss:onParentScene: and its entrance completion in the emulator:
  size, start position, entrance target and duration, movement loop, attack interval and hitbox outline.

usage: python -I tools/extract_data.py   (run from the repository root, with the ipa unpacked in decompiled/ipa)
"""
import io
import json
import os
import plistlib
import re
import struct
import sys

sys.path.insert(0, os.path.join('tools', 're'))
from objc_trace import Tracer  # noqa: E402

APP = os.path.join('decompiled', 'ipa', 'Payload', 'BEPiDGame.app')
BINARY = os.path.join(APP, 'BEPiDGame')
LASER = {3, 5, 7, 8, 15, 23, 27, 30, 42, 100, 101, 102}


def save(name, data):
    with open(os.path.join('data', name), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write('\n')


def ships():
    t = Tracer(BINARY, out=io.StringIO())
    t.skip_impl.add('createEnemyWithLife:withScore:withShootingTime:andMovmentTime:inParentView:')
    found = {}
    for code in list(range(0, 51)) + list(range(100, 106)):
        obj = t.new_object('SpaceShip')
        buf = io.StringIO(); t.out = buf
        t.send(obj, 'initEnemyOfType:inParentView:', code, 0)
        m = re.search(r'createEnemyWithLife:withScore:withShootingTime:andMovmentTime:inParentView: (-?\d+) (-?\d+) ([\d.e-]+) ([\d.e-]+)', buf.getvalue())
        damage = struct.unpack('<i', bytes(t.mu.mem_read(obj + 108, 4)))[0]
        life, score, fire, move = int(m.group(1)), int(m.group(2)), float(m.group(3)), float(m.group(4))
        found[str(code)] = {'life': life, 'score': score, 'fire_interval': round(fire, 3), 'move_interval': round(move, 3),
                            'damage': damage, 'laser': code in LASER}
    return found


BOSS_LIFE_DAMAGE_SCORE = ('getLife', 'getShootDamage', 'getScore')


def bosses():
    from objc_trace import u32f
    out = {}
    for code in range(1, 11):
        buf = io.StringIO()
        t = Tracer(BINARY, out=buf)
        scene = t.new_object('Chapter1Scene')
        t.send(scene, 'initWithSize:', u32f(320.0), u32f(568.0))
        t.send(scene, 'setIsActive:', 1)
        boss = t.new_object('Boss')
        first = len(t.blocks)
        buf.seek(0); buf.truncate()
        t.send(boss, 'initBoss:onParentScene:', code, scene)
        init_log = buf.getvalue()
        entrance_block = next(i for i, b in enumerate(t.blocks) if i >= first and b[2] == 'runAction:completion:')
        buf.seek(0); buf.truncate()
        t.run_block(entrance_block)
        done_log = buf.getvalue()
        num = r'([-\d.e]+)'
        start = re.search(r'<Boss [^>]*> setPosition: \(%s, %s\)' % (num, num), init_log)
        size = re.search(r'<Boss [^>]*> setSize: \(%s, %s\)' % (num, num), init_log)
        entrance = re.search(r'class SKAction moveTo:duration: \(%s, %s\) %s' % (num, num, num), init_log)
        waits = {h: float(v) for v, h in re.findall(r'class SKAction waitForDuration: %s\s+=> (#[0-9a-f]+) ' % num, init_log + done_log)}
        attack = re.search(r'arrayWithObjects:count: \[(#[0-9a-f]+) waitForDuration:, #[0-9a-f]+ runBlock:\] 2', done_log)
        moves = []
        for line in done_log.splitlines():
            m = re.search(r'class SKAction moveByX:y:duration: %s %s %s' % (num, num, num), line)
            if m:
                moves.append(['by', float(m.group(1)), float(m.group(2)), float(m.group(3))])
            m = re.search(r'class SKAction moveTo:duration: \(%s, %s\) %s' % (num, num, num), line)
            if m:
                moves.append(['to', float(m.group(1)), float(m.group(2)), float(m.group(3))])
        outline = [[float(a), float(b)] for a, b in re.findall(r'(?:moveToPoint|addLineToPoint): \(%s, %s\)' % (num, num), done_log)]
        stats = {k: struct.unpack('<i', struct.pack('<I', t.send(boss, k)))[0] for k in BOSS_LIFE_DAMAGE_SCORE}
        out[str(code)] = {
            'size': [float(size.group(1)), float(size.group(2))],
            'start': [float(start.group(1)), float(start.group(2))],
            'entrance': [float(entrance.group(1)), float(entrance.group(2)), float(entrance.group(3))],
            'attack_interval': waits.get(attack.group(1), 1.0) if attack else 1.0,
            'moves': moves,
            'outline': outline,
            'life': stats['getLife'], 'damage': stats['getShootDamage'], 'score': stats['getScore'],
        }
    return out


def main():
    save('ships.json', ships())
    save('bosses.json', bosses())
    with open(os.path.join(APP, 'ShipSounds.plist'), 'rb') as f:
        sounds = plistlib.load(f)
    save('ship_sounds.json', {k.split('_')[-1]: v for k, v in sorted(sounds.items(), key=lambda kv: int(kv[0].split('_')[-1]))})
    with open(os.path.join(APP, 'gameTextures.atlasc', 'gameTextures.plist'), 'rb') as f:
        atlas = plistlib.load(f)
    sizes = {}
    for image in atlas['images']:
        for sub in image['subimages']:
            w, h = re.findall(r'[\d.]+', sub['spriteSourceSize'])
            sizes[sub['name'].rsplit('.', 1)[0]] = [float(w), float(h)]
    save('textures.json', dict(sorted(sizes.items())))
    print('ships', len(json.load(open('data/ships.json'))), 'sounds', len(sounds), 'textures', len(sizes))


if __name__ == '__main__':
    main()
