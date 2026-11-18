"""The campaign: ChapterScene and the nine chapters (see docs/CHAPTERS.md).

Each chapter has four stages. A stage opens with I.C.A.R.U.S. lines and its first ships, and destroyEnemy:
drives every later spawn and the win. The kill rules are translated from each ChapterNScene destroyEnemy: in
the original and checked against it in the emulator by tests/test_chapters.py, so the odd ones are kept as
they are. Counter names follow the original ivars: small, medium and laser totals, and how many of each are
in the scene ("small_in" is smallEnemyInScene).

The message window that shows each line is visual only. The lines are spoken, as in the original.
"""
from ..engine import actions as A
from . import rand
from .base_scene import BaseScene, H, W
from .powerups import FAST_SHOT, LIFE, SHIELD, SPEED

ICARUS_RATE = 0.55
VICTORY_FLIGHT = (1.0, 3.0, 1.0, 2.0)   # defaultVictoriousAnimation: wait, fly up, wait, shrink
VICTORY_SCREEN_DELAY = 2.0              # endGameVictorious: then missionComplete
BOSS_APPROACH = 4.0                     # makeBossEntrance in chapters 1 and 3: the blurred approach
DELAYED_SPAWN = 3.0                     # performSelector:createSmallEnemy2 afterDelay:3


class ChapterScene(BaseScene):
    CHAPTER = 0
    SPAWNS = {}          # method name: (counter, ship code)

    def __init__(self, services, tilt_source=None, stage=1, on_select=None, on_next=None, on_restart=None,
                 play_intro=None):
        super().__init__(services, tilt_source)
        self.stage_number = stage
        self.services.globals.free_mode = False
        self.small = self.medium = self.laser = 0
        self.small_in = self.medium_in = self.laser_in = 0
        self.released_power_up = False
        self.the_end = False
        self.the_boss = None
        self.on_select = on_select or (lambda: None)     # backMenuCampanha: the level selection
        self.on_next = on_next or (lambda: None)         # proximoMissao: the next level
        self.on_restart = on_restart or (lambda: None)   # reinicia
        # playIntroCutSceneChapter: calls on_done when the cutscene ends. Cutscenes come with the menus step.
        self.play_intro = play_intro or (lambda chapter, on_done: on_done())

    # start

    def did_move_to_view(self):
        self.allow_move = False
        self.allow_shoot = False
        if self.stage_number == 1:
            self.play_intro(self.CHAPTER, self._after_intro)
        else:
            self._after_intro()

    def _after_intro(self):
        BaseScene.did_move_to_view(self)
        self.next_stage()

    def next_stage(self):
        self.small = self.medium = self.laser = 0
        self.small_in = self.medium_in = self.laser_in = 0
        self.allow_move = True
        self.allow_shoot = True
        self.opening(self.stage_number)

    def opening(self, stage):
        raise NotImplementedError

    # helpers

    def create(self, name):
        """createSmallEnemy1 and the like: count the ship, then createEnemyWithType:."""
        counter, code = self.SPAWNS[name]
        setattr(self, counter, getattr(self, counter) + 1)
        setattr(self, counter + '_in', getattr(self, counter + '_in') + 1)
        return self.create_enemy_with_type(code)

    def _dec(self, counter):
        """counter -= 1, returning the value before."""
        old = getattr(self, counter)
        setattr(self, counter, old - 1)
        return old

    def say(self, key, pre=0.0, post=0.0, then=None):
        """presentText:withSpeaker: "I.C.A.R.U.S." with speakSentence:withRate:0.55 pre post completition:."""
        text = self.services.strings.get(key)
        self.services.voice.speak_then(text, ICARUS_RATE, pre, post, then or (lambda: None))

    def say_chain(self, lines, then):
        """Lines spoken one after another, each starting in the previous one's completion."""
        if not lines:
            then()
            return
        key, pre, post = lines[0]
        self.say(key, pre, post, lambda: self.say_chain(lines[1:], then))

    def later(self, seconds, fn):
        self.services.scheduler.after(seconds, fn)

    def boss_now(self, code):
        """makeBossEntrance without an approach: the boss spawns and the player can move and shoot again."""
        self.the_boss = self.spawn_boss(code)
        self.allow_move = True
        self.allow_shoot = True

    def boss_after_approach(self, code):
        """makeBossEntrance with the blurred approach sprite (visual), which takes 4 seconds."""
        self.run(A.wait(BOSS_APPROACH), completion=lambda: self.boss_now(code))

    def stage4_loop(self, lines, then):
        self.allow_move = False
        self.allow_shoot = False
        self.say_chain(lines, then)

    # periodic

    def base_actions(self):
        super().base_actions()
        if self.player.life == 2 and not self.released_power_up:
            self.release_power_up(LIFE)
            self.released_power_up = True

    # winning

    def default_victorious_animation(self):
        """The ship waits a second, flies up off the screen, then shrinks; then endGameVictorious."""
        self.allow_move = False
        self.allow_shoot = False
        w1, fly, w2, shrink = VICTORY_FLIGHT
        p = self.player
        p.run(A.sequence([A.wait(w1), A.move_to(W * 0.5, H + 100.0, fly)]), completion=lambda: p.run(
            A.sequence([A.wait(w2), A.scale_to(0.5, shrink)]), completion=lambda: self.later(0.0, self.end_game_victorious)))

    def end_game_victorious(self):
        self.run(A.wait(VICTORY_SCREEN_DELAY), completion=self.mission_complete)

    def end_lvl_speech(self, key, pre, post, then, stop_controls=False):
        """The common endLvl: runs once, speaks the closing line, then continues."""
        if self.the_end:
            return
        self.the_end = True
        if stop_controls:
            self.allow_move = False
            self.allow_shoot = False
        self.say(key, pre, post, then)

    def mission_complete(self):
        """missionComplete: records progress, then the "Mission completed" menu."""
        self._record_progress()
        s = self.services.strings
        self.open_menu(s.get('missao_completou'), [(s.get('missao_selecionar'), self.on_select),
                                                   (s.get('missao_proximo'), self.on_next)])

    def _record_progress(self):
        g, save = self.services.globals, self.services.save
        fase, capitulo = self.stage_number, self.CHAPTER
        if fase != g.last_level or capitulo != g.last_chapter:
            return
        if g.last_level < 4:
            key = 'Missao %d Capitulo %d Completa' % (fase + 1, capitulo)
            if not save.get(key):
                g.last_level += 1
                g.save_progress(save)
                save.set(key, True)
        elif g.last_chapter <= 8:
            key = 'Missao 1 Capitulo %d Completa' % (g.last_chapter + 1)
            if not save.get(key):
                save.set('ControleCapitulo', 'yes')
                save.synchronize()
                g.last_level = 1
                g.last_chapter += 1
                g.save_progress(save)
                save.set('Missao %d Capitulo %d Completa' % (g.last_level, g.last_chapter), True)

    # losing

    def end_game(self):
        """The player died (or chapter 6 lost too many allies): silence, then the campaign game over menu."""
        self.services.aureal.stop_all()
        self.services.voice.stop()
        super().end_game()
        self.game_over_screen()

    def game_over_screen(self):
        """telaGameOverCampanha."""
        s = self.services.strings
        self.open_menu(s.get('game_over'), [(s.get('missao_selecionar'), self.on_select),
                                            (s.get('game_proximo'), self.on_restart)])

    def stop_audio(self):
        self.services.aureal.stop_all()
        self.services.voice.stop()
        self._accel_timer.invalidate()
        self.remove_all_children()
        self.remove_all_actions()


