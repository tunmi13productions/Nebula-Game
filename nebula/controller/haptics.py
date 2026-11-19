"""Controller vibration (a port addition, DEVIATIONS.md, "Game controllers"). The original never vibrated.

The game tells Haptics what happened; Haptics buzzes the pad through `rumble(low, high, ms)` (Pads.rumble),
or does nothing when there is no pad or vibration is off. A pad's low-frequency motor is in its left grip
and its high-frequency motor in its right grip, so they stand for the left and right edges.

    hit (shield or life lost)   a short buzz on both motors
    the player explodes         a long, strong buzz on both motors
    power-up collected          a small pulse on the light motor
    reaching the left edge      the left (low) motor
    reaching the right edge     the right (high) motor
"""

PATTERNS = {
    'hit': (0.6, 0.6, 150),
    'explode': (1.0, 1.0, 900),
    'power_up': (0.0, 0.45, 70),
    'edge_left': (0.55, 0.0, 120),
    'edge_right': (0.0, 0.75, 120),
}


class Haptics:
    def __init__(self, rumble=None):
        self.rumble = rumble
        self.enabled = True
        self.played = []          # what was asked for, for the tests

    def _buzz(self, name):
        self.played.append(name)
        if self.enabled and self.rumble is not None:
            self.rumble(*PATTERNS[name])

    def hit(self):
        self._buzz('hit')

    def explode(self):
        self._buzz('explode')

    def power_up(self):
        self._buzz('power_up')

    def edge(self, side):
        self._buzz('edge_left' if side < 0 else 'edge_right')
