"""Traces every chapter intro cutscene in the emulator and writes its pictures as data, data/cutscenes.json.

The log of CutScene playIntroCutSceneChapter:completition: (with every captured block run) is split into
segments: "main" (what executeCutSceneN does when the narration starts) and one per block, keyed by block
number. Each narration part (playAudioFileNamed:completion: or speakSentence...completition:) names the
block that runs when it ends; each runAction:completion: names the block that runs when the action ends.
Segments hold node operations (create, set a property, add, run an action, remove), with the actions
defined alongside. The title card (capIntroWithName) is left to the game, which draws it by hand.

usage: python -I tools/re/extract_cutscenes.py   (from the repository root)
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objc_trace import Tracer, u32f  # noqa: E402

BINARY = os.path.join('decompiled', 'ipa', 'Payload', 'BEPiDGame.app', 'BEPiDGame')

CREATE = re.compile(r"class SK\w+ (spriteNodeWithImageNamed:|spriteNodeWithTexture:size:|spriteNodeWithTexture:|"
                    r"spriteNodeWithColor:size:) (.*?)  => (#\w+)")
INIT_CREATE = re.compile(r"^(#\w+) alloc (initWithImageNamed:|initWithTexture:) (.*?)  => (#\w+)")
ACTION = re.compile(r"class SKAction (\w+:?(?:\w+:)*) ?(.*?)  => (#\w+)")
SET = re.compile(r"^(#\w+) [\w:]+ (setSize|setPosition|setAlpha|setAnchorPoint|setZPosition|setZRotation|setXScale|"
                 r"setYScale|setScale|setHidden): (.*?)(?:  =>.*)?$")
ADD = re.compile(r"^(<CutScene 0x[0-9a-f]+>|#\w+)(?: [\w:]+)? addChild: (#\w+)")
RUN = re.compile(r"^(#\w+|<CutScene 0x[0-9a-f]+>) (?:[\w:]+ )?runAction(?::withKey:)?: (#\w+)")
RUN_DONE = re.compile(r"^(#\w+|<CutScene 0x[0-9a-f]+>) (?:[\w:]+ )?runAction:completion: (#\w+) BLOCK#(\d+)")
SIMPLE = re.compile(r"^(#\w+) (?:[\w:]+ )?(removeAllActions|removeFromParent)\b")
PART = re.compile(r"<CutScene 0x[0-9a-f]+> playAudioFileNamed:completion: L\('(\w+)'\) BLOCK#(\d+)")
SPEAK = re.compile(r"speakSentence:withRate:preUtteranceDelay:postUtteranceDelay:completition: L\('(\w+)'\) .*BLOCK#(\d+)")
SEGMENT = re.compile(r"^== BLOCK#(\d+) ")
TEXNAME = re.compile(r"tex\('([^']+)'\)|'([^']+)'")


def floats(text):
    return [float(v) for v in re.findall(r'-?[\d.]+(?:e-?\d+)?', text)]


def trace(chapter):
    buf = io.StringIO()
    t = Tracer(BINARY, out=buf)
    scene = t.new_object('Chapter1Scene')
    t.send(scene, 'initWithSize:', u32f(320.0), u32f(568.0))
    cs = t.new_object('CutScene')
    t.send(cs, 'init')
    t.pos[cs] = (0.0, 0.0)
    t.sizes[cs] = (320.0, 568.0)
    t.skip_impl.update({'playAudioFileNamed:completion:', 'runBlockOnDifferentThread:withPriority:'})
    t.send(cs, 'playIntroCutSceneChapter:completition:', chapter, 0)
    i = 0
    while i < len(t.blocks) and i < 300:
        t.run_block(i)
        i += 1
    return buf.getvalue().splitlines()


def parse(lines):
    start = next(i for i, l in enumerate(lines) if 'executeCutScene' in l)
    segments, actions, parts, textures = {'main': []}, {}, [], {}
    current = segments['main']
    for line in lines[start + 1:]:
        line = line.strip()
        m = SEGMENT.match(line)
        if m:
            current = segments.setdefault(m.group(1), [])
            continue
        m = CREATE.search(line)
        if m:
            kind, args, node = m.groups()
            tm = TEXNAME.search(args)
            texture = (tm.group(1) or tm.group(2)) if tm else None
            ref = re.match(r'(#\w+)', args)
            if texture is None and ref and ref.group(1) in textures:
                texture = textures[ref.group(1)]
            if args.startswith('#') and ' texture' in args.split(')')[0] and ref:
                texture = textures.get(ref.group(1), texture)
            op = {'op': 'create', 'node': node, 'texture': texture}
            if kind.endswith('size:'):
                nums = floats(args.split(')')[-2] if ')' in args else args)
                if len(nums) >= 2:
                    op['size'] = nums[-2:]
            if kind == 'spriteNodeWithColor:size:':
                op['color'] = True
            textures[node] = texture
            current.append(op)
            continue
        m = re.search(r"^(#\w+) [\w:]+ texture  => (#\w+)", line)
        if m:
            textures[m.group(2)] = textures.get(m.group(1))
            continue
        m = ACTION.search(line)
        if m:
            name, args, ident = m.groups()
            if name in ('sequence:', 'group:'):
                refs = re.findall(r'(#\w+)', args.split(']')[0])
                actions[ident] = {'type': name[:-1], 'items': refs}
            elif name == 'repeatActionForever:':
                actions[ident] = {'type': 'forever', 'items': re.findall(r'(#\w+)', args)[:1]}
            else:
                actions[ident] = {'type': name, 'args': floats(args)}
            continue
        m = SET.match(line)
        if m:
            node, prop, value = m.groups()
            current.append({'op': 'set', 'node': node, 'prop': prop[3:].lower(), 'value': floats(value)})
            continue
        m = ADD.match(line)
        if m:
            parent = 'root' if m.group(1).startswith('<CutScene') else m.group(1)
            current.append({'op': 'add', 'node': m.group(2), 'parent': parent})
            continue
        m = RUN_DONE.match(line)
        if m:
            node = 'root' if m.group(1).startswith('<CutScene') else m.group(1)
            current.append({'op': 'run', 'node': node, 'action': m.group(2), 'then': m.group(3)})
            continue
        m = RUN.match(line)
        if m:
            node = 'root' if m.group(1).startswith('<CutScene') else m.group(1)
            current.append({'op': 'run', 'node': node, 'action': m.group(2)})
            continue
        m = SIMPLE.match(line)
        if m:
            current.append({'op': m.group(2), 'node': m.group(1)})
            continue
        m = PART.search(line) or SPEAK.search(line)
        if m:
            parts.append({'key': m.group(1), 'then': m.group(2)})
    used = {a for seg in segments.values() for op in seg if op['op'] == 'run' for a in [op['action']]}
    def keep(ident, out):
        if ident in out or ident not in actions:
            return
        out[ident] = actions[ident]
        for sub in actions[ident].get('items', []):
            keep(sub, out)
    kept = {}
    for ident in used:
        keep(ident, kept)
    return {'segments': segments, 'actions': kept, 'parts': parts}


def main():
    out = {}
    for chapter in range(1, 10):
        out[str(chapter)] = parse(trace(chapter))
        data = out[str(chapter)]
        print('chapter', chapter, len(data['parts']), 'parts,', sum(len(s) for s in data['segments'].values()), 'operations')
    with open(os.path.join('data', 'cutscenes.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=1)
        f.write('\n')


if __name__ == '__main__':
    main()
