"""BaseScene, the shared gameplay scene. See docs/NOTES.md (input and movement, physics categories and
collisions, swoosh fields and side walls, shots, damage model).
"""
from ..engine import actions as A
from ..engine.nodes import Node, Scene
from ..engine.physics import Body, Circle, PhysicsWorld, attach, rectangle
from ..data import engine_sound
from .powerups import FAST_SHOT, LIFE, SHIELD, SPEED, PowerUp
from .rand import between
from .ship import (CAT_ENEMY, CAT_ENEMY_SHOT, CAT_LASER, CAT_OBSTACLE, CAT_PLAYER, CAT_PLAYER_SHOT, CAT_POWERUP,
                   CAT_SWOOSH_LEFT, CAT_SWOOSH_RIGHT, CAT_WALL, Shot, SpaceShip, burst_and_remove)

W, H = 320.0, 568.0
ACCEL_INTERVAL = 0.2      # CMMotionManager accelerometerUpdateInterval
DEAD_ZONE = 0.04          # outputAccelerationData: smaller readings count as zero
STATE_THRESHOLD = 0.05    # update: beyond this the ship is moving left or right
BASE_LOOP = 1.0           # "BaseActions"
TALK_INTERVAL = 0.3       # "TalkingMovement"
POSITION_FACTOR_IPHONE = 0.17
RATE_STATUS, RATE_MOVE = 0.55, 0.6
PLAYER_SHOT_FLIGHT = 1.0
SCORE_DELAY = 0.9
END_GAME_DELAY = 1.5
SHOT_BURST_FRAMES = 15    # arrayPower_2, the Fireball frames
ENEMY_BURST_FRAMES = 9    # arrayPower_3

STOPPED, RIGHT, LEFT = 0, 1, 2


def _pair(a, b, cat_a, cat_b):
    """Returns (body with cat_a, body with cat_b) if the contact is between those two categories, else None."""
    if a.category == cat_a and b.category == cat_b:
        return a, b
    if b.category == cat_a and a.category == cat_b:
        return b, a
    return None


