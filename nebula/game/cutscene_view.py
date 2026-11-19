"""The pictures of the chapter intro cutscenes, played back from data/cutscenes.json. Visual only.

tools/re/extract_cutscenes.py traced each cutscene in the emulator and stored its node operations in
segments: "main" runs when the narration starts, each narration part names the segment that runs when the
part ends, and each action run with a completion names the segment that runs when the action ends. This
module replays them on a root node that covers the screen in black (the CutScene node, z 999.5).

The title card (capIntroWithName) is drawn here by hand from its trace: "Chapter %@" in white Futura 20 at
(160, 340.8) and the chapter title in Futura 30 at (160, 240.8), fading in over 1.5 and 2 seconds, then both
fading out over 2 from 5 seconds in.
"""
import json
import os

from ..engine import actions as A
from ..engine.nodes import Node

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data',
                     'cutscenes.json')
_CUTSCENES = None


def cutscene_data(chapter):
    global _CUTSCENES
    if _CUTSCENES is None:
        with open(_DATA, encoding='utf-8') as f:
            _CUTSCENES = json.load(f)
    return _CUTSCENES[str(chapter)]


def _action(defs, ident):
    d = defs[ident]
    kind, a = d['type'], d.get('args', [])
    items = [_action(defs, i) for i in d.get('items', []) if i in defs]
    if kind == 'sequence':
        return A.sequence(items)
    if kind == 'group':
        return A.group(items)
    if kind == 'forever':
        return A.repeat_forever(items[0]) if items else A.wait(0)
    if kind == 'fadeInWithDuration:':
        return A.fade_alpha_to(1.0, a[0])
    if kind == 'fadeOutWithDuration:':
        return A.fade_alpha_to(0.0, a[0])
    if kind == 'fadeAlphaTo:duration:':
        return A.fade_alpha_to(a[0], a[1])
    if kind == 'moveByX:y:duration:':
        return A.move_by(a[0], a[1], a[2])
    if kind == 'moveTo:duration:':
        return A.move_to(a[0], a[1], a[2])
    if kind == 'moveToX:duration:':
        return A.move_to_x(a[0], a[1])
    if kind == 'moveToY:duration:':
        return A.move_to_y(a[0], a[1])
    if kind in ('scaleBy:duration:', 'scaleXBy:y:duration:'):
        return A.scale_by(a[0], a[-1])
    if kind == 'scaleTo:duration:':
        return A.scale_to(a[0], a[1])
    if kind == 'rotateByAngle:duration:':
        return A.rotate_by(a[0], a[1])
    if kind == 'resizeToWidth:height:duration:':
        return A.resize_to(a[0], a[1], a[2])
    if kind == 'resizeByWidth:height:duration:':
        return _ResizeBy(a[0], a[1], a[2])
    if kind == 'waitForDuration:':
        return A.wait(a[0])
    return A.wait(a[-1] if a else 0.0)


class _ResizeBy(A.resize_to):
    def __init__(self, dw, dh, duration):
        super().__init__(0.0, 0.0, duration)
        self.dw, self.dh = dw, dh

    def begin(self, node, state):
        state['start'] = node.size
        self.width, self.height = node.size[0] + self.dw, node.size[1] + self.dh


class CutSceneView:
    def __init__(self, scene, chapter, strings):
        W, H = scene.size
        self.data = cutscene_data(chapter)
        self.root = Node(name='CutScene', size=(W, H), position=(0.0, 0.0))
        self.root.anchor, self.root.color, self.root.z = (0.0, 0.0), (0.0, 0.0, 0.0, 1.0), 999.5
        self.nodes = {'root': self.root}
        scene.add_child(self.root)
        self._title(chapter, strings, W)

    def _title(self, chapter, strings, W):
        from .cutscene import roman
        number = Node(name='label', position=(W / 2, 340.8))
        number.text, number.font_size, number.font_name = strings.format('chapterNNumber', roman(chapter)), 20, 'Futura'
        title = Node(name='label', position=(W / 2, 240.8))
        title.text, title.font_size, title.font_name = strings.get('cap%d_title' % chapter), 30, 'Futura'
        for n in (number, title):
            n.font_color, n.alpha, n.z = (1.0, 1.0, 1.0), 0.0, 1
            self.root.add_child(n)
        number.run(A.sequence([A.fade_alpha_to(1.0, 1.5), A.run_block(lambda: title.run(A.fade_alpha_to(1.0, 2.0)))]))
        number.run(A.sequence([A.wait(5.0), A.fade_alpha_to(0.0, 2.0)]))
        title.run(A.sequence([A.wait(5.0), A.fade_alpha_to(0.0, 2.0)]))

    def narration_starts(self):
        self.run_segment('main')

    def part_ended(self, index):
        parts = self.data['parts']
        if 0 <= index < len(parts):
            self.run_segment(parts[index]['then'])

    def remove(self):
        self.root.remove_all_actions()
        self.root.remove_from_parent()

    def run_segment(self, name):
        for op in self.data['segments'].get(name, []):
            kind = op['op']
            if kind == 'create':
                n = Node(name='cutscenePicture')
                n.texture = op.get('texture')
                if 'size' in op:
                    n.size = tuple(op['size'])
                self.nodes[op['node']] = n
                continue
            node = self.nodes.get(op['node'])
            if node is None:
                continue
            if kind == 'set':
                v = op['value']
                prop = op['prop']
                if prop == 'size' and len(v) >= 2:
                    node.size = (v[0], v[1])
                elif prop == 'position' and len(v) >= 2:
                    node.position = (v[0], v[1])
                elif prop == 'anchorpoint' and len(v) >= 2:
                    node.anchor = (v[0], v[1])
                elif prop == 'alpha' and v:
                    node.alpha = v[0]
                elif prop == 'zposition' and v:
                    node.z = v[0]
                elif prop == 'scale' and v:
                    node.scale = v[0]
            elif kind == 'add':
                parent = self.nodes.get(op['parent'], self.root)
                parent.add_child(node)
            elif kind == 'run':
                if op['action'] not in self.data['actions']:
                    continue
                action = _action(self.data['actions'], op['action'])
                then = op.get('then')
                node.run(action, completion=(lambda t=then: self.run_segment(t)) if then else None)
            elif kind == 'removeAllActions':
                node.remove_all_actions()
            elif kind == 'removeFromParent':
                node.remove_from_parent()
