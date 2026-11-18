"""The original Global singleton's upgrade stats and formulas (see docs/NOTES.md, upgrades)."""


class GlobalState:
    def __init__(self):
        self.time_shot_points = 0
        self.shot_points = 0
        self.life_points = 0
        self.shield_points = 0
        self.speed_points = 0
        self.win_points = 0
        self.last_chapter = 1
        self.last_level = 1
        self.free_mode = False

    def get_time_shot(self):
        """Seconds between auto shots."""
        p = self.time_shot_points
        return 1.0 + p * -0.1 if p <= 4 else 0.5

    def get_shot(self):
        p = self.shot_points
        return p + 1 if p < 5 else 6

    def get_life(self):
        p = self.life_points
        return 5 * p + 5 if p < 5 else 30

    def get_shield(self):
        return min(self.shield_points, 5)

    def get_speed(self):
        """The divisor of screen width for movement speed: lower is faster."""
        p = self.speed_points
        return 50 - 5 * p if p < 5 else 25
