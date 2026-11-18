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

    @classmethod
    def load(cls, save):
        """Global init: the upgrade points and progress from the save. A save with no chapter yet starts at
        chapter 1, level 1, and saves that."""
        g = cls()
        g.shot_points = save.integer('Shoot_Points')
        g.time_shot_points = save.integer('TimeShoot_Points')
        g.life_points = save.integer('Life_Points')
        g.shield_points = save.integer('Shild_Points')
        g.speed_points = save.integer('Speed_Points')
        g.win_points = save.integer('Win_Points')
        g.last_chapter = save.integer('last_Chapter')
        g.last_level = save.integer('last_Level')
        if g.last_chapter < 1:
            g.last_chapter = g.last_level = 1
            g.save_progress(save)
        return g

    def save_points(self, save):
        """savePoints: the upgrade points and the unspent points."""
        save.set_integer('TimeShoot_Points', self.time_shot_points)
        save.set_integer('Shoot_Points', self.shot_points)
        save.set_integer('Life_Points', self.life_points)
        save.set_integer('Speed_Points', self.speed_points)
        save.set_integer('Shild_Points', self.shield_points)
        save.set_integer('Win_Points', self.win_points)
        save.synchronize()

    def save_progress(self, save):
        """saveProgress: the furthest chapter and level reached."""
        save.set_integer('last_Chapter', self.last_chapter)
        save.set_integer('last_Level', self.last_level)
        save.synchronize()

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
