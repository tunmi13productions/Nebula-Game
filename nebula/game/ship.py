"""SpaceShip, the class the original uses for the player and for enemies. This step covers the player body."""
from ..engine import actions as A
from ..engine.nodes import Node
from ..engine.physics import Body, Polygon, attach

PLAYER_CODE = 98
CAT_PLAYER, CAT_ENEMY, CAT_PLAYER_SHOT, CAT_ENEMY_SHOT = 0x1, 0x2, 0x4, 0x8
CAT_OBSTACLE, CAT_POWERUP, CAT_LASER = 0x10, 0x20, 0x40
CAT_SWOOSH_RIGHT, CAT_SWOOSH_LEFT, CAT_WALL = 0x80, 0x100, 0x200


def player_hitbox(w):
    """The player's polygon from initPlayerInParentView:, in fractions of the ship node width w (71.11 at W = 320)."""
    a, b, c, d = w / 6, w / 2, w * 5 / 26, w / 26
    return Polygon([(-a, -b), (a, -b), (b, -c), (b, d), (a, b), (-a, b), (-b, d), (-b, -c)])


class SpaceShip(Node):
    def __init__(self, code, life, shield, scene_width, scene_height):
        super().__init__(name='SpaceShip')
        self.code = code
        self.life = self.max_life = life
        self.shield = self.max_shield = shield
        self.parent_width, self.parent_height = int(scene_width), int(scene_height)
        self.receive_damage = True
        self.reached_half_health = False
        self.sound_id = None
        self.ship_size = (0.0, 0.0)   # spaceshipNode size, before the node's own scale

    @classmethod
    def player(cls, scene_width, scene_height, global_state):
        """initPlayerInParentView: life and shield from upgrades, a W/4.5 square sprite, the octagon hitbox,
        node scale 1.5 and an idle bob of w/15 up and down, one second each way with ease in-out."""
        ship = cls(PLAYER_CODE, global_state.get_life(), global_state.get_shield(), scene_width, scene_height)
        w = scene_width / 4.5
        ship.ship_size = (w, w)
        ship.size = (w, w)
        attach(ship, Body(player_hitbox(w), category=CAT_PLAYER, contact=CAT_ENEMY_SHOT | CAT_OBSTACLE, collision=CAT_OBSTACLE))
        ship.scale = 1.5
        bob = w / 15
        ship.run(A.repeat_forever(A.sequence([A.move_by(0, bob, 1.0).with_timing(A.EASE_IN_EASE_OUT),
                                              A.move_by(0, -bob, 1.0).with_timing(A.EASE_IN_EASE_OUT)])))
        return ship

    # visual-only in the original: sprite frame animations for banking and levelling out
    def move_left(self):
        pass

    def move_right(self):
        pass

    def stabilise_from_left(self):
        pass

    def stabilise_from_right(self):
        pass
