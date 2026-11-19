"""VersusScene: two players over the relay server, as the original played over Game Center (docs/NOTES.md,
"Versus mode"; DEVIATIONS.md, "Multiplayer through a relay server").

Both machines run this same scene and trust each other; the relay only carries messages. Messages are the
original's C structs, little-endian, the first int their type:
    3 specs (16 bytes)  device, lifePoints, shieldPoints          sent when the match starts
    4 (4 bytes)         specs received                             starts the countdown
    0 move (20 bytes)   x (float), own life, opponent's life and shield as the sender sees them, every 0.05 s
    1 shot (4 bytes)    the opponent fired
    6 (4 bytes)         round over (teste)

The scene opens in the lobby (lobbyMusic, the createBG panel) while the relay pairs the players, then runs
matchStarted. A shot that hits on the shooter's screen damages the opponent there; the damage reaches the
opponent through the move messages, whose life and shield fields each side applies when they are lower. A
shot hitting the player only bursts and plays player_hit.caf. When a life reaches 0, the round ends after a
second with the winner's name and versus_Vitoria (or versus_Empate), and restarts after 5 more seconds.
"""
import struct

from ..audio.players import LoopingMusic
from ..audio.volumes import VOLUMES
from ..engine import actions as A
from ..engine.nodes import Node
from ..engine.physics import Body, Circle, attach
from . import looks
from .base_scene import (BaseScene, ENEMY_BURST_FRAMES, H, POSITION_FACTOR_IPHONE, RATE_STATUS, SHOT_BURST_FRAMES,
                         W)
from .hud import EnemyBar, PlayerBars
from .map_generator import MapGenerator
from .rand import arc4random
from .ship import (CAT_ENEMY, CAT_ENEMY_SHOT, CAT_OBSTACLE, CAT_PLAYER, CAT_PLAYER_SHOT, Shot, SpaceShip,
                   burst_and_remove, player_hitbox)

MOVE, SHOT, SPECS, SPECS_RECEIVED, ROUND_OVER = 0, 1, 3, 4, 6
DEVICE_IPHONE = 1                 # device: the port is always the iPhone layout
IPAD_SCALE = 2.4                  # DAT_00080ef0, x between iPhone and iPad widths
SEND_INTERVAL = 0.05              # sendMove: (DAT_00080220)
COUNT_INTERVAL = 1.0
END_DELAY = 1.0
RESTART_DELAY = 5.0
MAX_WAITING_TIME = 5.0
SHOT_FRAME = 0.04                 # DAT_00082010 / DAT_00080ef8
SHOT_FLIGHT = 1.0
COUNT_START = 4                   # counter: speaks 3, 2, 1, then versus_Inicio
LOBBY_MUSIC = ('Lino Rise - Channel Intro Pompeii', 'mp3')   # LinoRise_ChannelIntroPompeii.mp3


def enemy_stats(life_points, shield_points):
    """setEnemyLife:andShield: from the opponent's Hangar upgrades."""
    life = 30 if life_points >= 5 else life_points * 5 + 5
    return life, min(shield_points, 5)


