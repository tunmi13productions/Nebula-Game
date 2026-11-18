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
from .cutscene import CutScene
from .map_generator import MapGenerator
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
        # playIntroCutSceneChapter:completition: before stage 1; on_done starts the chapter.
        self.play_intro = play_intro or self._play_cutscene
        self.cutscene = None

    # start

    def did_move_to_view(self):
        self.allow_move = False
        self.allow_shoot = False
        self.map = MapGenerator(self, self.services)       # initChapterNStage:onScene:
        self.map.chapter(self.CHAPTER, self.stage_number)
        if self.stage_number == 1:
            self.play_intro(self.CHAPTER, self._after_intro)
        else:
            self._after_intro()

    def _play_cutscene(self, chapter, on_done):
        self.cutscene = CutScene(self.services, chapter, on_done)
        self.cutscene.start()

    def cutscene_running(self):
        return self.cutscene is not None and self.cutscene.running

    def player_shoot(self):
        """A tap skips the cutscene (Space or Enter here); otherwise Space fires."""
        if self.cutscene_running():
            self.cutscene.skip()
        else:
            super().player_shoot()

    def menu_activate(self):
        if self.cutscene_running() and not self.in_menu:
            self.cutscene.skip()
        else:
            super().menu_activate()

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
        """missionComplete: records progress, then the "Mission completed" menu: Next level, Select level.
        After level 4 the saved chapter becomes the next one (level 1), and Next level goes back to the
        level selection (backMenuCampanha), which then opens on that chapter. After chapter 9 that's a
        "chapter 10" with no strings, as in the original."""
        self._record_progress()
        s = self.services.strings
        on_next = self.on_next
        if self.stage_number == 4:
            save = self.services.save
            save.set_integer('capitulo', self.CHAPTER + 1)
            save.set_integer('fase', 1)
            save.synchronize()
            on_next = self.on_select
        self.open_menu(s.get('missao_completou'), [(s.get('missao_proximo'), on_next),
                                                   (s.get('missao_selecionar'), self.on_select)])

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
        """telaGameOverCampanha: New game (restart the level), then Select level."""
        s = self.services.strings
        self.open_menu(s.get('game_over'), [(s.get('game_proximo'), self.on_restart),
                                            (s.get('missao_selecionar'), self.on_select)])

    def pause_restart(self):
        self.on_restart()

    def pause_leave(self):
        self.on_select()

    def stop_audio(self):
        if getattr(self, 'map', None) is not None:
            self.map.stop()
        if self.cutscene is not None:
            self.cutscene.stop()
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


class Chapter2Scene(ChapterScene):
    """Direction."""
    CHAPTER = 2
    SPAWNS = {'small1': ('small', 10), 'small2': ('small', 41), 'medium1': ('medium', 40), 'medium2': ('medium', 43),
              'laser1': ('laser', 42)}

    def opening(self, stage):
        if stage == 1:
            self.say('chap2_icarus1', 1.0, 0.0, lambda: self.create('small1'))
        elif stage == 2:
            self.say('chap2_icarus2', 1.0, 0.0, lambda: (self.create('small1'), self.create('small2')))
        elif stage == 3:
            self.create('small2')
            self.create('laser1')
        else:
            self.stage4_loop([('chap2_icarus3', 1.0, 0.0)], lambda: self.boss_now(2))

    def destroy_enemy(self, code):
        st = self.stage_number
        if st == 3:
            if code == 43:
                if self._dec('medium_in') <= 1 and self.medium < 2:
                    self.release_power_up(LIFE)
                    self.create('medium2')
            elif code == 42:
                if self._dec('laser_in') <= 1 and self.laser < 5:
                    self.create('medium2' if self.laser > 3 else 'laser1')
            elif code == 41:
                if self._dec('small_in') <= 1 and (self.medium < 2 or self.medium_in > 0):
                    self.create('small2')
            if self.medium == 2 and self.small_in == 0:
                self.default_victorious_animation()
        elif st == 2:
            if code == 42:
                if self._dec('laser_in') <= 1 and self.laser < 4:
                    if self.laser == 2:
                        self.release_power_up(LIFE)
                    self.create('laser1')
            elif code in (41, 10):
                if self._dec('small_in') <= 1:
                    spawn_small = True
                    if self.small > 3:
                        if self.laser < 4:
                            if self.laser == 0:
                                self.release_power_up(LIFE)
                                self.create('laser1')
                        elif self.laser_in < 1:
                            spawn_small = False
                    if spawn_small:
                        self.create('small2')
            if self.laser == 4 and self.small_in == 0:
                self.default_victorious_animation()
        elif st == 1:
            if code == 40:
                if self._dec('medium_in') <= 1 and self.medium < 5:
                    self.create('medium1')
            elif code == 10:
                if self._dec('small_in') <= 1 and (self.medium < 5 or self.medium_in != 0):
                    self.create('small1')
                    if self.small == 2:
                        self.create('medium1')
            if self.medium == 5 and self.small_in == 0:
                self.default_victorious_animation()
        else:
            self.end_lvl()

    def end_lvl(self):
        self.end_lvl_speech('chap2_icarus4', 1.0, 0.0, self.default_victorious_animation)