class BaseScene(Scene):
    def __init__(self, services, tilt_source=None):
        super().__init__(W, H)
        self.services = services
        self.tilt_source = tilt_source or (lambda: 0.0)   # returns acceleration.x; the keyboard stands in for tilt
        self.physics_world = PhysicsWorld()
        self.is_active = True
        self.allow_move = True
        self.allow_shoot = True
        self.can_shoot = False
        self.power_up_shot = False
        self.game_paused = False
        self.talking_move = False
        self._talking_running = False
        self.current_max_accel_x = 0.0
        self.movement_state = STOPPED
        self._last_spoken_state = STOPPED
        self.should_lateral_play_hit_sound = True
        self.last_shot_hit = None          # lastShoot
        self.toaster = None                # the laser beam the player is touching
        self.time_between_power_ups = 0    # timed drops are off unless a mode turns them on
        self.time_to_next_power_up = 0
        self.power_up_type1 = 0
        self.power_up_type2 = 0
        self.stage_number = 0              # 0 is free mode; campaign stages are 1 to 4
        self.score_counter = 0
        self.death_counter = 0
        self.velocidade = W / services.globals.get_speed()

        self.player = SpaceShip.player(self, services.globals)
        w, h = self.player.ship_size
        self.player.position = (W * 0.5, h + (H / 3) * POSITION_FACTOR_IPHONE)
        self.player.z = 5
        self.add_child(self.player)
        services.aureal.configure(H * 1.25, self.player.position, self, max_x=W)
        self._create_swoosh_fields()
        self._create_side_walls()

        self._accel_timer = services.scheduler.every(ACCEL_INTERVAL, lambda t: self._sample_accelerometer())
        self.run(A.repeat_forever(A.sequence([A.run_block(self.base_actions), A.wait(BASE_LOOP)])), key='BaseActions')

    def did_move_to_view(self):
        """BaseScene didMoveToView: starts the auto-fire loop that re-enables shooting."""
        self.starting_shoot_loop()

    # input

    def _sample_accelerometer(self):
        if self.game_paused:
            return
        x = self.tilt_source()
        self.current_max_accel_x = x if (x > DEAD_ZONE or x < -DEAD_ZONE) else 0.0

    def speak_life(self):
        """Swipe down in the original: 'Your life is N'."""
        if not self.game_paused:
            self.services.voice.speak(self.services.strings.format('info_vida', self.player.life), RATE_STATUS)

    # shooting

    def starting_shoot_loop(self):
        interval = self.services.globals.get_time_shot()
        self.run(A.repeat_forever(A.sequence([A.run_block(lambda: setattr(self, 'can_shoot', True)), A.wait(interval)])),
                 key='BlockShoot')

    def player_shoot(self):
        """playerShoot, on tap: at most one shot per auto-fire interval unless fast shot is active."""
        if self.in_menu or not (self.can_shoot or self.power_up_shot) or self.game_paused or not self.allow_shoot:
            return None
        p = self.player
        w, h = p.ship_size
        shot = Shot(p, (w * 0.5, h * 0.2))
        shot.position = (p.position[0], p.position[1] * 1.2)
        attach(shot, Body(Circle(W / 30.0), category=CAT_PLAYER_SHOT, contact=CAT_ENEMY | CAT_OBSTACLE,
                          collision=CAT_PLAYER_SHOT | CAT_ENEMY_SHOT))
        shot.z = 5
        self.add_child(shot)
        shot.run(A.sequence([A.move_to_y(H + 20.0, PLAYER_SHOT_FLIGHT), A.remove_from_parent()]))
        self.can_shoot = False
        p.shot_sound(None)
        return shot

    # per frame (update:)

    def on_update(self, dt):
        if self.game_paused or not self.allow_move:
            return
        accel = self.current_max_accel_x
        p = self.player
        if accel > STATE_THRESHOLD:
            if self.movement_state != RIGHT:
                p.move_left()     # the original's names are swapped: this is the right-bank animation
                self.movement_state = RIGHT
        elif accel < -STATE_THRESHOLD:
            if self.movement_state != LEFT:
                p.move_right()
                self.movement_state = LEFT
        else:
            if self.movement_state == RIGHT:
                p.stabilise_from_left()
            elif self.movement_state == LEFT:
                p.stabilise_from_right()
            self.movement_state = STOPPED
        half = p.ship_size[0] * 0.5
        x = min(max(p.position[0] + accel * self.velocidade, half), W - half)
        p.position = (x, p.position[1])
        self.services.aureal.listener = p.position

    def did_evaluate_actions(self):
        # The swoosh fields are held to the ship by fixed physics joints in the original.
        px, py = self.player.position
        for field, (ox, oy) in self._swoosh_offsets:
            field.position = (px + ox, py + oy)

    # BaseActions, every second

    def base_actions(self):
        if self.game_paused:
            return
        beam = self.toaster
        if beam is not None:
            if beam.ship.parent is not None and self.player.parent is not None and self.player.life > 0:
                # Standing in a laser hurts again every second.
                if self.player.inflict_damage(beam.ship.shoot_damage):
                    self._schedule_end_game()
            elif beam.ship.parent is None:
                self.toaster = None
        if self.time_between_power_ups > 0:
            self.time_to_next_power_up -= 1
            if self.time_to_next_power_up < 0:
                self.release_power_up(between(self.power_up_type1, self.power_up_type2))
                tb = self.time_between_power_ups
                self.time_to_next_power_up = between(tb, tb * 2)
        if self.talking_move and self.allow_move:
            if not self._talking_running:
                self._talking_running = True
                self.run(A.repeat_forever(A.sequence([A.run_block(self.talking_move_action), A.wait(TALK_INTERVAL)])),
                         key='TalkingMovement')
        else:
            self.remove_action('TalkingMovement')
            self._talking_running = False

    def talking_move_action(self):
        if self.game_paused:
            return
        if not (self.talking_move and self.allow_move):
            self.remove_action('TalkingMovement')
            self._talking_running = False
            return
        if self._last_spoken_state == self.movement_state:
            return
        key = {RIGHT: 'talkingMove_D', LEFT: 'talkingMove_E'}.get(self.movement_state, 'talkingMove_P')
        self.services.voice.speak(self.services.strings.get(key), RATE_MOVE)
        self._last_spoken_state = self.movement_state

    # fields and walls

    def _create_swoosh_fields(self):
        w, h = self.player.ship_size
        fw = w * 0.7
        self._swoosh_offsets = []
        for cat, sign in ((CAT_SWOOSH_LEFT, -1), (CAT_SWOOSH_RIGHT, 1)):
            field = Node(name='swoosh', size=(fw, 10.0))
            attach(field, Body(rectangle(fw, 10.0), category=cat, contact=CAT_ENEMY_SHOT, collision=cat))
            self.add_child(field)
            self._swoosh_offsets.append((field, (sign * (w * 0.5 + fw * 0.5), h * 0.5)))
        self.did_evaluate_actions()

    def _create_side_walls(self):
        h = self.player.ship_size[1]
        y = self.player.position[1]
        self.walls = []
        for x in (0.0, W):
            wall = Node(name='wall', position=(x, y), size=(3.0, h))
            attach(wall, Body(rectangle(3.0, h), category=CAT_WALL, contact=CAT_PLAYER, collision=CAT_WALL))
            self.add_child(wall)
            self.walls.append(wall)

    # enemies

    def create_enemy_with_type(self, code):
        """createEnemyWithType: builds the ship (which starts its entrance), gives it a looping engine sound
        linked to it, and adds it to the scene."""
        ship = SpaceShip.enemy(code, self)
        ship.z = 5
        aureal = self.services.aureal
        sound = engine_sound(code)
        key = aureal.next_key()
        if sound is not None:
            aureal.add_sound(sound[0], sound[1], key)
        ship.sound_id = key
        aureal.link(key, ship)
        aureal.play_forever(key, ship.position)
        aureal.sound_id += 1
        self.add_child(ship)
        return ship

    # power-ups

    def release_power_up(self, kind):
        """releasePowerUpOfType: a power-up with a looping radar beep linked to it."""
        p = PowerUp(kind, self)
        aureal = self.services.aureal
        key = aureal.next_key()
        aureal.add_sound('beep_radar', 'caf', key)
        aureal.sound_id += 1
        aureal.link(key, p)
        aureal.play_forever(key, p.position)
        self.add_child(p)
        return p

    def collect_power_up(self, p):
        p.remove_from_parent()
        s, voice, fx = self.services.strings, self.services.voice, self.services.effects
        if p.kind == LIFE:
            voice.speak(s.get('life_grabbed'), RATE_STATUS)
            fx.play('Power-Up.caf')
            self.player.restore_life()
        elif p.kind == SHIELD:
            voice.speak(s.get('shield_grabbed'), RATE_STATUS)
            fx.play('Power-Up.caf')
            self.player.restore_shield()
        elif p.kind == SPEED:
            voice.speak(s.get('speed_grabbed'), RATE_STATUS)
            fx.play('Power-Up.caf')
            self.velocidade = W / 10.0
            self.player.starting_power_up(SPEED)
        elif p.kind == FAST_SHOT:
            self.power_up_shot = True
            voice.speak(s.get('fastShot_grabbed'), RATE_STATUS)
            fx.play('Power-Up.caf')
            self.player.starting_power_up(FAST_SHOT)

    def end_power_up(self, kind):
        """endPowerUpOfType: after 10 seconds."""
        s, voice = self.services.strings, self.services.voice
        if kind == FAST_SHOT:
            voice.speak(s.get('fastShot_end'), RATE_STATUS)
            self.power_up_shot = False
        elif kind == SPEED:
            voice.speak(s.get('speed_end'), RATE_STATUS)
            self.velocidade = W / self.services.globals.get_speed()

    # hooks for subclasses

    def destroy_enemy(self, code):
        """Called whenever an enemy is gone. Chapters, free mode and the tutorial override it."""

    def add_score(self, ship):
        self.score_counter += ship.score
        if self.stage_number == 0:
            # VoiceOver-only in the original, always on here (see DEVIATIONS).
            self.services.voice.speak(self.services.strings.format('freemode_Score', self.score_counter), RATE_MOVE)
        self.death_counter += 1

    def end_game(self):
        """BaseScene endGame: the scene becomes inactive (the fade-in overlay is visual only). Subclasses add
        their ending screen."""
        self.is_active = False

    def swipe_up(self):
        """Swipe up (Escape): the pause menu in gameplay scenes, which comes with the menus step."""

    # in-game menus (menuObjects)

    def open_menu(self, title, items):
        """Shows an in-game menu. items is a list of (label, action). Selection starts on the first item and
        the title and that item are spoken together, as "%@, %@"."""
        self.menu_title = title
        self.menu_items = list(items)
        self.menu_selection = 1
        self.in_menu = True
        self.services.voice.speak('%s, %s' % (title, self.menu_items[0][0]), RATE_STATUS)

    in_menu = False

    def _menu_count(self):
        return len(self.menu_items) + 1   # index 0 is the title

    def menu_next(self):
        """Swipe right with VoiceOver (the down arrow here)."""
        if not self.in_menu:
            return
        fx = self.services.effects
        if self.menu_selection + 1 < self._menu_count():
            fx.play('chageButton.mp3')
            self.menu_selection += 1
            self.services.voice.speak(self.menu_items[self.menu_selection - 1][0], RATE_STATUS)
        elif self.menu_selection == 1 and self._menu_count() == 2:
            fx.play('chageButton.mp3')
            self.services.voice.speak(self.menu_items[0][0], RATE_STATUS)
        else:
            fx.play('errorButton.mp3')

    def menu_previous(self):
        """Swipe left with VoiceOver (the up arrow here)."""
        if not self.in_menu:
            return
        fx = self.services.effects
        if self.menu_selection < 2:
            fx.play('errorButton.mp3')
            return
        fx.play('chageButton.mp3')
        self.menu_selection -= 1
        self.services.voice.speak(self.menu_items[self.menu_selection - 1][0], RATE_STATUS)

    def menu_activate(self):
        """Double tap with VoiceOver (Enter here): the accept sound, then the item's action."""
        if not self.in_menu:
            return
        self.services.effects.play('acceptButton.mp3')
        self.in_menu = False
        self.menu_items[self.menu_selection - 1][1]()

    def _schedule_end_game(self):
        self.services.scheduler.after(END_GAME_DELAY, self.end_game)

    # contacts (didBeginContact:)

    def did_begin_contact(self, a, b):
        if self.game_paused:
            return
        fx = self.services.effects
        hit = _pair(a, b, CAT_ENEMY, CAT_PLAYER_SHOT)
        if hit:
            enemy, shot = hit[0].node, hit[1].node
            burst_and_remove(shot, ENEMY_BURST_FRAMES)
            fx.play('enemy_hit.caf')
            if enemy.inflict_damage(self.services.globals.get_shot()):
                self.destroy_enemy(enemy.code)
                self.services.scheduler.after(SCORE_DELAY, lambda: self.add_score(enemy))
        ram = _pair(a, b, CAT_ENEMY, CAT_PLAYER)
        if ram:
            enemy = ram[0].node
            self.destroy_enemy(enemy.code)
            fx.play('player_hit.caf')
            if self.player.inflict_damage(enemy.shoot_damage):
                self._schedule_end_game()
            enemy.inflict_damage(enemy.life)
        struck = _pair(a, b, CAT_ENEMY_SHOT, CAT_PLAYER)
        if struck:
            shot = struck[0].node
            burst_and_remove(shot, SHOT_BURST_FRAMES)
            if self.last_shot_hit is not shot:
                self.last_shot_hit = shot
                fx.play('player_hit.caf')
                if self.player.inflict_damage(shot.ship.shoot_damage):
                    self.allow_move = False
                    self._schedule_end_game()
        clash = _pair(a, b, CAT_PLAYER_SHOT, CAT_ENEMY_SHOT)
        if clash:
            fx.play('colisaoTiro.mp3')
            burst_and_remove(clash[1].node, SHOT_BURST_FRAMES)
            burst_and_remove(clash[0].node, SHOT_BURST_FRAMES)
        grab = _pair(a, b, CAT_POWERUP, CAT_PLAYER)
        if grab and grab[0].node.parent is not None:
            self.collect_power_up(grab[0].node)
        laser = _pair(a, b, CAT_LASER, CAT_PLAYER)
        if laser:
            self.toaster = laser[0].node
            if self.player.inflict_damage(self.toaster.ship.shoot_damage):
                self._schedule_end_game()
        if _pair(a, b, CAT_SWOOSH_LEFT, CAT_ENEMY_SHOT):
            fx.play('Swoosh_Left.caf')
        elif _pair(a, b, CAT_SWOOSH_RIGHT, CAT_ENEMY_SHOT):
            fx.play('Swoosh_Right.caf')
        if a.category == CAT_WALL or b.category == CAT_WALL:
            if self.should_lateral_play_hit_sound:
                if self.talking_move:
                    self.services.voice.speak(self.services.strings.get('talkingMove_F'), RATE_MOVE)
                right = self.player.position[0] >= W * 0.5
                fx.play('bound_right.mp3' if right else 'bound_left.mp3')
                self.should_lateral_play_hit_sound = False

    def did_end_contact(self, a, b):
        if self.game_paused:
            return
        if a.category == CAT_LASER or b.category == CAT_LASER:
            self.toaster = None
        if a.category == CAT_WALL or b.category == CAT_WALL:
            self.should_lateral_play_hit_sound = True
