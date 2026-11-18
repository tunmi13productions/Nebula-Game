"""SpaceShip, the class the original uses for the player and for enemies (see docs/NOTES.md)."""
from ..data import SHIPS, TEXTURES
from ..engine import actions as A
from ..engine.nodes import Node
from ..engine.particles import Emitter
from ..engine.physics import Body, Circle, Polygon, attach, rectangle
from . import hud, looks
from .rand import arc4random, between

PLAYER_CODE = 98
CAT_PLAYER, CAT_ENEMY, CAT_PLAYER_SHOT, CAT_ENEMY_SHOT = 0x1, 0x2, 0x4, 0x8
CAT_OBSTACLE, CAT_POWERUP, CAT_LASER = 0x10, 0x20, 0x40
CAT_SWOOSH_RIGHT, CAT_SWOOSH_LEFT, CAT_WALL = 0x80, 0x100, 0x200

RATE_STATUS = 0.55
ALARM_INTERVAL = 4.0
ENEMY_SHOT_FLIGHT = 1.5
ENEMY_SHOT_1_CODES = {0, 21, 22, 41}
BURST_FRAME = 0.02
BANK_FRAME = 0.03                                   # the banking animations, per frame
LASER_CODES = {3, 5, 7, 8, 15, 23, 27, 30, 42, 100, 101, 102}
ALLY_CODES = {37, 38, 39}
DRIFTER_CODES = {37, 38, 39, 46, 47, 48, 49, 50}     # allies, the fuel tank and rocks: they fall instead of fighting
ROCK_CODES = {47, 48, 49, 50}
DRIFTER_OFFSCREEN = 90                              # destroyEnemy: code for a drifter that left the screen
LASER_CHARGE, LASER_WARM = 1.0, 1.5                 # charge sound, then firing sound, then the beam
LASER_RETREAT = 3.0
SPIN = 3.14159274                                   # rotateByAngle: M_PI as a float, every 3 seconds


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