class Chapter3Scene(ChapterScene):
    """Hyperdrive."""
    CHAPTER = 3
    SPAWNS = {'small1': ('small', 43), 'small2': ('small', 22), 'small3': ('small', 21), 'medium1': ('medium', 6),
              'medium2': ('medium', 20), 'laser1': ('laser', 23)}

    def opening(self, stage):
        if stage == 1:
            self.say('chap3_icarus1', 1.0, 0.0, lambda: (self.create('small1'), self.create('medium1')))
        elif stage == 2:
            self.create('small2')
        elif stage == 3:
            self.say_chain([('chap3_icarus3', 1.0, 0.0), ('chap3_icarus4', 0.0, 0.0)],
                           lambda: (self.create('small2'), self.create('medium2')))
        else:
            self.stage4_loop([('chap3_icarus5', 1.0, 0.0)], lambda: self.boss_after_approach(3))

    def destroy_enemy(self, code):
        st = self.stage_number
        if st == 3:
            if code == 20:
                if self._dec('medium_in') <= 1:
                    if self.medium < 4:
                        self.create('medium2')
                    else:
                        self.release_power_up(LIFE)
                        self.release_power_up(LIFE)
                        self.create('laser1')
            elif code == 21:
                if self._dec('small_in') <= 1 and (self.laser < 2 or self.laser_in > 0):
                    self.create('small3')
            elif code == 22:
                if self._dec('small_in') <= 1:
                    if self.small < 2:
                        self.create('small2')
                    else:
                        self.release_power_up(SPEED)
                        self.release_power_up(FAST_SHOT)
                        self.create('small3')
            elif code == 23:
                if self._dec('laser_in') <= 1 and self.laser < 2:
                    self.create('laser1')
            if self.laser == 2 and self.small_in == 0:
                self.default_victorious_animation()
        elif st == 2:
            if code == 20:
                if self._dec('medium_in') <= 1:
                    if self.medium < 5:
                        self.create('medium2')
                    else:
                        self.release_power_up(LIFE)
                        self.create('laser1')
            elif code == 23:
                if self._dec('laser_in') <= 1 and self.laser < 4:
                    if self.laser == 2:
                        self.release_power_up(LIFE)
                    self.create('laser1')
            elif code == 22:
                if self._dec('small_in') <= 1:
                    if self.small > 5 and self.laser > 3 and self.laser_in < 1:
                        pass
                    else:
                        if self.small > 5 and self.medium == 0:
                            self.release_power_up(FAST_SHOT)
                            self.create('medium2')
                        self.create('small2')
            if self.laser == 4 and self.small_in == 0:
                self.default_victorious_animation()
        elif st == 1:
            if code == 6:
                if self._dec('medium_in') <= 1 and self.medium < 2:
                    self.create('medium1')
            elif code == 43:
                if self._dec('small_in') <= 1 and self.small < 2:
                    self.create('small1')
            if self.medium == 2 and self.small == 2 and self.small_in <= 0 and self.medium_in <= 0:
                self.end_stage1()
        else:
            self.default_victorious_animation()

    def end_stage1(self):
        """The warp jump: the line, then the warp sound, and the stage is won."""
        self.allow_move = False
        self.allow_shoot = False

        def jump():
            p = self.player
            p.run(A.move_to_y(H, 3.0))
            self.services.effects.play('science_fiction_warp_dimensional.mp3')
            self.end_game_victorious()
        self.say('chap3_icarus2', 0.5, 0.0, jump)


