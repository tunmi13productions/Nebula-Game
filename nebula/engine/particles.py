"""SKEmitterNode: a particle emitter loaded from the original .sks files (data/emitters.json).

Visual only. It uses its own random generator, so it never touches the game's arc4random sequence.

Each particle is born at the emitter (plus a random offset within position_range), moves at its speed along
its emission angle, is pushed by the acceleration, and changes scale, alpha, rotation and colour at their
per-second speeds until its lifetime ends. A colour sequence, when there is one, sets the colour over the
particle's life instead. "range" values spread a start value evenly around it, as SpriteKit's variances do.
With a target node (normally the scene), particles stay where they were born when the emitter moves;
without one they move with the emitter.
"""
import json
import math
import os
import random

from .nodes import Node

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data',
                     'emitters.json')
_EMITTERS = None
_random = random.Random(1)


def emitter_data(name):
    global _EMITTERS
    if _EMITTERS is None:
        with open(_DATA, encoding='utf-8') as f:
            _EMITTERS = json.load(f)
    return dict(_EMITTERS[name])


def _spread(value, rng):
    return value + (_random.random() - 0.5) * rng if rng else value


class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'age', 'life', 'scale', 'alpha', 'rotation', 'color', 'blend')


class Emitter(Node):
    simulate = True     # visual only; headless test runs turn it off to save time (tests/conftest.py)

    def __init__(self, name, **overrides):
        super().__init__(name=name)
        self.params = emitter_data(name)
        self.params.update(overrides)
        self.particles = []
        self.target = None        # targetNode: None (particles move with the emitter) or the scene
        self.xscale = self.yscale = 1.0   # the emitter node's xScale and yScale, which stretch its particles
        self._owed = 0.0
        self.emitted = 0

    def set(self, **overrides):
        """setParticleBirthRate: and the like, after loading."""
        self.params.update(overrides)

    def reset(self):
        self.particles = []
        self.emitted = 0
        self._owed = 0.0

    def update_actions(self, dt):
        super().update_actions(dt)
        if self.paused or not Emitter.simulate:
            return
        self._simulate(dt)

    # simulation

    def _origin(self):
        """Where new particles start, in the target's space."""
        if self.target is None:
            return 0.0, 0.0
        x, y, n = 0.0, 0.0, self
        while n is not None and n is not self.target:
            px, py = n.position
            x, y = px + x * n.scale, py + y * n.scale
            n = n.parent
        return x, y

    def _simulate(self, dt):
        p = self.params
        alive = []
        for q in self.particles:
            q.age += dt
            if q.age >= q.life:
                continue
            q.vx += p['acceleration'][0] * dt
            q.vy += p['acceleration'][1] * dt
            q.x += q.vx * dt
            q.y += q.vy * dt
            q.scale = max(0.0, q.scale + p['scale_speed'] * dt)
            q.alpha = min(1.0, max(0.0, q.alpha + p['alpha_speed'] * dt))
            q.rotation += p['rotation_speed'] * dt
            q.blend = min(1.0, max(0.0, q.blend + p['color_blend_speed'] * dt))
            if not p.get('color_sequence'):
                q.color = [min(1.0, max(0.0, c + s * dt)) for c, s in zip(q.color, p['color_speed'])]
            alive.append(q)
        self.particles = alive
        rate = p['birth_rate']
        limit = p['to_emit']
        if rate <= 0:
            return
        self._owed += rate * dt
        ox, oy = self._origin()
        while self._owed >= 1.0:
            self._owed -= 1.0
            if limit and self.emitted >= limit:
                self._owed = 0.0
                break
            self.emitted += 1
            self.particles.append(self._spawn(ox, oy))

    def _spawn(self, ox, oy):
        p = self.params
        q = Particle()
        rx, ry = p['position_range']
        q.x = ox + (_random.random() - 0.5) * rx
        q.y = oy + (_random.random() - 0.5) * ry
        angle = _spread(p['emission_angle'], p['emission_angle_range'])
        speed = _spread(p['speed'], p['speed_range'])
        q.vx, q.vy = speed * math.cos(angle), speed * math.sin(angle)
        q.age = 0.0
        q.life = max(0.001, _spread(p['lifetime'], p['lifetime_range']))
        q.scale = max(0.0, _spread(p['scale'], p['scale_range']))
        q.alpha = min(1.0, max(0.0, _spread(p['alpha'], p['alpha_range'])))
        q.rotation = _spread(p['rotation'], p['rotation_range'])
        q.color = [min(1.0, max(0.0, _spread(c, r))) for c, r in zip(p['color'], p['color_range'])]
        q.blend = min(1.0, max(0.0, _spread(p['color_blend'], p['color_blend_range'])))
        return q

    def color_of(self, q):
        seq = self.params.get('color_sequence')
        if not seq:
            return q.color
        return keyframe(seq, q.age / q.life)


def keyframe(seq, t):
    """SKKeyframeSequence sampleAtTime: with linear interpolation, clamped at the ends."""
    times, values = seq['times'], seq['values']
    if t <= times[0] or len(times) == 1:
        return values[0]
    for i in range(1, len(times)):
        if t <= times[i]:
            a, b = times[i - 1], times[i]
            k = (t - a) / (b - a) if b > a else 1.0
            return [x + (y - x) * k for x, y in zip(values[i - 1], values[i])]
    return values[-1]
