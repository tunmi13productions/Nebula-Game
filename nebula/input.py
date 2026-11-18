"""Keyboard stand-in for the accelerometer (see docs/DEVIATIONS.md, arrow-key steering).

Holding right reads as a fixed positive acceleration.x and holding left as the same value negated. Neither
or both reads as level. The value is sampled every 0.2 seconds like the original accelerometer, so
everything downstream behaves as it did with tilt.
"""
DEFAULT_TILT = 0.3   # provisional, tuned by playtesting. Must stay above 0.05 so the movement state changes.


class KeyboardTilt:
    def __init__(self, tilt=DEFAULT_TILT):
        self.tilt = tilt
        self.left = False
        self.right = False

    def __call__(self):
        if self.left == self.right:
            return 0.0
        return self.tilt if self.right else -self.tilt
