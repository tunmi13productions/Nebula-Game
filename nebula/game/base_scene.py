"""BaseScene, the shared gameplay scene. This step covers the player, steering, the listener, the side walls
and talking movement. See docs/NOTES.md (input and movement, physics categories, swoosh fields and side walls).
"""
from ..engine import actions as A
from ..engine.nodes import Node, Scene
from ..engine.physics import Body, PhysicsWorld, attach, rectangle
from .ship import CAT_PLAYER, CAT_WALL, SpaceShip

W, H = 320.0, 568.0
ACCEL_INTERVAL = 0.2      # CMMotionManager accelerometerUpdateInterval
DEAD_ZONE = 0.04          # outputAccelerationData: smaller readings count as zero
STATE_THRESHOLD = 0.05    # update: beyond this the ship is moving left or right
BASE_LOOP = 1.0           # "BaseActions"
TALK_INTERVAL = 0.3       # "TalkingMovement"
POSITION_FACTOR_IPHONE = 0.17
RATE_STATUS, RATE_MOVE = 0.55, 0.6

STOPPED, RIGHT, LEFT = 0, 1, 2


class BaseScene(Scene):
    def __init__(self, services, tilt_source=None):
        super().__init__(W, H)
        self.services = services
        self.tilt_source = tilt_source or (lambda: 0.0)   # returns acceleration.x; the keyboard stands in for tilt
        self.physics_world = PhysicsWorld()
        self.allow_move = True
        self.allow_shoot = True
        self.game_paused = False
        self.talking_move = False
        self._talking_running = False
        self.current_max_accel_x = 0.0
        self.movement_state = STOPPED
        self._last_spoken_state = STOPPED
        self.should_lateral_play_hit_sound = True
        self.velocidade = W / services.globals.get_speed()

        self.player = SpaceShip.player(W, H, services.globals)
        w, h = self.player.ship_size
        self.player.position = (W * 0.5, h + (H / 3) * POSITION_FACTOR_IPHONE)
        self.player.z = 5
        self.add_child(self.player)
        services.aureal.configure(H * 1.25, self.player.position, self, max_x=W)
        self._create_side_walls()

        self._accel_timer = services.scheduler.every(ACCEL_INTERVAL, lambda t: self._sample_accelerometer())
        self.run(A.repeat_forever(A.sequence([A.run_block(self.base_actions), A.wait(BASE_LOOP)])), key='BaseActions')

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

    # BaseActions, every second

    def base_actions(self):
        if self.game_paused:
            return
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

    # side walls

    def _create_side_walls(self):
        h = self.player.ship_size[1]
        y = self.player.position[1]
        self.walls = []
        for x in (0.0, W):
            wall = Node(name='wall', position=(x, y), size=(3.0, h))
            attach(wall, Body(rectangle(3.0, h), category=CAT_WALL, contact=CAT_PLAYER, collision=CAT_WALL))
            self.add_child(wall)
            self.walls.append(wall)

    def did_begin_contact(self, a, b):
        if self.game_paused:
            return
        if a.category == CAT_WALL or b.category == CAT_WALL:
            if self.should_lateral_play_hit_sound:
                if self.talking_move:
                    self.services.voice.speak(self.services.strings.get('talkingMove_F'), RATE_MOVE)
                right = self.player.position[0] >= W * 0.5
                self.services.effects.play('bound_right.mp3' if right else 'bound_left.mp3')
                self.should_lateral_play_hit_sound = False

    def did_end_contact(self, a, b):
        if self.game_paused:
            return
        if a.category == CAT_WALL or b.category == CAT_WALL:
            self.should_lateral_play_hit_sound = True
