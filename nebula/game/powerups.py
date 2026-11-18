"""PowerUp: the four collectable cubes (see docs/NOTES.md and docs/MODES.md).

Types: 1 life, 2 shield, 3 speed (fast forward), 4 fast shot. A power-up appears at the top edge at a random
x between 50 and W - 50, drifts to y = -H over 10 seconds towards a random x between W/4 and W/2, and is
removed. The scene links a looping radar beep to it so it can be found by ear.
"""
from ..engine import actions as A
from ..engine.nodes import Node
from ..engine.physics import Body, Circle, attach
from .rand import between
from .ship import CAT_PLAYER, CAT_POWERUP

LIFE, SHIELD, SPEED, FAST_SHOT = 1, 2, 3, 4
NAMES = {LIFE: 'LIFE_POWERUP', SHIELD: 'SHIELD_POWERUP', SPEED: 'FF_POWERUP', FAST_SHOT: 'FS_POWERUP'}
DRIFT = 10.0
# the cube's picture: 25 frames looped at 0.05 seconds each (visual only)
FRAMES = {LIFE: 'LifeCube_', SHIELD: 'ShieldCube_', SPEED: 'FastForward_', FAST_SHOT: 'FastShoot_'}
FRAME_TIME = 0.05


class PowerUp(Node):
    def __init__(self, kind, scene):
        super().__init__(name=NAMES.get(kind, 'POWERUP'))
        self.kind = kind
        w, h = scene.size
        self.size = (w / 10.0, w / 10.0)
        self.position = (float(between(50, int(w) - 50)), h)
        self.z = 6
        attach(self, Body(Circle(self.size[0] / 2.0), category=CAT_POWERUP, contact=CAT_PLAYER, collision=CAT_POWERUP))
        target_x = between(int(w / 4), int(w / 2))
        self.run(A.sequence([A.move_to(float(target_x), -h, DRIFT), A.remove_from_parent()]))
        prefix = FRAMES.get(kind)
        if prefix:
            frames = ['%s%02d' % (prefix, i) for i in range(25)]
            self.texture = frames[0]
            self.run(A.repeat_forever(A.animate_with_textures(frames, FRAME_TIME)))