class Chapter4Scene(ChapterScene):
    """Home. Rocks only: createSmallEnemy rolls 0 to 3 and compares it with 49, 48 and 47, which never match,
    so it always spawns ship 50. Original bug, kept."""
    CHAPTER = 4

    def create_small(self):
        roll = rand.between(0, 3)
        code = {49: 49, 48: 48, 47: 47}.get(roll, 50)   # roll is 0 to 3, so this is always 50
        self.small += 1
        self.small_in += 1
        return self.create_enemy_with_type(code)

    def opening(self, stage):
        if stage == 1:
            self.say('chap4_icarus1', 0.5, 0.0, lambda: self._boss(4))
        elif stage == 2:
            self.say('chap4_icarus2', 0.5, 0.0, self.create_small)
        elif stage == 3:
            self.say('chap4_icarus3', 0.5, 0.0, lambda: self._boss(6))
        else:
            self.say('chap4_icarus4', 0.5, 0.5, lambda: self._boss(10))

    def _boss(self, code):
        self.allow_move = False
        self.allow_shoot = False
        self.boss_now(code)

    def destroy_enemy(self, code):
        st = self.stage_number
        if st == 2:
            old = self._dec('small_in')
            if self.small < 5:
                self.create_small()
            elif self.small < 20:
                if old < 2:
                    self.create_small()
                    self.create_small()
                elif old <= 2:
                    self.create_small()
            if self.small >= 20 and self.small_in <= 0:
                self.default_victorious_animation()
        elif st in (1, 3):
            self.default_victorious_animation()
        else:
            self.end_lvl()

    def end_lvl(self):
        self.end_lvl_speech('chap4_icarus5', 0.5, 0.5, self.default_victorious_animation, stop_controls=True)


class Chapter5Scene(ChapterScene):
    """Burning."""
    CHAPTER = 5
    SPAWNS = {'small1': ('small', 28), 'small2': ('small', 29), 'medium1': ('medium', 31), 'laser1': ('laser', 30)}

    def opening(self, stage):
        if stage == 1:
            def go():
                self.create('small1')
                self.later(DELAYED_SPAWN, lambda: self.create('small2'))
            self.say_chain([('chap5_icarus1', 0.0, 0.0), ('chap5_icarus2', 0.0, 0.0)], go)
        elif stage == 2:
            self.create('small1')
            self.create('small2')
        elif stage == 3:
            self.create('medium1')
            self.create('laser1')
        else:
            self.stage4_loop([('chap5_icarus3', 0.0, 0.0)], lambda: self.boss_now(5))

    def destroy_enemy(self, code):
        st = self.stage_number
        if st == 3:
            if code == 28:
                if self._dec('small_in') < 6:
                    self.create('laser1')
            elif code == 29:
                if self._dec('small_in') < 3 and self.laser < 5:
                    self.create('medium1')
            elif code == 30:
                if self._dec('laser_in') <= 1 and self.laser < 5:
                    if self.laser == 2:
                        self.release_power_up(FAST_SHOT)
                        if self.laser == 5:
                            self.release_power_up(SHIELD)
                    self.create('small1')
            elif code == 31:
                self.medium_in -= 1
                if self.laser < 5:
                    self.create('small2')
            if self.laser >= 5 and self.small_in == 0 and self.medium_in == 0 and self.laser_in == 0:
                self.default_victorious_animation()
        elif st == 2:
            if code == 28:
                if self._dec('small_in') < 3:
                    if self.small < 3:
                        self.create('small1')
                    elif self.laser < 4:
                        self.create('laser1')
            elif code == 29:
                if self._dec('small_in') < 3 and self.laser < 4:
                    self.create('small2')
                elif self.small < 1 and self.laser == 4:
                    self.create('laser1')
                    self.release_power_up(FAST_SHOT)
            elif code == 30:
                if self._dec('laser_in') <= 1:
                    if self.laser < 4:
                        self.create('laser1')
                    elif self.laser == 4:
                        self.create('medium1')
            elif code == 31:
                self.medium_in -= 1
            if self.laser == 4 and self.small_in == 0 and self.laser_in == 0 and self.medium_in == 0:
                self.default_victorious_animation()
        elif st == 1:
            if code == 31:
                self.medium_in -= 1
            elif code == 29:
                old = self._dec('small_in')
                if old < 3:
                    if self.small < 6:
                        self.create('small2')
                    elif old < 2 and self.small <= 6:
                        self.create('medium1')
                        self.create('small1')
            elif code == 28:
                old = self._dec('small_in')
                if old < 3:
                    if self.small < 5:
                        self.create('small1')
                    elif old < 2 and self.small <= 6:
                        self.create('medium1')
                        self.create('small2')
            if self.small >= 6 and self.small_in == 0 and self.medium_in == 0 and self.laser_in == 0:
                self.default_victorious_animation()
        else:
            self.end_lvl()

    def end_lvl(self):
        self.end_lvl_speech('chap5_icarus4', 0.5, 0.5, self.make_player_turn_around)

    def make_player_turn_around(self):
        """The ship swings right, loops back across and dives off the bottom (4.5 seconds)."""
        self.allow_move = False
        self.allow_shoot = False
        p = self.player
        loop = A.group([A.move_by(-300.0, 0.0, 1.5),
                        A.sequence([A.move_by(0.0, H / 2, 0.75), A.move_by(0.0, -H / 2, 0.75)]),
                        A.rotate_by(3.14159, 1.5)])
        p.run(A.move_to(300.0, H / 2, 1.0), completion=lambda: p.run(loop, completion=lambda: p.run(
            A.move_by(0.0, -H, 2.0), completion=self.end_game_victorious)))


