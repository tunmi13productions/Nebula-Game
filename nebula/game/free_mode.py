"""FreeModeScene: endless play with two enemy pools, a boss every tenth special, timed power-ups and a saved
best score (see docs/MODES.md, Free mode)."""
from ..engine import actions as A
from .map_generator import MapGenerator
from .base_scene import BaseScene, RATE_STATUS
from .rand import between

BASE_POOL = [0, 2, 1, 22, 9, 10, 40, 42, 4, 6, 47, 28, 17, 26, 28, 48, 29, 30, 32, 36, 17, 18, 19]
SPECIAL_POOL = [7, 8, 11, 43, 20, 23, 31, 34, 33, 44, 35, 3, 19, 25, 13, 16, 15, 27]
BOSS_LIST = [1, 2, 3, 4, 5, 6, 9, 10]
COUNTDOWN = 3
FIRST_ENEMY_DELAY = 0.5
BASES_BEFORE_SPECIALS = 10
BOSS_EVERY = 10


class FreeModeScene(BaseScene):
    def __init__(self, services, tilt_source=None, on_menu=None, on_new_game=None):
        super().__init__(services, tilt_source)
        self.stage_number = 0
        self.services.globals.free_mode = True
        self.segundos = COUNTDOWN
        self.base_in_scene = self.special_in_scene = 0
        self.total_base = self.total_special = 0
        self.ini_base, self.fin_base = 0, 3
        self.ini_special, self.fin_special = 0, 1
        self.next_base_type = self.next_special_type = 0
        self.boss_code = 0
        self.on_menu = on_menu or (lambda: None)           # backMenuController
        self.on_new_game = on_new_game or (lambda: None)   # novoJogo
        self.map = MapGenerator(self, services)            # initFreemodeMapInScene:
        self.map.free_mode()

    # start

    def did_move_to_view(self):
        super().did_move_to_view()
        self.run(A.sequence([A.wait(1.0), A.repeat_forever(A.sequence([A.run_block(self._countdown), A.wait(1.0)]))]),
                 key='RegressiveCounter')

    def _countdown(self):
        voice, s = self.services.voice, self.services.strings
        if self.segundos > 0:
            voice.speak('%d' % self.segundos, RATE_STATUS)
        else:
            self.remove_action('RegressiveCounter')
            voice.speak(s.get('versus_Inicio'), RATE_STATUS)
            self.services.scheduler.after(FIRST_ENEMY_DELAY, self.create_first_enemy)
            self.time_between_power_ups = 60
            self.time_to_next_power_up = 60
            self.power_up_type1, self.power_up_type2 = 1, 4
        self.segundos -= 1

    # spawning

    def create_first_enemy(self):
        self.base_in_scene = self.special_in_scene = 0
        self.total_base = self.total_special = 0
        self.ini_base, self.fin_base = 0, 3
        self.ini_special, self.fin_special = 0, 1
        self.next_base_type = between(4, 8)
        self.next_special_type = between(8, 13)
        self.release_base_enemy()

    def release_base_enemy(self):
        """Only one base enemy at a time. From the call where 10 have already spawned, it also starts the
        specials if none has spawned yet. The count is checked before this call's spawn, as in the original."""
        specials_due = self.total_base >= BASES_BEFORE_SPECIALS
        if self.base_in_scene == 0:
            self.base_in_scene = 1
            self.total_base += 1
            self.create_enemy_with_type(BASE_POOL[between(self.ini_base, self.fin_base)])
        if specials_due and self.total_special == 0:
            self.release_special_enemy()

    def release_special_enemy(self):
        if self.special_in_scene != 0:
            return
        self.special_in_scene += 1
        self.total_special += 1
        if self.total_special % BOSS_EVERY == 0:
            self.boss_code += 1
            if self.boss_code == len(BOSS_LIST):
                self.boss_code = 1
            self.spawn_boss(BOSS_LIST[self.boss_code])
        else:
            self.create_enemy_with_type(SPECIAL_POOL[between(self.ini_special, self.fin_special)])

    def is_base_enemy(self, code):
        return code in BASE_POOL

    def destroy_enemy(self, code):
        if self.is_base_enemy(code):
            self.base_in_scene -= 1
            self.release_base_enemy()
            return
        self.special_in_scene -= 1
        if self.next_special_type < self.total_special and self.fin_special < len(SPECIAL_POOL) - 1:
            self.next_special_type = self.total_special + between(8, 13)
            if self.fin_special < len(SPECIAL_POOL) - 1:
                self.ini_special += 1
                self.fin_special += 1
        if self.next_base_type < self.total_base and self.fin_base < len(BASE_POOL) - 1:
            self.next_base_type = self.total_base + between(4, 8)
            if self.fin_base < len(BASE_POOL) - 1:
                self.ini_base += 1
                self.fin_base += 1
        self.release_special_enemy()

    # end

    def end_game(self):
        if not self.is_active:
            return
        self.allow_move = False
        self.services.aureal.stop_all()
        self.services.voice.stop()
        super().end_game()
        save = self.services.save
        if self.score_counter > save.integer('bestScore'):
            save.set_integer('bestScore', self.score_counter)
            save.synchronize()
        self.game_over_screen()

    def game_over_screen(self):
        """telaGameOver: "Game Over" with New game and Back to menu, announcing score and best score."""
        s = self.services.strings
        best = self.services.save.integer('bestScore')
        self.menu_title = s.get('game_over')
        self.menu_items = [(s.get('game_proximo'), self.on_new_game), (s.get('game_selecionar'), self.on_menu)]
        self.menu_selection = 1
        self.in_menu = True
        self.end_screen = True
        summary = s.format('game_over_freemode', self.score_counter, best)
        self.services.voice.speak('%s , %s' % (summary, self.menu_items[0][0]), RATE_STATUS)

    def pause_restart(self):
        self.on_new_game()

    def pause_leave(self):
        self.on_menu()

    def stop_audio(self):
        self.map.stop()
        self.services.aureal.stop_all()
        self.services.voice.stop()
        self._accel_timer.invalidate()
        self.remove_all_children()
        self.remove_all_actions()