class VersusScene(BaseScene):
    def __init__(self, services, tilt_source, net, on_menu):
        """net: a connected RelayClient, already paired or waiting; on_menu: back to the menus."""
        super().__init__(services, tilt_source)
        self.net, self.on_menu = net, on_menu
        self.started = False             # gameStarter
        self.round_over = False
        self.ended = False               # endGame
        self.waiting_start = False
        self.waiting_response = False
        self.counter = COUNT_START
        self.count_timer = None
        self.end_timer = None
        self.restart_timer = None
        self.watchdog = None
        self.allow_move = self.allow_shoot = False
        self.map = MapGenerator(self, services)
        self.map.versus()
        self.map.suspend_foreground()
        self.label = Node(name='label', position=(W * 0.5, H * 0.5))
        self.label.text, self.label.font_size, self.label.font_name = '3', 60, 'Futura'
        self.label.font_color, self.label.z = (1.0, 1.0, 1.0), 11
        self.add_child(self.label)
        self._make_enemy(5, 0)
        self.send_timer = services.scheduler.every(SEND_INTERVAL, lambda t: self.send_move())
        self.lobby = self._lobby_panel()
        self.lobby_music = None
        path = services.sound_path(*LOBBY_MUSIC)
        if path is not None:             # at half volume, looping
            self.lobby_music = LoopingMusic(services.audio, path)
            self.lobby_music.play()
            services.audio.set_volume(self.lobby_music.handle, 0.5 * VOLUMES.music)
        net.on_matched = lambda name: self.match_started()
        net.on_data = self.receive
        net.on_opponent_left = self.match_ended
        net.on_error = lambda reason: self.match_ended()

    # the lobby and the ships

    def _lobby_panel(self):
        """createBG: black over everything, with the starfield, a planet and SpaceshipVersus.png."""
        panel = Node(name='multiplayer_BG', size=(W, H), position=(W * 0.5, H * 0.5))
        panel.color, panel.z = (0.0, 0.0, 0.0, 1.0), 90
        for texture, size in (('starfieldBG', (H, H)), ('planet%d' % (arc4random() % 6), (640.0, 640.0)),
                              ('SpaceshipVersus', (319.93, H))):
            n = Node(name='lobbyPicture', size=size, position=(0.0, 0.0))
            n.texture = texture
            panel.add_child(n)
        self.add_child(panel)
        return panel

    def _make_enemy(self, life, shield):
        """initEnemyPlayerInParentView: Enemy_00, the player's size and octagon, scale 1.5, at the top."""
        old = getattr(self, 'enemy', None)
        if old is not None:
            self.services.aureal.stop('enemyShipSound')
            old.remove_from_parent()
        e = SpaceShip(200, life, shield, self)
        w = W / 4.5
        e.ship_size = e.size = (w, w)
        e.add_sprite('Enemy_00')
        attach(e, Body(player_hitbox(w), category=CAT_ENEMY, contact=CAT_PLAYER_SHOT | CAT_OBSTACLE,
                       collision=CAT_OBSTACLE))
        e.scale = 1.5
        e.position = (W * 0.5, H - w)
        e.z = 5
        e.life_bar = EnemyBar(e)
        self.add_child(e)
        self.enemy = e
        aureal = self.services.aureal
        aureal.add_sound('SpaceShipSound', 'caf', 'enemyShipSound')
        aureal.link('enemyShipSound', e)
        aureal.play_forever('enemyShipSound', e.position)

    def _remake_player(self):
        """createPlayerShip, on restart: a new ship and bars."""
        if self.player.parent is not None:
            self.player.remove_from_parent()
        for n in self.player_bars.nodes:
            n.remove_from_parent()
        self.player = SpaceShip.player(self, self.services.globals)
        w, h = self.player.ship_size
        self.player.position = (W * 0.5, h + (H / 3) * POSITION_FACTOR_IPHONE)
        self.player.z = 5
        self.add_child(self.player)
        self.player_bars = PlayerBars(self, self.player)
        self.services.aureal.listener = self.player.position

    # the match

    def _send(self, fmt, *values):
        if not self.net.send(struct.pack(fmt, *values)):
            self.match_ended()
            return False
        return True

    def match_started(self):
        """matchStarted: the nebulas begin, the lobby goes, the specs are sent, and the 5 second watchdog."""
        self.map.begin_versus_nebulas()
        if self.lobby is not None:
            self.lobby.remove_from_parent()
            self.lobby = None
        if self.lobby_music is not None:
            self.lobby_music.stop()
        g = self.services.globals
        if not self._send('<iiii', SPECS, DEVICE_IPHONE, g.life_points, g.shield_points):
            return
        self._start_watchdog()

    def _start_watchdog(self):
        if self.watchdog is not None:
            self.watchdog.invalidate()
        self.watchdog = self.services.scheduler.after(MAX_WAITING_TIME, self.search_canceled)

    def search_canceled(self):
        """No answer in time: the match ends and the game returns to the menu."""
        self.back_to_menu()

    def match_ended(self):
        """The opponent left, or a message couldn't be sent: back to the menu."""
        if not getattr(self, 'leaving', False):
            self.back_to_menu()

    def send_move(self):
        if not self.started or self.game_paused:
            return
        x = self.player.position[0]
        self._send('<ifiii', MOVE, x, self.player.life, self.enemy.life, self.enemy.shield)

    def receive(self, data):
        """match:didReceiveData:fromPlayer:"""
        if self.watchdog is not None:
            self.watchdog.invalidate()
            self.watchdog = None
        if len(data) < 4:
            return
        kind = struct.unpack_from('<i', data)[0]
        if kind == MOVE and len(data) >= 20:
            _, x, life, my_life, my_shield = struct.unpack_from('<ifiii', data)
            self.enemy.position = (x, self.enemy.position[1])
            if self.started:
                if life < self.enemy.life:
                    self.enemy.inflict_damage(self.enemy.life - life)
                if my_life < self.player.life:
                    self.player.inflict_damage(self.player.life - my_life)
                if my_shield < self.player.shield:
                    self.player.inflict_damage(1)
        elif kind == SHOT:
            self._enemy_shot()
        elif kind == SPECS and len(data) >= 16:
            _, _device, life_points, shield_points = struct.unpack_from('<iiii', data)
            life, shield = enemy_stats(life_points, shield_points)
            self._make_enemy(life, shield)
            if not self._send('<i', SPECS_RECEIVED):
                return
            self._start_watchdog()
        elif kind == SPECS_RECEIVED:
            if self.count_timer is not None:
                self.count_timer.invalidate()
            self.count_timer = self.services.scheduler.every(COUNT_INTERVAL, lambda t: self.regressive_count())
        elif kind == ROUND_OVER:
            if not self.waiting_start:
                self._end_round()
        if self.enemy.life < 1 or self.player.life < 1:
            self._end_round()

    def _end_round(self):
        """endMultiplayerGame: moving and shooting stop, and the end screen comes once a round. Moves keep
        flowing, so the other side also learns the round is over."""
        if self.round_over or self.waiting_start:
            return
        self.round_over = True
        self.allow_shoot = self.allow_move = False
        self.end_timer = self.services.scheduler.after(END_DELAY, self.screen_before_restart)

    def regressive_count(self):
        """regressiveCount: 3, 2, 1, then versus_Inicio and the round."""
        if self.watchdog is not None:
            self.watchdog.invalidate()
            self.watchdog = None
        self.counter -= 1
        voice, s = self.services.voice, self.services.strings
        if self.counter <= 0:
            if self.count_timer is not None:
                self.count_timer.invalidate()
                self.count_timer = None
            voice.speak(s.get('versus_Inicio'), RATE_STATUS)
            self.can_shoot = True
            self.allow_move = self.allow_shoot = True
            self.started = True
            self.label.remove_from_parent()
            self.map.resume_foreground()
            return
        voice.speak('%d' % self.counter, RATE_STATUS)
        self.label.text = '%d' % self.counter

    # shooting and hits

    def player_shoot(self):
        """playerShoot: shot.png with the first frames, half the ship's size, from the ship's nose to the top
        in a second; the opponent is told."""
        if self.in_menu or not self.can_shoot or not self.allow_shoot or not self.started:
            return None
        p = self.player
        w, h = p.ship_size
        shot = Shot(p, (w * 0.5, h * 0.5))
        shot.texture = 'shot'
        shot.position = (p.position[0], p.position[1] + h * 1.5 * 0.5)
        attach(shot, Body(Circle(5.0), category=CAT_PLAYER_SHOT, contact=CAT_ENEMY | CAT_OBSTACLE,
                          collision=CAT_PLAYER_SHOT | CAT_ENEMY_SHOT))
        shot.z = 5
        self.add_child(shot)
        shot.run(A.animate_with_textures(looks.ARRAY_POWER_1, SHOT_FRAME))
        shot.run(A.sequence([A.move_to_y(H + 20.0, SHOT_FLIGHT), A.remove_from_parent()]))
        self.can_shoot = False
        self._send('<i', SHOT)
        p.shot_sound(None)
        return shot

    def _enemy_shot(self):
        """Message 1: the opponent's bullet, falling from under its ship."""
        e = self.enemy
        w, h = e.ship_size
        shot = Shot(e, (w * 0.5, h * 0.5))
        shot.texture = looks.ARRAY_POWER_2[0]
        shot.position = (e.position[0], e.position[1] - h * 1.5 * 0.5)
        attach(shot, Body(Circle(2.0), category=CAT_ENEMY_SHOT, contact=CAT_PLAYER | CAT_OBSTACLE))
        shot.z = 5
        self.add_child(shot)
        shot.run(A.animate_with_textures(looks.ARRAY_POWER_2, SHOT_FRAME))
        shot.run(A.sequence([A.move_to_y(-20.0, SHOT_FLIGHT), A.remove_from_parent()]))
        e.shot_sound(shot)

    def did_begin_contact(self, a, b):
        """didBeginContact: a shot hitting the opponent damages it by the player's shot power; a shot
        hitting the player only bursts (its damage arrives in the opponent's moves); shots cancel out."""
        cats = {a.category: a.node, b.category: b.node}
        fx = self.services.effects
        if CAT_ENEMY in cats and CAT_PLAYER_SHOT in cats:
            burst_and_remove(cats[CAT_PLAYER_SHOT], ENEMY_BURST_FRAMES, looks.ARRAY_POWER_3)
            fx.play('enemy_hit.caf')
            if self.started:
                self.enemy.inflict_damage(self.services.globals.get_shot())
        elif CAT_PLAYER_SHOT in cats and CAT_ENEMY_SHOT in cats:
            burst_and_remove(cats[CAT_ENEMY_SHOT], SHOT_BURST_FRAMES, looks.ARRAY_POWER_2)
            burst_and_remove(cats[CAT_PLAYER_SHOT], ENEMY_BURST_FRAMES, looks.ARRAY_POWER_3)
        elif CAT_ENEMY_SHOT in cats and CAT_PLAYER in cats:
            burst_and_remove(cats[CAT_ENEMY_SHOT], SHOT_BURST_FRAMES, looks.ARRAY_POWER_2)
            fx.play('player_hit.caf')

    # the end of a round

    def screen_before_restart(self):
        """The winner (or draw) box with Back to menu, spoken as "%@, %@", then a restart in 5 seconds."""
        self.end_timer = None
        if self.ended:
            return
        s = self.services.strings
        me, them = self.player.life < 1, self.enemy.life < 1
        if me and them:
            text, box = s.get('versus_Empate'), 'boxMultiplayerEmpate'
        else:
            winner = (self.net.opponent or '') if me else (self.net.name or '')
            text, box = ('%s %s' % (winner, s.get('versus_Vitoria'))).strip(), 'boxFinalMultiplayer'
        overlay = Node(name='endBox', size=(W, H), position=(W * 0.5, H * 0.5))
        overlay.color, overlay.z = (0.0, 0.0, 0.0, 0.6), 89
        picture = Node(name='box', size=(266.667, 320.0), position=(0.0, 0.0))
        picture.texture, picture.z = box + ('' if s.language == 'pt' else '_en'), 1
        overlay.add_child(picture)
        label = Node(name='label', position=(0.0, -20.0))
        label.text, label.font_size, label.font_name = text, 22, 'Futura'
        label.font_color, label.z = (1.0, 1.0, 1.0), 2
        overlay.add_child(label)
        self.add_child(overlay)
        self.open_menu(text, [(s.get('game_selecionar'), self.back_to_menu)], overlay=overlay)
        self.restart_timer = self.services.scheduler.after(RESTART_DELAY, self.restart_game)

    def restart_game(self):
        """restartGame: both ships rebuilt, the countdown label back, and the match starts again."""
        self.restart_timer = None
        if self.ended:
            return
        if self.in_menu:
            self.in_menu = False
            overlay = getattr(self, 'menu_overlay', None)
            if overlay is not None:
                overlay.remove_from_parent()
                self.menu_overlay = None
        self.waiting_start = self.waiting_response = False
        self.started = self.round_over = False
        self.counter = COUNT_START
        self.label.text = '3'
        if self.label.parent is None:
            self.add_child(self.label)
        self._remake_player()
        self._make_enemy(5, 0)
        self.allow_move = self.allow_shoot = False
        self.map.suspend_foreground()
        self.match_started()

    def back_to_menu(self):
        """backToMenu: the match ends and the menus return."""
        if getattr(self, 'leaving', False):
            return
        self.leaving = self.ended = True
        self.stop_audio()
        self.net.leave()
        self.net.close()
        self.on_menu()

    # the scene's lifetime

    def step(self, dt):
        self.net.poll()
        super().step(dt)

    invite_code = None
    code_lines = None      # (what C says, what Shift C says), each given the code: set by the App

    def handle_raw_key(self, event):
        """While hosting: C reads the invite code again, Shift C copies it to the clipboard (a port
        addition)."""
        import pygame
        if event.key != pygame.K_c or not self.invite_code or self.code_lines is None:
            return False
        again, copied = self.code_lines
        say = self.services.screen_reader.say
        if getattr(event, 'mod', 0) & pygame.KMOD_SHIFT:
            from ..menus.textbox import _clipboard_set
            _clipboard_set(self.invite_code)
            say(copied(self.invite_code))
        else:
            say(again(self.invite_code))
        return True

    def swipe_up(self):
        """No pause in versus mode."""

    def handle_key(self, key):
        if key == 'escape' and not self.started and not self.in_menu:
            self.back_to_menu()       # searchCanceled: leaving the lobby or the countdown
            return True
        return super().handle_key(key)

    def stop_audio(self):
        for t in (self.send_timer, self.count_timer, self.end_timer, self.restart_timer, self.watchdog):
            if t is not None:
                t.invalidate()
        self.map.stop()
        if self.lobby_music is not None:
            self.lobby_music.stop()
        self.services.aureal.stop_all()       # stopAllSounds
