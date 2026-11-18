"""TutorialScene: the six tutorial sections (see docs/MODES.md, Tutorial).

Narration plays through the scene's own player, each clip starting when the previous one ends. Clip names
are Localizable.strings keys (tut_1.0 and so on) that resolve to the localized mp3.
"""
from ..audio.players import Narration
from ..engine import actions as A
from .base_scene import BaseScene, H

FIRE_TIMER_LASER = 3.0
FIRE_TIMER_ENEMY = 1.0


class TutorialScene(BaseScene):
    def __init__(self, services, tilt_source=None, tutorial_type=1, on_select=None, on_next=None):
        super().__init__(services, tilt_source)
        self.tutorial_type = tutorial_type
        self.voice_player = Narration(services.audio, services.scheduler)
        self.first_enemy = None
        self.laser_ship = None
        self.aux = 0
        self.on_select = on_select or (lambda: None)   # backMenuController: back to tutorial selection
        self.on_next = on_next or (lambda: None)       # proximoTutorial: the next section

    # flow

    def did_move_to_view(self):
        super().did_move_to_view()
        getattr(self, 'tutorial%d' % self.tutorial_type)()

    def play(self, key, then=None):
        self.voice_player.play(self.services.strings.sound_path(key), then)

    def chain(self, keys, then):
        """Plays narration keys back to back, then runs `then`."""
        if not keys:
            then()
            return
        self.play(keys[0], lambda: self.chain(keys[1:], then))

    def play_effect_then(self, key, then):
        """SKAction playSoundFileNamed waitForCompletion YES, used inside tutorial 2's choreography."""
        name = self.services.strings.get(key)
        self.services.effects.play_then(name, then, self.services.scheduler)

    # sections

    def tutorial1(self):
        """Movement: talking movement on, four clips, then free movement. It ends with swipe up."""
        self.allow_shoot = False
        self.allow_move = False
        self.talking_move = True
        self.chain(['tut_1.0', 'tut_1.1', 'tut_1.2', 'tut_1.3'], lambda: setattr(self, 'allow_move', True))

    def tutorial2(self):
        """Enemies: a demo ship shows where things come from, then hunts you. Shooting stays off."""
        self.allow_move = False
        self.allow_shoot = False
        self.player.receive_damage = False   # sections 2 to 6 make the player invulnerable

        def arrive():
            e = self.first_enemy = self.create_enemy_with_type(1)
            e.invalidate_movement_and_shoot()
            e.run(A.move_to(160.0, H * 0.8, 1.5))
            self.chain(['tut_2.1', 'tut_2.2', 'tut_2.3'], to_left)

        def to_left():
            self.first_enemy.run(A.move_to_x(20.0, 1.0))
            self.run(A.wait(2.0), completion=lambda: self.play_effect_then('tut_2.4', to_right))

        def to_right():
            self.first_enemy.run(A.move_to_x(300.0, 2.0))
            self.run(A.wait(1.0), completion=lambda: self.play_effect_then('tut_2.5', shot_one))

        def shot_one():
            e = self.first_enemy
            e.manual_shot()
            e.run(A.move_to_x(20.0, 2.0), completion=lambda: self.run(
                A.wait(1.0), completion=lambda: self.play_effect_then('tut_2.6', shot_two)))

        def shot_two():
            e = self.first_enemy
            e.manual_shot()
            e.run(A.move_to_x(160.0, 1.0), completion=lambda: self.run(
                A.wait(0.5), completion=lambda: self.play_effect_then('tut_2.7', hunt)))

        def hunt():
            e = self.first_enemy
            e.manual_shot()
            self.allow_move = True
            e.initialize_movement()
            e.initialize_shoot_with_time(FIRE_TIMER_ENEMY)
        self.play('tut_2.0', arrive)

    def tutorial3(self):
        """Attack: five clips, then shoot ships that keep coming (they move but don't shoot)."""
        self.allow_move = False
        self.allow_shoot = False
        self.player.receive_damage = False   # sections 2 to 6 make the player invulnerable

        def go():
            self.allow_move = True
            self.allow_shoot = True
            self.create_enemy()
        self.chain(['tut_3.0', 'tut_3.1', 'tut_3.2', 'tut_3.3', 'tut_3.4'], go)

    def tutorial4(self):
        """Battle: six clips, then an invulnerable fighter and timed speed and fast-shot drops."""
        self.allow_move = False
        self.allow_shoot = False
        self.player.receive_damage = False   # sections 2 to 6 make the player invulnerable

        def go():
            self.allow_move = True
            self.allow_shoot = True
            self.power_up_type1, self.power_up_type2 = 3, 4
            self.time_between_power_ups = 20
            self.time_to_next_power_up = 5
            self.create_enemy()
        self.chain(['tut_4.0', 'tut_4.1', 'tut_4.2', 'tut_4.3', 'tut_4.4', 'tut_4.5'], go)

    def tutorial5(self):
        """Basic: a laser ship demonstrates its laser, then fights. After it, three fuel tanks to dodge."""
        self.allow_move = False
        self.allow_shoot = False
        self.player.receive_damage = False   # sections 2 to 6 make the player invulnerable

        def laser():
            e = self.first_enemy = self.create_enemy_with_type(7)
            e.invalidate_movement_and_shoot()
            e.run(A.move_to(248.0, H * 0.8, 1.5))
            self.play('tut_5.2', demo)

        def demo():
            self.first_enemy.manual_shot()
            self.play('tut_5.3', fight)

        def fight():
            self.allow_move = True
            self.allow_shoot = True
            self.first_enemy.initialize_shoot_with_time(FIRE_TIMER_LASER)
        self.chain(['tut_5.0', 'tut_5.1'], laser)

    def tutorial6(self):
        """Special: eleven clips (tut_6.2 plays the 6.0 file, as in the original), then a short gauntlet."""
        self.allow_move = True
        self.allow_shoot = True
        self.player.receive_damage = False   # sections 2 to 6 make the player invulnerable
        keys = ['tut_6.%d' % i for i in range(11)]
        self.chain(keys, self.create_enemy)

    # spawning

    def create_enemy(self):
        t = self.tutorial_type
        if t == 3:
            e = self.first_enemy = self.create_enemy_with_type(0)
            e.invalidate_movement_and_shoot()
            e.initialize_movement()
        elif t == 4:
            e = self.first_enemy = self.create_enemy_with_type(0)
            e.receive_damage = False
        elif t == 5:
            if self.aux == 0:
                self.allow_shoot = False
                self.play('tut_5.4', lambda: setattr(self, 'first_enemy', self.create_enemy_with_type(46)))
            elif self.aux in (1, 2):
                self.first_enemy = self.create_enemy_with_type(46)
            else:
                self.end_tutorial()
            self.aux += 1
        elif t == 6:
            if self.aux == 0:
                self.create_enemy_with_type(0)
            elif self.aux == 1:
                self.create_enemy_with_type(3)
            elif self.aux in (2, 3):
                self.create_enemy_with_type(46)
            else:
                self.end_tutorial()
            self.aux += 1

    def destroy_enemy(self, code):
        if self.tutorial_type in (3, 5, 6):
            self.create_enemy()

    # ending

    def swipe_up(self):
        self.end_tutorial()

    def end_tutorial(self):
        self.voice_player.stop()
        self.remove_all_actions()
        self.destroi_cena()
        self.end_game()

    def destroi_cena(self):
        for ship in (self.first_enemy, self.laser_ship):
            if ship is not None:
                ship.remove_all_actions()
                ship.remove_from_parent()
        self.first_enemy = self.laser_ship = None

    def end_game(self):
        if not self.is_active:
            return
        super().end_game()
        self.tutorial_completo()

    def tutorial_completo(self):
        s = self.services.strings
        last = self.tutorial_type > 5
        # Next tutorial, then Select tutorial. After the last tutorial both go back to the selection.
        self.open_menu(s.get('tutorial_completou'), [
            (s.get('tutorial_proximo'), self.on_select if last else self.on_next),
            (s.get('tutorial_selecionar'), self.on_select),
        ])

    def stop_audio(self):
        """willMoveFromView: silence everything when leaving the scene."""
        self.voice_player.stop()
        self.services.aureal.stop_all()
        self.services.voice.stop()
        self._accel_timer.invalidate()
        self.remove_all_children()
        self.remove_all_actions()

