"""The life, shield and power-up bars (initializePLayerLifeBar and initializeEnemyLifeBar). Visual only.

The player's bars sit along the bottom of the screen at z 8, in this order: the backbar, the orange life fill
(214, 130, 31) under the lifeBar frame, the purple power-up fill under the powerUpBar frame, and the cyan
shield fill (15, 183, 225) under the shieldBar frame. Fills are anchored at their left end. Sizes and
positions are the original's at 320 by 568 points, scaled to the scene.

An enemy (not the allies and rocks) gets a red fill under the enemyLife frame, the ship's width wide and a
fifteenth of that tall, centred above it.

Whenever life or shield changes the fill resizes to value times (full width / maximum) over 0.3 seconds,
as inflictDamage, restoreLife and restoreShield did. Here the bars watch the ship each frame for that.
The power-up fill fills in 0.3 seconds and drains over 10 when a power-up starts.
"""
from ..engine import actions as A
from ..engine.nodes import Node

RESIZE = 0.3
LIFE_FILL = (214 / 255, 130 / 255, 31 / 255, 1.0)
SHIELD_FILL = (15 / 255, 183 / 255, 225 / 255, 1.0)
POWER_FILL = (0.5, 0.0, 0.5, 1.0)      # purpleColor
RED = (1.0, 0.0, 0.0, 1.0)
NO_BAR = {37, 38, 39, 46, 47, 48, 49, 50}


def _bar(name, size, position, texture=None, color=None, z=8.0):
    n = Node(name=name, size=size, position=position)
    n.anchor = (0.0, 0.5)
    n.texture, n.color, n.z = texture, color, z
    return n


class Gauge:
    """A fill that follows one value of a ship."""

    def __init__(self, node, full_width, read, maximum):
        self.node, self.full, self.read, self.maximum = node, full_width, read, maximum
        self.last = read()
        node.size = (self.width(self.last), node.size[1])

    def width(self, value):
        return self.full * value / self.maximum if self.maximum else 0.0

    def update(self):
        value = self.read()
        if value != self.last:
            self.last = value
            self.node.run(A.resize_to_width(self.width(value), RESIZE), key='resize')


class PlayerBars:
    def __init__(self, scene, ship):
        W, H = scene.size
        sx, sy = W / 320.0, H / 568.0
        self.ship = ship
        life_w, small_w, power_w = 307.2 * sx, 159.2 * sx, 144.727 * sx
        life_y, small_y = 7.57335 * sy, 21.0371 * sy
        nodes = [
            _bar('lifebarBG', (W, 37.8667 * sy), (0.0, 18.9333 * sy), texture='backbar'),
            _bar('lifebar', (life_w, 11.36 * sy), (8.0 * sx, life_y), color=LIFE_FILL),
            _bar('lifeBarTop', (life_w, 11.36 * sy), (8.0 * sx, life_y), texture='lifeBar'),
            _bar('PowerUpBar', (0.0, 9.46667 * sy), (172.8 * sx, small_y), color=POWER_FILL),
            _bar('powerUpBarTop', (power_w, 9.46667 * sy), (172.8 * sx, small_y), texture='powerUpBar'),
            _bar('shieldBar', (small_w, 9.46667 * sy), (6.4 * sx, small_y), color=SHIELD_FILL),
            _bar('shieldBarTop', (small_w, 9.46667 * sy), (6.4 * sx, small_y), texture='shieldBar'),
        ]
        for n in nodes:
            scene.add_child(n)
        self.nodes = nodes
        self.power = nodes[3]
        self.power_width = power_w
        self.gauges = [Gauge(nodes[1], life_w, lambda: ship.life, ship.max_life),
                       Gauge(nodes[5], small_w, lambda: ship.shield, ship.max_shield)]

    def update(self):
        for g in self.gauges:
            g.update()

    def power_up(self, duration):
        self.power.run(A.sequence([A.resize_to_width(self.power_width, RESIZE),
                                   A.resize_to_width(0.0, duration)]), key='resize')

    def remove(self):
        for n in self.nodes:
            n.remove_from_parent()


class EnemyBar:
    def __init__(self, ship):
        w = ship.ship_size[0]
        h = w / 15.0
        position = (-w / 2.0, w / 2.0 + 20.0)
        fill = _bar('lifebar', (w, h), position, color=RED, z=0.0)
        frame = _bar('lifebarBG', (w, h), position, texture='enemyLife', z=0.0)
        ship.add_child(fill)
        ship.add_child(frame)
        self.gauge = Gauge(fill, w, lambda: ship.life, ship.max_life)

    def update(self):
        self.gauge.update()
