"""Converts the original SpriteKit particle emitters (.sks keyed archives) into data/emitters.json.

usage: python -I tools/extract_emitters.py   (from the repository root, with the ipa unpacked in decompiled/ipa)
"""
import glob
import json
import os
import plistlib
import re

APP = os.path.join('decompiled', 'ipa', 'Payload', 'BEPiDGame.app')


def load(path):
    with open(path, 'rb') as f:
        p = plistlib.load(f)
    objs = p['$objects']

    def res(v):
        if isinstance(v, plistlib.UID):
            o = objs[v.data]
            if isinstance(o, dict):
                return {k: res(x) for k, x in o.items() if k != '$class'} | {'$class': _cls(o, objs)}
            return None if o == '$null' else o
        if isinstance(v, list):
            return [res(x) for x in v]
        return v
    return res(p['$top']['root'])


def _cls(o, objs):
    c = o.get('$class')
    return objs[c.data]['$classname'] if isinstance(c, plistlib.UID) else None


def nums(text):
    return [float(v) for v in re.findall(r'-?[\d.]+(?:e-?\d+)?', text or '')]


def color(c):
    if c is None:
        return None
    if 'NSRGB' in c:
        v = [float(x) for x in c['NSRGB'].rstrip(b'\0').split()]
        return v + [1.0] if len(v) == 3 else v
    if 'NSWhite' in c:
        w = [float(x) for x in c['NSWhite'].rstrip(b'\0').split()]
        return [w[0], w[0], w[0], w[1] if len(w) > 1 else 1.0]
    return None


def sequence(s, convert):
    if not s:
        return None
    times = s['_times']['NS.objects']
    values = [convert(v) for v in s['_values']['NS.objects']]
    return {'times': times, 'values': values, 'interpolation': s.get('_interpolationMode', 1),
            'repeat': s.get('_repeatMode', 1)}


def emitter(r):
    tex = r.get('_particleTexture') or {}
    return {
        'texture': tex.get('_imgName'),
        'texture_size': nums(tex.get('_pixelSize', {}).get('NS.sizeval')) if tex else None,
        'birth_rate': r['_birthrate'], 'to_emit': r['_numParticlesToEmit'],
        'lifetime': r['_lifetime'], 'lifetime_range': r['_lifetimeVariance'],
        'position_range': nums(r['_startPositionVariance']),
        'emission_angle': r['_emissionAngle'], 'emission_angle_range': r['_emissionAngleVariance'],
        'speed': r['_startSpeed'], 'speed_range': r['_startSpeedVariance'],
        'acceleration': nums(r['_acceleration']),
        'rotation': r['_startRotation'], 'rotation_range': r['_startRotationVariance'],
        'rotation_speed': r['_rotationSpeed'],
        'scale': r['_startScale'], 'scale_range': r['_startScaleVariance'], 'scale_speed': r['_scaleSpeed'],
        'alpha': r['_startOpacity'], 'alpha_range': r['_startOpacityVariance'], 'alpha_speed': r['_opacitySpeed'],
        'color': [r['_startColorR'], r['_startColorG'], r['_startColorB'], r['_startColorA']],
        'color_range': [r['_startColorVarianceR'], r['_startColorVarianceG'], r['_startColorVarianceB'],
                        r['_startColorVarianceA']],
        'color_speed': [r['_colorSpeedR'], r['_colorSpeedG'], r['_colorSpeedB'], r['_colorSpeedA']],
        'color_blend': r['_startColorMix'], 'color_blend_range': r['_startColorBlendVariance'],
        'color_blend_speed': r['_colorBlendSpeed'],
        'color_sequence': sequence(r.get('_particleColorSequence'), color),
        'alpha_sequence': sequence(r.get('_particleAlphaSequence'), float),
        'scale_sequence': sequence(r.get('_particleScaleSequence'), float),
        'blend_mode': r['_particleBlendMode'],
        'z': r['_zPosition'],
    }


def main():
    out = {}
    for path in sorted(glob.glob(os.path.join(APP, '*.sks'))):
        out[os.path.splitext(os.path.basename(path))[0]] = emitter(load(path))
    with open(os.path.join('data', 'emitters.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=1)
        f.write('\n')
    print(len(out), 'emitters')


if __name__ == '__main__':
    main()