def burst_and_remove(node, frames, textures=None):
    """A hit shot stops, plays its burst animation (frames x 0.02 s) and is then removed. Its linked sound lives
    until then. textures are the burst's pictures (visual only)."""
    node.remove_all_actions()
    node.run(A.sequence([A.wait(frames * BURST_FRAME), A.remove_from_parent()]))
    if textures:
        node.run(A.animate_with_textures(textures, BURST_FRAME))


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
        ship.add_sprite('Player_10')
        attach(ship, Body(player_hitbox(w), category=CAT_PLAYER, contact=CAT_ENEMY_SHOT | CAT_OBSTACLE, collision=CAT_OBSTACLE))
        ship.scale = 1.5
        bob = w / 15
        ship.run(A.repeat_forever(A.sequence([A.move_by(0, bob, 1.0).with_timing(A.EASE_IN_EASE_OUT),
                                              A.move_by(0, -bob, 1.0).with_timing(A.EASE_IN_EASE_OUT)])))
        return ship

    @classmethod
    def enemy(cls, code, scene, entrance=True):
        """initEnemyOfType:inParentView: and createEnemyWithLife:...: stats, sizing, start position and entrance."""
        stats = SHIPS[code]
        ship = cls(code, stats['life'], 0, scene)
        ship.shoot_damage = stats['damage']
        ship.score = stats['score']
        ship.fire_interval = stats['fire_interval']
        ship.move_interval = stats['move_interval']
        tex = TEXTURES.get('SpaceShips_%d' % code, (40.0, 40.0))
        ship.ship_size = fit_size(tex, scene.size[0] / 4.3)
        ship.size = ship.ship_size
        ship.add_sprite('SpaceShips_%d' % code)
        if code not in hud.NO_BAR:
            ship.life_bar = hud.EnemyBar(ship)
        ship.scale = 0.8
        ship.position = (float(ship.parent_width // 2), ship.parent_height + ship.ship_size[1])
        if entrance:
            ship.run_entrance()
        return ship

    def add_sprite(self, texture):
        """spaceshipNode: the ship's picture, a child sprite of ship_size (visual only)."""
        self.sprite = Node(name='spaceshipNode', size=self.ship_size)
        self.sprite.texture = texture
        self.add_child(self.sprite)

    def run_entrance(self):
        W, H = self.parent_width, self.parent_height
        sw = self.ship_size[0]
        if self.code in DRIFTER_CODES:
            x = between(int(sw), int(W - sw))
            self.run(A.move_to(float(x), float(H + H // 2), 1.5),
                     completion=lambda: (self.set_physics_body_specs(), self.push_spaceship()))
        elif self.code in LASER_CODES:
            x = sw * 1.8 if arc4random() & 1 == 0 else W - sw * 1.8
            y = between(int(H * 0.8), int(H * 0.85))
            self.run(A.move_to(float(int(x)), float(y), 1.0),
                     completion=lambda: (self.start_shooting(self.fire_interval), self.set_physics_body_specs()))
        else:
            x = between(int(sw), int(W - sw))
            y = between(int(H * 0.75), int(H * 0.9))
            self.run(A.move_to(float(x), float(y), 1.5).with_timing(A.EASE_IN_EASE_OUT),
                     completion=lambda: (self.start_shooting(self.fire_interval),
                                         self.start_moving(self.move_interval), self.set_physics_body_specs()))

    # movement (startMovingWithInterval:, move:, pushSpaceShip)

    def start_moving(self, interval):
        self.move_interval = interval
        self.run(A.repeat_forever(A.sequence([A.run_block(self.move_tick), A.wait(interval)])), key='MovingAction')

    def move_tick(self):
        game = self.game
        if not game.is_active or self.life < 1:
            self.remove_spaceship(autodestruction=True)
            return
        if game.game_paused or arc4random() & 1 == 0:
            return
        sw = self.ship_size[0]
        x = between(int(sw * 0.5), int(self.parent_width - sw * 0.5))
        y = between(int(self.parent_height * 0.7), int(self.parent_height * 0.85))
        t = self.move_interval
        duration = t if t <= 1.0 else (1.5 if t <= 3.0 else 2.0)
        self.run(A.move_to(float(x), float(y), duration).with_timing(A.EASE_IN_EASE_OUT))

    def push_spaceship(self):
        """Drifters fall 2H over 5 to 8 seconds (allies 2 to 5, rocks 3 to 6) with a random sideways drift.
        Rocks and the fuel tank spin. At the bottom, allies and rocks leave and report code 90, while the
        fuel tank explodes and reports itself."""
        quarter = self.parent_width // 4
        dx = between(-quarter, quarter)
        lo, hi = (2, 5) if self.code in ALLY_CODES else ((3, 6) if self.code in ROCK_CODES else (5, 8))
        fall = A.move_by(float(dx), float(-2 * self.parent_height), float(between(lo, hi)))
        if self.code not in ALLY_CODES:
            self.run(A.repeat_forever(A.rotate_by(SPIN, 3.0)))

        def landed():
            if self.code == 46:
                self.destroy()
                self.game.destroy_enemy(self.code)
            else:
                self.remove_spaceship(autodestruction=True)
                self.game.destroy_enemy(DRIFTER_OFFSCREEN)
        self.run(fall, completion=landed)

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

    def starting_power_up(self, kind):
        """startingPowerUpOfTipe: the power bar fills in 0.3 s and drains over 10 s, then the effect ends."""
        bars = getattr(self.game, 'player_bars', None)
        if self.is_player and bars is not None:
            bars.power_up(10.0)
        self.run(A.sequence([A.wait(0.3), A.wait(10.0), A.run_block(lambda: self.game.end_power_up(kind))]))

    # destruction (destroyShip)

    def destroy(self):
        if 100 <= self.code < 106:
            self.game.destroy_enemy(self.code)
        self.remove_spaceship(autodestruction=False)
        aureal = self.services.aureal
        if self.sound_id is not None:
            aureal.stop(self.sound_id, 2)
        name, ext = (('explosion_1', 'caf'), ('Explosion_', 'mp3'), ('explosion', 'mp3'))[arc4random() % 3]
        self.play_unlinked(name, ext, self.position)
        attach(self, None)
        # which explosion to show: arc4random() & 1, a draw in the original's random sequence
        frames = looks.EXPLOSION_1 if arc4random() & 1 == 0 else looks.EXPLOSION_2
        if self.is_player:
            self.game.can_shoot = False
            self.game.remove_action('BlockShoot')
        self.show_explosion(frames)
        if not self.is_player:
            self.score_sparkle()
        self.run(A.sequence([A.wait(1.0), A.remove_from_parent()]))

    def show_explosion(self, frames=looks.EXPLOSION_1):
        """destroyShip's picture: the ship's children go, and the ship, three times its size, plays the
        Explosion02 or Explosion03 frames (Global Explosion_1 or _2) at 0.032 seconds each. Visual only; the
        ship's size for the game is untouched, so the explosion is a child of that size."""
        for child in list(self.children):
            child.remove_from_parent()
        w, h = self.ship_size
        boom = Node(name='explosion', size=(w * 3, h * 3))
        boom.texture = frames[0]
        boom.run(A.animate_with_textures(frames, looks.EXPLOSION_FRAME))
        self.add_child(boom)

    def score_sparkle(self):
        """An enemy's score.sks burst: 30 additive sparks that double in size over 0.45 seconds, fly to the
        top centre (W/2, 0.95 H) after 0.3 seconds, shrink away over 0.3 and go (visual only)."""
        em = Emitter('score')
        em.set(to_emit=30, birth_rate=450.0, lifetime=2.0, speed=100.0, speed_range=60.0, alpha=0.8,
               alpha_range=0.2, alpha_speed=-0.5, scale=0.75, scale_range=0.2, scale_speed=-0.5, rotation=0.0,
               rotation_range=0.0, rotation_speed=0.0, color_blend=1.0, color_blend_range=0.0,
               color_blend_speed=0.0, blend_mode=1)
        em.position, em.z = self.position, 100
        self.game.add_child(em)
        em.run(A.scale_to(2.0, 0.45))
        em.run(A.sequence([A.wait(0.3), A.move_to(self.parent_width / 2, self.parent_height * 0.95, 0.3),
                           A.scale_to(0.0, 0.3), A.remove_from_parent()]))

    def remove_spaceship(self, autodestruction):
        """removeSpaceshipOnAutodestruction: stops the alarm and all actions and removes a laser beam.
        With autodestruction the ship also leaves the scene."""
        self.remove_action('alarme')
        if getattr(self, 'laser_body', None) is not None:
            self.laser_body.remove_from_parent()
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
        if arc4random() & 1:
            if self.code in LASER_CODES:
                if not self.laser_active:
                    self.laser_shoot()
            else:
                self.fire_bullet()

    # scripted control, used by the tutorial

    def invalidate_movement_and_shoot(self):
        """Stops every action (entrance, movement, shooting) and switches the physics body on."""
        self.remove_all_actions()
        self.set_physics_body_specs()

    def initialize_movement(self):
        self.start_moving(1.0)

    def initialize_shoot_with_time(self, interval):
        self.start_shooting(interval)

    def manual_shot(self):
        """manualShot: a laser for laser ships (if none is active), otherwise a Fireball bullet of size W/12."""
        if self.code in LASER_CODES:
            if not self.laser_active:
                self.laser_shoot()
            return None
        return self.fire_bullet(size=self.parent_width // 12)

    def fire_bullet(self, flight=ENEMY_SHOT_FLIGHT, size=None):
        """The non-laser branch of shoot: (size W/6), also used by manualShot (size W/12)."""
        size = self.parent_width // 6 if size is None else size
        bullet = Shot(self, (float(size), float(size)))
        bullet.texture = looks.FIREBALL[2]
        bullet.tint, bullet.color_blend = looks.ship_color(self.code), 1.0
        bullet.run(A.repeat_forever(A.animate_with_textures(looks.FIREBALL, looks.BULLET_FRAME)))
        attach(bullet, Body(Circle(5.0), category=CAT_ENEMY_SHOT, contact=CAT_PLAYER | CAT_PLAYER_SHOT, collision=CAT_ENEMY_SHOT))
        bullet.position = (self.position[0], self.position[1] - self.ship_size[1] * 0.5)
        bullet.z = self.z
        bullet.run(A.sequence([A.move_to_y(-20.0, flight), A.remove_from_parent()]))
        self.game.add_child(bullet)
        self.shot_sound(bullet)
        return bullet

    # lasers (laserShoot)

    def laser_shoot(self):
        """Charge sound, wait 1 s, firing sound, wait 1.5 s, then a beam W/50 wide and H tall centred on the
        ship's column holds for 3 to 7 whole seconds. The firing sound then fades while the beam slides up
        over 3 s, still harmful, and is removed."""
        if self.game.game_paused:
            return
        hold = float(arc4random() % 5 + 3)
        self.laser_active = True
        beam = self.laser_body = Shot(self, (0.0, 0.0))
        beam.anchor = (0.5, 1.0)
        self.game.add_child(beam)
        keys = {}

        def charge():
            keys['sound'] = self.play_linked('Laser_Charge', 'caf', self)

        def glow():
            """The charging glow: one of the four MyParticle emitters, picked with arc4random() % 4 (this
            draw is part of the original's random sequence), at the ship's nose, slow and red."""
            variant = ('MyParticle', 'MyParticle1', 'MyParticle2', 'MyParticle3')[arc4random() & 3]
            em = keys['emitter'] = Emitter(variant)
            em.set(birth_rate=10.0, lifetime=1.0, position_range=[0.0, 0.0], speed=0.0, speed_range=0.0,
                   rotation=0.0, alpha=1.0, alpha_range=1.0, alpha_speed=1.0, scale=0.2, scale_range=0.0,
                   scale_speed=0.0, acceleration=[0.0, 0.0], blend_mode=1, color=[1.0, 0.0, 0.0, 1.0])
            em.position = (self.position[0], self.position[1] - self.ship_size[1] * 0.45)
            em.z = 5
            self.game.add_child(em)

        def fire():
            keys['sound'] = self.play_linked('Laser_Firing', 'mp3', self)

        def stream():
            """The beam's look: the particles pour down."""
            keys['emitter'].set(acceleration=[0.0, -500.0], birth_rate=150.0, lifetime=2.0)

        def stop_stream():
            em = keys['emitter']
            em.set(acceleration=[0.0, 0.0], birth_rate=0.0)
            em.run(A.sequence([A.wait(2.0), A.remove_from_parent()]))

        def beam_on():
            beam.position = (self.position[0], float(self.parent_height // 2))
            beam.size = (float(self.parent_width // 50), float(self.parent_height))
            attach(beam, Body(rectangle(*beam.size), category=CAT_LASER, contact=CAT_PLAYER, collision=CAT_LASER))

        def retreat():
            self.services.aureal.stop(keys.get('sound'), 1)

            def done():
                beam.remove_from_parent()
                self.laser_active = False
            beam.run(A.move_to_y(float(self.parent_height), LASER_RETREAT), completion=done)
        beam.run(A.sequence([A.run_block(charge), A.run_block(glow), A.wait(LASER_CHARGE), A.run_block(fire),
                             A.run_block(stream), A.wait(LASER_WARM), A.run_block(beam_on), A.wait(hold),
                             A.run_block(stop_stream), A.run_block(retreat)]))

    # visual-only in the original: sprite frame animations for banking and levelling out
    # banking: the player's 21 Player_ frames, 10 being level, at 0.03 seconds a frame (visual only)

    def _bank(self, frames):
        sprite = getattr(self, 'sprite', None)
        if sprite is not None:
            sprite.remove_all_actions()
            sprite.run(A.animate_with_textures(['Player_%02d' % i for i in frames], BANK_FRAME))

    def move_left(self):
        """moveSpaceshipToLeft: frames 11 to 20."""
        self._bank(range(11, 21))

    def move_right(self):
        """moveSpaceshipToRight: frames 9 down to 0."""
        self._bank(range(9, -1, -1))

    def stabilise_from_left(self):
        """estabilizaSpaceshipToLeft: frames 20 back to 10."""
        self._bank(range(20, 9, -1))

    def stabilise_from_right(self):
        """estabilizaSpaceshipToRight: frames 0 up to 10."""
        self._bank(range(0, 11))