class Chapter1Scene(ChapterScene):
    """Refueling."""
    CHAPTER = 1
    SPAWNS = {'small': ('small', 0), 'tank': ('small', 46), 'medium': ('medium', 2), 'laser1': ('laser', 7),
              'laser2': ('laser', 8)}

    def opening(self, stage):
        if stage == 1:
            self.say('chap1_icarus1', 1.0, 0.0, lambda: self.create('small'))
        elif stage == 2:
            self.create('small')
            self.create('medium')
        elif stage == 3:
            self.say('chap1_icarus1.2', 1.0, 0.0, lambda: (self.create('tank'), self.create('laser1')))
        else:
            self.stage4_loop([('chap1_icarus2', 0.0, 1.0), ('chap1_icarus3', 0.0, 0.0)],
                             lambda: self.run(A.wait(0.5), completion=self.make_boss_entrance))

    def make_boss_entrance(self):
        self.boss_after_approach(1)

    def destroy_enemy(self, code):
        st = self.stage_number
        if st == 3:
            if code in (0, 46):
                if self._dec('small_in') <= 1 and (self.laser < 3 or self.laser_in != 0):
                    self.create('small' if rand.arc4random() & 1 == 0 else 'tank')
            elif code == 7:
                if self._dec('laser_in') <= 1:
                    if self.laser < 1:
                        self.create('laser1')
                    elif self.laser == 1:
                        self.release_power_up(LIFE)
                        self.create('laser2')
            elif code == 8:
                if self._dec('laser_in') <= 1 and self.laser < 5:
                    self.create('laser2')
            if self.laser == 5 and self.small_in == 0:
                self.default_victorious_animation()
        elif st == 2:
            if code == 7:
                if self._dec('laser_in') <= 1 and self.laser < 3:
                    self.create('laser1')
            elif code == 2:
                if self._dec('medium_in') <= 1 and self.medium <= 3:
                    self.create('medium')
                elif self.medium == 4:
                    self.release_power_up(LIFE)
                    self.create('laser1')
            elif code == 0:
                if self._dec('small_in') <= 1 and (self.laser < 3 or self.laser_in != 0):
                    self.create('small')
            if self.laser == 3 and self.small_in == 0:
                self.default_victorious_animation()
        elif st == 1:
            if code == 2:
                if self._dec('medium_in') <= 1 and self.medium < 3:
                    self.create('medium')
                    if self.medium == 2:
                        self.release_power_up(LIFE)
            elif code == 0:
                if self._dec('small_in') <= 1 and (self.medium < 3 or self.medium_in != 0):
                    self.create('small')
                    if self.small == 5:
                        self.create('medium')
            if self.medium == 3 and self.small_in == 0:
                self.default_victorious_animation()
        else:
            self.end_lvl()

    def end_lvl(self):
        """Docking at the refuelling station: the station sprite slides in over 10 seconds while the line is
        spoken, then the ship flies to it and shrinks for 7 seconds."""
        if self.the_end:
            return
        self.the_end = True
        self.allow_move = False
        self.allow_shoot = False
        p = self.player
        p.run(A.move_to(256.0, p.position[1], 2.0))
        self.run(A.wait(1.0), completion=lambda: self.say('chap1_icarus4'))

        def dock():
            p.run(A.move_to(284.0, H, 7.0))
            p.run(A.sequence([A.wait(2.0), A.scale_to(0.1, 5.0)]), completion=self.end_game_victorious)
        self.run(A.wait(10.0), completion=dock)


CHAPTERS = {c.CHAPTER: c for c in (
    Chapter1Scene,
)}