class Chapter6Scene(ChapterScene):
    """Exodus. Allied ships (37, 38, 39) must not be shot: a fifth one destroyed loses the stage. Allies that
    fly off the bottom (code 90) don't count."""
    CHAPTER = 6
    SPAWNS = {'small1': ('small', 4), 'small2': ('small', 22), 'small3': ('small', 21), 'laser1': ('laser', 5),
              'medium1': ('medium', 37), 'medium2': ('medium', 38), 'medium3': ('medium', 39)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inocent = 0   # inocentCounter

    def opening(self, stage):
        if stage == 1:
            self.create('small1')
            self.create('laser1')
        elif stage == 2:
            self.say_chain([('chap6_icarus1', 0.0, 0.0), ('chap6_icarus2', 0.5, 0.0)], lambda: self.create('medium1'))
        elif stage == 3:
            self.create('medium1')
            self.create('medium2')
        else:
            def go():
                self.create('small1')
                self.create('laser1')
                self.release_power_up(FAST_SHOT)
                self.release_power_up(SPEED)
            self.say('chap6_icarus3', 0.5, 0.5, go)

    def _random_ally(self):
        r = rand.arc4random() % 3
        return 'medium2' if r == 1 else 'medium1' if r == 0 else 'medium3'

    def destroy_enemy(self, code):
        st = self.stage_number
        if st == 3:
            if code == 37:
                self.inocent += 1
                if self._dec('medium_in') < 3 and self.medium < 20:
                    self.create('medium1')
            elif code in (38, 39):
                self.medium_in -= 1
                self.inocent += 1
                if self.medium_in < 2 and self.medium < 20:
                    self.create('medium2' if code == 38 else 'medium3')
            elif code == 90:
                old = self._dec('medium_in')
                if self.medium < 20 and old <= 1:
                    r = rand.arc4random() & 3
                    if r == 1:
                        self.create('medium2')
                        self.create('medium1')
                    elif r == 0:
                        self.create('medium1')
                        self.create('medium3')
                    else:
                        self.create('medium3')
                        self.create('medium2')
            self._check_allies()
            if self.medium >= 20 and self.medium_in == 0:
                self.default_victorious_animation()
        elif st == 2:
            if code == 37:
                self.inocent += 1
                if self._dec('medium_in') <= 1 and self.medium < 20:
                    self.create('medium2')
            elif code in (38, 39):
                self.medium_in -= 1
                self.inocent += 1
                if self.medium_in < 1 and self.medium < 20:
                    self.create('medium3' if code == 38 else 'medium1')
            elif code == 90:
                self.medium_in -= 1
                if self.medium < 20:
                    self.create(self._random_ally())
            self._check_allies()
            if self.medium >= 20 and self.medium_in == 0:
                self.default_victorious_animation()
        elif st == 1:
            if code == 5:
                if self._dec('laser_in') <= 1 and self.laser < 8:
                    if self.laser in (4, 1):
                        self.release_power_up(FAST_SHOT)
                    self.create('laser1')
            elif code == 4:
                if self._dec('small_in') <= 1 and (self.laser < 8 or self.laser_in > 0):
                    self.create('small1')
            if self.laser == 8 and self.small_in <= 0:
                self.default_victorious_animation()
        else:
            if code == 4:
                if self._dec('small_in') <= 1 and (self.laser < 3 or self.laser_in > 0):
                    self.create(self._random_ally())
            elif code == 5:
                if self._dec('laser_in') <= 1 and self.laser < 3:
                    if self.laser == 1:
                        self.release_power_up(SHIELD)
                    self.create('laser1')
            elif code in (37, 90):
                if code == 37:
                    self.inocent += 1
                if self._dec('medium_in') < 3 and self.medium < 20:
                    self.create('small1')
            elif code in (38, 39):
                self.medium_in -= 1
                self.inocent += 1
                if self.medium_in < 2 and self.medium < 20:
                    self.create('small1')
            self._check_allies()
            if self.laser >= 3 and self.small_in <= 0 and self.medium_in <= 0:
                self.end_lvl()

    def _check_allies(self):
        if self.inocent > 4:
            self.end_game()

    def end_lvl(self):
        self.end_lvl_speech('chap6_icarus4', 0.5, 0.5, self.default_victorious_animation)


class Chapter7Scene(ChapterScene):
    """Hope."""
    CHAPTER = 7
    SPAWNS = {'small1': ('small', 36), 'small2': ('small', 33), 'small3': ('small', 32), 'medium1': ('medium', 34),
              'medium2': ('medium', 44), 'medium3': ('medium', 35), 'laser1': ('laser', 3)}

    def opening(self, stage):
        if stage == 1:
            self.say_chain([('chap7_icarus1', 0.5, 0.0), ('chap7_icarus2', 0.5, 0.5)], lambda: self.create('small1'))
        elif stage == 2:
            self.say('chap7_icarus3', 0.5, 0.0, lambda: self.create('small2'))
        elif stage == 3:
            self.say('chap7_icarus4', 0.5, 0.0, lambda: self.create('laser1'))
        else:
            self.stage4_loop([('chap7_icarus5', 0.5, 0.0), ('chap7_icarus6', 0.5, 0.5)], lambda: self.boss_now(7))

    def destroy_enemy(self, code):
        st = self.stage_number
        if st == 3:
            if code == 3:
                if self._dec('laser_in') <= 1 and self.laser < 4:
                    if self.laser != 2:
                        self.create('laser1')
                    else:
                        self.create('small3')
                        self.create('medium3')
                        self.release_power_up(FAST_SHOT)
                        self.laser += 1
            elif code == 32:
                old = self._dec('small_in')
                if 0 <= self.small < 5:
                    if old < 2:
                        self.create('small3')
                elif self.small == 5:
                    if old < 2:
                        self.create('small3')
                        self.create('medium2')
                        self.release_power_up(FAST_SHOT)
                elif self.small > 5 and old < 2:
                    self.create('laser1')
            elif code == 35:
                if self._dec('medium_in') < 3 and self.medium < 2:
                    self.create('medium2')
            elif code == 44:
                if self._dec('medium_in') <= 1 and self.medium < 2:
                    self.create('medium3')
            if self.medium_in <= 0 and self.laser_in <= 0 and self.small_in <= 0 and self.laser >= 4:
                self.default_victorious_animation()
        elif st == 2:
            if code == 44:
                if self._dec('medium_in') <= 1 and self.medium == 2:
                    self.create('medium2')
                    self.create('small2')
                    self.release_power_up(SPEED)
            elif code == 35:
                if self._dec('medium_in') <= 1 and self.medium < 4:
                    if self.medium == 1:
                        self.create('small2')
                    elif self.small > 3:
                        self.create('medium3')
            elif code == 33:
                if self._dec('small_in') <= 1 and self.small < 6:
                    if self.small == 1:
                        self.create('medium3')
                    elif self.small in (3, 4):
                        self.create('medium2')
                    elif self.small == 5:
                        self.create('medium2')
                        self.create('medium3')
                        self.release_power_up(LIFE)
                    else:
                        self.create('small2')
            if self.medium_in <= 0 and self.small_in <= 0 and self.medium >= 4:
                self.default_victorious_animation()
        elif st == 1:
            if code == 34:
                if self._dec('medium_in') <= 1 and self.medium < 5:
                    # Deviation (docs/DEVIATIONS.md, "Chapter 7 stage 1 softlock is fixed"): the original only
                    # respawned the medium while life was above 4, which could leave the stage unwinnable.
                    if self.player.life > 4:
                        if self.medium == 4:
                            self.release_power_up(LIFE)
                    else:
                        self.release_power_up(LIFE)
                    self.create('medium1')
            elif code == 36:
                if self._dec('small_in') <= 1 and self.small < 8:
                    if self.small == 1:
                        self.create('medium1')
                        self.create('small1')
                        self.release_power_up(SHIELD)
                        self.release_power_up(FAST_SHOT)
                    else:
                        if self.small == 5:
                            self.release_power_up(FAST_SHOT)
                        self.create('small1')
            if self.small >= 8 and self.medium >= 4 and self.small_in <= 0 and self.medium_in <= 0:
                self.default_victorious_animation()
        else:
            self.end_lvl()

    def end_lvl(self):
        self.end_lvl_speech('chap7_icarus7', 0.5, 0.0, self.default_victorious_animation)


class Chapter8Scene(ChapterScene):
    """Revenge."""
    CHAPTER = 8
    SPAWNS = {'small1': ('small', 17), 'small2': ('small', 18), 'medium1': ('medium', 19), 'medium2': ('medium', 25),
              'laser1': ('laser', 27)}

    def opening(self, stage):
        if stage == 1:
            def go():
                self.create('small1')
                self.later(DELAYED_SPAWN, lambda: self.create('small2'))
            self.say('chap8_icarus1', 0.5, 0.5, go)
        elif stage == 2:
            self.create('small2')
            self.create('medium1')
        elif stage == 3:
            self.create('laser1')
            self.create('medium2')
        else:
            self.stage4_loop([('chap8_icarus2', 0.5, 0.5)], lambda: self.boss_now(8))

    def destroy_enemy(self, code):
        st = self.stage_number
        if st == 3:
            if code == 17:
                if self._dec('small_in') <= 1 and self.laser < 5:
                    self.create('laser1')
            elif code == 19:
                if self._dec('medium_in') <= 1 and self.medium < 7:
                    self.create('medium2')
            elif code == 25:
                if self._dec('medium_in') <= 1 and self.medium < 7:
                    self.create('medium1')
            elif code == 27:
                if self._dec('laser_in') <= 1:
                    if self.laser < 3:
                        if self.laser == 2:
                            self.release_power_up(FAST_SHOT)
                        self.create('small1')
                    elif self.laser < 6:
                        self.create('laser1')
            if self.laser >= 5 and self.small_in == 0 and self.medium_in == 0 and self.laser_in == 0:
                self.default_victorious_animation()
        elif st == 2:
            if code == 27:
                if self._dec('laser_in') <= 1:
                    if self.laser < 5:
                        if self.laser == 4:
                            self.release_power_up(FAST_SHOT)
                        self.create('small2')
                    elif self.laser < 6:
                        if self.medium > 5:
                            self.release_power_up(FAST_SHOT)
                        self.create('laser1')
            elif code == 19:
                if self._dec('medium_in') <= 1 and self.laser < 6:
                    if self.medium == 5:
                        self.release_power_up(SHIELD)
                    self.create('medium1')
            elif code == 18:
                if self._dec('small_in') < 3 and self.laser < 6:
                    self.create('laser1')
            if self.laser >= 6 and self.small_in == 0 and self.laser_in == 0 and self.medium_in == 0:
                self.default_victorious_animation()
        elif st == 1:
            if code == 19:
                if self._dec('medium_in') <= 1 and self.medium < 6:
                    if self.medium == 3:
                        self.release_power_up(FAST_SHOT)
                    self.create('small1')
            elif code == 18:
                if self._dec('small_in') < 3 and self.medium < 6:
                    self.create('small2')
            elif code == 17:
                if self._dec('small_in') < 3 and self.medium < 6:
                    self.create('medium1')
            if self.medium >= 6 and self.small_in <= 0 and self.medium_in <= 0:
                self.default_victorious_animation()
        else:
            self.end_lvl()

    def end_lvl(self):
        self.end_lvl_speech('chap8_icarus3', 0.5, 0.5, self.default_victorious_animation)


class Chapter9Scene(ChapterScene):
    """Pegasus."""
    CHAPTER = 9
    SPAWNS = {'small1': ('small', 12), 'small2': ('small', 14), 'medium1': ('medium', 13), 'medium2': ('medium', 16),
              'laser1': ('laser', 15)}

    def opening(self, stage):
        if stage == 1:
            self.say('chap9_icarus1', 0.5, 0.5, lambda: self.create('small1'))
        elif stage == 2:
            self.create('small2')
        elif stage == 3:
            self.create('medium2')
        else:
            self.say_chain([('chap9_icarus2', 0.5, 1.5), ('chap9_icarus3', 0.5, 0.0)], lambda: self.boss_now(9))

    def destroy_enemy(self, code):
        st = self.stage_number
        if st == 3:
            if code == 15:
                if self._dec('laser_in') <= 1 and self.laser < 7:
                    if self.laser in (1, 2):
                        self.release_power_up(SHIELD)
                        if self.laser == 2:
                            self.release_power_up(FAST_SHOT)
                    self.create('laser1')
            elif code == 16:
                if self._dec('medium_in') <= 1 and (self.laser < 7 or self.laser_in > 0):
                    if self.medium == 3:
                        self.create('laser1')
                    self.create('medium2')
            if self.laser >= 7 and self.medium_in <= 0:
                self.enter_ground()
        elif st == 2:
            if code == 15:
                if self._dec('laser_in') <= 1 and self.laser < 8:
                    if self.laser in (4, 1):
                        self.release_power_up(SHIELD)
                        if self.laser == 4:
                            self.release_power_up(SPEED)
                    self.create('laser1')
            elif code == 14:
                if self._dec('small_in') <= 1 and (self.laser < 8 or self.laser_in > 0):
                    if self.small == 1:
                        self.create('laser1')
                        self.release_power_up(SPEED)
                    self.create('small2')
            if self.laser >= 8 and self.small_in <= 0:
                self.default_victorious_animation()
        elif st == 1:
            if code == 13:
                if self._dec('medium_in') <= 1 and self.medium < 10:
                    if self.medium in (2, 6):
                        self.release_power_up(FAST_SHOT)
                    self.create('medium1')
            elif code == 12:
                if self._dec('small_in') <= 1 and (self.medium < 10 or self.medium_in > 0):
                    if self.small == 1:
                        self.create('medium1')
                        self.release_power_up(SHIELD)
                        self.release_power_up(SPEED)
                    self.create('small1')
            if self.medium >= 10 and self.small_in <= 0:
                self.default_victorious_animation()
        else:
            self.end_lvl()

    def enter_ground(self):
        """The descent into the planet: a black fade (visual) while the ship flies off as in a victory."""
        self.default_victorious_animation()

    def end_lvl(self):
        self.end_lvl_speech('chap9_icarus4', 0.5, 0.0, self.end_it_all, stop_controls=True)

    def end_it_all(self):
        """The last lines and the countdown, endingSound.mp3, then the credits and the mission complete menu."""
        p = self.player

        def two():
            self.services.voice.speak_then('2...', ICARUS_RATE, 0.0, 0.2, one)

        def one():
            self.services.voice.speak_then('1...', ICARUS_RATE, 0.0, 0.2, impact)

        def impact():
            self.services.effects.play('endingSound.mp3')
            self.run(A.sequence([A.wait(5.0), A.run_block(self.run_fast_credits)]))

        def brace():
            p.run(A.move_to(0.0, H + 20.0, 4.0))
            self.say('chap9_icarus6', 0.0, 0.2, two)
        self.say('chap9_icarus5', 0.0, 0.25, brace)

    def run_fast_credits(self):
        """The credits fade in over 7 seconds and scroll for 25, then after 2 more seconds the mission
        complete menu. The credits voice line starts after a 7 second delay."""
        self.services.voice.speak_queued(self.services.strings.get('credits_voice'), ICARUS_RATE, 7.0, 0.0)
        self.run(A.sequence([A.wait(7.0), A.wait(25.0), A.wait(2.0)]), completion=self.mission_complete)


CHAPTERS = {c.CHAPTER: c for c in (
    Chapter1Scene, Chapter2Scene, Chapter3Scene, Chapter4Scene, Chapter5Scene,
    Chapter6Scene, Chapter7Scene, Chapter8Scene, Chapter9Scene,
)}
