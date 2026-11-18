"""SpaceShip, the class the original uses for the player and for enemies (see docs/NOTES.md)."""
import random

from ..data import SHIPS, TEXTURES
from ..engine import actions as A
from ..engine.nodes import Node
from ..engine.physics import Body, Circle, Polygon, attach

PLAYER_CODE = 98
CAT_PLAYER, CAT_ENEMY, CAT_PLAYER_SHOT, CAT_ENEMY_SHOT = 0x1, 0x2, 0x4, 0x8
CAT_OBSTACLE, CAT_POWERUP, CAT_LASER = 0x10, 0x20, 0x40
CAT_SWOOSH_RIGHT, CAT_SWOOSH_LEFT, CAT_WALL = 0x80, 0x100, 0x200

RATE_STATUS = 0.55
ALARM_INTERVAL = 4.0
ENEMY_SHOT_FLIGHT = 1.5
ENEMY_SHOT_1_CODES = {0, 21, 22, 41}
BURST_FRAME = 0.02


def player_hitbox(w):
    """The player's polygon from initPlayerInParentView:, in fractions of the ship node width w (71.11 at W = 320)."""
    a, b, c, d = w / 6, w / 2, w * 5 / 26, w / 26
    return Polygon([(-a, -b), (a, -b), (b, -c), (b, d), (a, b), (-a, b), (-b, d), (-b, -c)])


def enemy_hitbox(w, h):
    """setPhysicsBodySpecs: an octagon that sits slightly left of and below the sprite's centre, as in the original."""
    return Polygon([(-0.5 * w, -0.44667 * h), (-0.1 * w, -0.5 * h), (0.3 * w, -0.44667 * h), (0.3 * w, -0.1 * h),
                    (0.3 * w, 0.3 * h), (-0.1 * w, 0.3 * h), (-0.5 * w, 0.3 * h), (-0.5 * w, -0.1 * h)])


def fit_size(texture, box):
    """createEnemyWithLife:...: scale the texture so its larger side equals box, keeping the aspect ratio."""
    w, h = texture
    k = box / max(w, h)
    return w * k, h * k


def burst_and_remove(node, frames):
    """A hit shot stops, plays its burst animation (frames x 0.02 s) and is then removed. Its linked sound lives until then."""
    node.remove_all_actions()
    node.run(A.sequence([A.wait(frames * BURST_FRAME), A.remove_from_parent()]))


class Shot(Node):
    """Shoot: a bullet that remembers which ship fired it."""

    def __init__(self, ship, size):
        super().__init__(name='Shoot', size=size)
        self.ship = ship


