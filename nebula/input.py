"""Keyboard stand-in for the accelerometer (see docs/DEVIATIONS.md, arrow-key steering).

Holding right reads as a fixed positive acceleration.x and holding left as the same value negated. Neither
or both reads as level. Holding Shift as well reads as a steeper tilt. The value is sampled every 0.2
seconds like the original accelerometer, so everything downstream behaves as it did with tilt.
"""
DEFAULT_TILT = 0.3        # chosen by playtesting. Must stay above 0.05 so the movement state changes.
DEFAULT_FAST_TILT = 0.6   # with Shift held: twice as steep, so twice as fast


class KeyboardTilt:
    def __init__(self, tilt=DEFAULT_TILT, fast_tilt=DEFAULT_FAST_TILT):
        self.tilt = tilt
        self.fast_tilt = fast_tilt
        self.left = False
        self.right = False
        self.fast = False

    def __call__(self):
        if self.left == self.right:
            return 0.0
        value = self.fast_tilt if self.fast else self.tilt
        return value if self.right else -value
