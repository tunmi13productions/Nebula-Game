"""Builds the game data tables in data/ from the original bundle.

- ships.json: every enemy type's stats, read by running the original constructor in the emulator.
- ship_sounds.json: ShipSounds.plist (engine loop per ship code).
- textures.json: texture sizes from the gameTextures atlas, which hitbox and position maths depend on.

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


def main():
    save('ships.json', ships())
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