class SpaceShip(Node):
    def __init__(self, code, life, shield, scene):
        super().__init__(name='SpaceShip')
        self.code = code
        self.life = self.max_life = life
        self.shield = self.max_shield = shield
        self.parent_width, self.parent_height = int(scene.size[0]), int(scene.size[1])
        self.game = scene               # spaceshipParentScene
        self.receive_damage = True
        self.reached_half_health = False
        self.sound_id = None            # Aureal key of the engine loop
        self.ship_size = (0.0, 0.0)     # spaceshipNode size, before the node's own scale
        self.shoot_damage = 1
        self.score = 0
        self.laser_active = False

    @property
    def services(self):
        return self.game.services

    @classmethod
    def player(cls, scene, global_state):
        """initPlayerInParentView: life and shield from upgrades, a W/4.5 square sprite, the octagon hitbox,
        node scale 1.5 and an idle bob of w/15 up and down, one second each way with ease in-out."""
        ship = cls(PLAYER_CODE, global_state.get_life(), global_state.get_shield(), scene)
        w = scene.size[0] / 4.5
        ship.ship_size = (w, w)
        ship.size = (w, w)
        attach(ship, Body(player_hitbox(w), category=CAT_PLAYER, contact=CAT_ENEMY_SHOT | CAT_OBSTACLE, collision=CAT_OBSTACLE))
        ship.scale = 1.5
        bob = w / 15
        ship.run(A.repeat_forever(A.sequence([A.move_by(0, bob, 1.0).with_timing(A.EASE_IN_EASE_OUT),
                                              A.move_by(0, -bob, 1.0).with_timing(A.EASE_IN_EASE_OUT)])))
        return ship

    @classmethod
    def enemy(cls, code, scene):
        """initEnemyOfType:inParentView: stats and sizing. Spawning, entrance and AI come with the enemy step."""
        stats = SHIPS[code]
        ship = cls(code, stats['life'], 0, scene)
        ship.shoot_damage = stats['damage']
        ship.score = stats['score']
        tex = TEXTURES.get('SpaceShips_%d' % code, (40.0, 40.0))
        ship.ship_size = fit_size(tex, scene.size[0] / 4.3)
        ship.size = ship.ship_size
        ship.scale = 0.8
        return ship

    def set_physics_body_specs(self):
        w, h = self.size
        attach(self, Body(enemy_hitbox(w, h), category=CAT_ENEMY, contact=0x15, collision=CAT_OBSTACLE))

    @property
    def is_player(self):
        return self.code == PLAYER_CODE

    # damage (inflictDamage:)

    def inflict_damage(self, damage):
        """Returns True if this hit destroyed the ship."""
        if not self.receive_damage:
            return False
        say = self.services.voice.speak
        s = self.services.strings
        if self.shield >= 1:
            self.shield -= 1
            if self.is_player:
                say(s.get('info_ShieldEnd') if self.shield == 0 else s.format('info_Shield', self.shield), RATE_STATUS)
            return False
        self.life -= damage
        if self.life < 1:
            self.destroy()
            return True
        if self.life <= self.max_life // 2 and not self.reached_half_health:
            # VoiceOver-only in the original, always on here (see DEVIATIONS). It says "Enemy" even for the player.
            say(s.get('feedback_HalfLife'), RATE_STATUS)
            self.reached_half_health = True
        if self.is_player:
            say(s.format('info_vida', self.life), RATE_STATUS)
            if self.life == 1:
                self.run(A.repeat_forever(A.sequence([A.play_sound(lambda: self.services.effects.play('alarm.caf')),
                                                      A.wait(ALARM_INTERVAL)])), key='alarme')
        return False

    def restore_life(self):
        if self.life < self.max_life:
            self.life += 1
            if self.is_player:
                self.services.voice.speak(self.services.strings.format('info_vida', self.life), RATE_STATUS)
            if self.life > 1:
                self.remove_action('alarme')

    def restore_shield(self):
        if self.shield < self.max_shield:
            self.shield += 1
            if self.is_player:
                self.services.voice.speak(self.services.strings.format('info_Shield', self.shield), RATE_STATUS)

    # destruction (destroyShip)

    def destroy(self):
        if 100 <= self.code < 106:
            self.game.destroy_enemy(self.code)
        self.remove_spaceship(autodestruction=False)
        aureal = self.services.aureal
        if self.sound_id is not None:
            aureal.stop(self.sound_id, 2)
        name, ext = random.choice((('explosion_1', 'caf'), ('Explosion_', 'mp3'), ('explosion', 'mp3')))
        self.play_unlinked(name, ext, self.position)
        attach(self, None)
        if self.is_player:
            self.game.can_shoot = False
            self.game.remove_action('BlockShoot')
        # The rest is the explosion animation; the node then leaves the scene.
        self.run(A.sequence([A.wait(1.0), A.remove_from_parent()]))

    def remove_spaceship(self, autodestruction):
        """removeSpaceshipOnAutodestruction: stops the alarm and all actions. With autodestruction it also leaves."""
        self.remove_action('alarme')
        self.remove_all_actions()
        if autodestruction:
            self.remove_from_parent()

    # sounds (executeSoundNamed..., executeWithoutLinkSoundNamed...)

    def _new_sound(self, name, ext):
        aureal = self.services.aureal
        key = aureal.next_key()
        aureal.add_sound(name, ext, key)
        aureal.sound_id += 1
        return key

    def play_linked(self, name, ext, node):
        aureal = self.services.aureal
        key = self._new_sound(name, ext)
        aureal.link(key, node)
        aureal.play_once(key, node.position)
        return key

    def play_unlinked(self, name, ext, position):
        key = self._new_sound(name, ext)
        self.services.aureal.play_once(key, position)
        return key

    def shot_sound(self, bullet):
        """soundTiroWithBullet:"""
        if self.code in (3, 5, 7, 8, 15, 23, 27, 30, 42, 100, 101, 102):
            return
        if self.is_player:
            self.services.effects.play('PlayerGun.caf')
        elif self.code in ENEMY_SHOT_1_CODES:
            self.play_linked('Enemy_Shot_1', 'caf', bullet)
        else:
            self.play_linked('Enemy_Shot_2', 'mp3', bullet)

    # enemy shooting (startShooting:, shoot:)

    def start_shooting(self, interval):
        self.run(A.repeat_forever(A.sequence([A.run_block(self.shoot_tick), A.wait(interval)])), key='ShootingAction')

    def shoot_tick(self):
        game = self.game
        if not game.is_active or self.life < 1:
            self.remove_spaceship(autodestruction=True)
        if game.game_paused:
            return
        if random.getrandbits(1):
            self.fire_bullet()

    def fire_bullet(self, flight=ENEMY_SHOT_FLIGHT):
        """The non-laser branch of shoot:. Lasers are added with the enemy step."""
        size = self.parent_width // 6
        bullet = Shot(self, (float(size), float(size)))
        attach(bullet, Body(Circle(5.0), category=CAT_ENEMY_SHOT, contact=CAT_PLAYER | CAT_PLAYER_SHOT, collision=CAT_ENEMY_SHOT))
        bullet.position = (self.position[0], self.position[1] - self.ship_size[1] * 0.5)
        bullet.z = self.z
        bullet.run(A.sequence([A.move_to_y(-20.0, flight), A.remove_from_parent()]))
        self.game.add_child(bullet)
        self.shot_sound(bullet)
        return bullet

    # visual-only in the original: sprite frame animations for banking and levelling out
    def move_left(self):
        pass

    def move_right(self):
        pass

    def stabilise_from_left(self):
        pass

    def stabilise_from_right(self):
        pass
