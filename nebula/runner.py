"""The game window, fixed-step loop and key handling shared by the game and the developer tools.

Keys follow docs/DEVIATIONS.md: arrows steer (faster with Shift held), Space fires, Escape is swipe up, L speaks life, and in menus
the down and up arrows move (swipe right and left) and Enter activates (double tap). A scene with a
handle_key method gets Escape, Left and Right first (menu screens and the campaign selector use them).
"""
import time

import pygame

from .controller.pads import Pads, read_events
from .render.renderer import Renderer
from .render.textures import TextureStore

FRAME = 1 / 60
POINTS = (320, 568)    # the original's screen in points (iPhone 5)


class GameWindow:
    def __init__(self, services, tilt, title='Nebula', scale=1.5):
        """scale is pixels per point: the window is the original 320 by 568 point screen times scale."""
        self.services, self.tilt = services, tilt
        self.scene = None
        self.running = False
        self.extra_keys = {}       # key -> callable, for developer tools
        pygame.init()
        self.screen = pygame.display.set_mode((round(POINTS[0] * scale), round(POINTS[1] * scale)))
        pygame.display.set_caption(title)
        self.renderer = Renderer(TextureStore(), scale)
        self.scale = scale
        # game controllers (a port addition): buttons become keys, a motion pad steers, and it vibrates
        self.pads = Pads(pygame, say=services.screen_reader.say)
        tilt.motion = self.pads.tilt
        services.haptics.rumble = self.pads.rumble

    def set_scale(self, scale):
        """Resizes the window: the 320 by 568 point screen times scale."""
        if scale == self.scale:
            return
        self.scale = scale
        self.screen = pygame.display.set_mode((round(POINTS[0] * scale), round(POINTS[1] * scale)))
        self.renderer.scale = scale
        self.renderer._scaled.clear()

    def set_scene(self, scene):
        old = self.scene
        if old is not None and hasattr(old, 'stop_audio'):
            old.stop_audio()
        self.scene = scene
        self.tilt.left = self.tilt.right = False
        self.tilt.fast = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
        scene.did_move_to_view()

    def quit(self):
        self.running = False

    def handle(self, ev):
        s = self.scene
        down = ev.type == pygame.KEYDOWN
        voice = self.services.voice
        in_game_menu = getattr(s, 'in_menu', False) and hasattr(s, 'menu_items')
        if (down and ev.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER)
                and getattr(voice, 'awaiting_continue', False) and not in_game_menu):
            voice.continue_()       # "press Enter or Space to continue", in screen reader mode
            return
        if down and hasattr(s, 'handle_text_event') and s.handle_text_event(ev):
            return                  # a text box took the key
        named = {pygame.K_ESCAPE: 'escape', pygame.K_LEFT: 'left', pygame.K_RIGHT: 'right',
                 pygame.K_LCTRL: 'control', pygame.K_RCTRL: 'control', pygame.K_F1: 'f1'}.get(ev.key)
        if down and named and hasattr(s, 'handle_key') and s.handle_key(named):
            return
        if ev.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
            self.tilt.fast = down
            return
        if ev.key == pygame.K_LEFT:
            self.tilt.left = down
        elif ev.key == pygame.K_RIGHT:
            self.tilt.right = down
        if not down:
            return
        if ev.key in self.extra_keys:
            self.extra_keys[ev.key]()
        elif ev.key == pygame.K_SPACE:
            s.player_shoot()
        elif ev.key == pygame.K_ESCAPE:
            if s.in_menu:
                return
            s.swipe_up()
        elif ev.key == pygame.K_l:
            s.speak_life()
        elif ev.key == pygame.K_DOWN:
            s.menu_next()
        elif ev.key == pygame.K_UP:
            s.menu_previous()
        elif ev.key == pygame.K_HOME and hasattr(s, 'menu_first'):
            s.menu_first()
        elif ev.key == pygame.K_END and hasattr(s, 'menu_last'):
            s.menu_last()
        elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            s.menu_activate()

    def draw(self):
        """SpriteKit scenes are drawn from their nodes; other screens draw themselves if they can."""
        s = self.scene
        if s is None:
            return
        if hasattr(s, 'walk'):
            self.renderer.draw_scene(s, self.screen)
        elif hasattr(s, 'draw'):
            s.draw(self.screen, self.renderer)
        else:
            self.screen.fill((0, 0, 0))
        pygame.display.flip()

    def run(self):
        self.running = True
        last = time.perf_counter()
        acc = 0.0
        while self.running:
            for ev in read_events(pygame):
                if ev.type == pygame.QUIT:
                    self.running = False
                elif ev.type in (pygame.KEYDOWN, pygame.KEYUP):
                    self.handle(ev)
                elif ev.type == pygame.TEXTINPUT:
                    if hasattr(self.scene, 'handle_text_event'):
                        self.scene.handle_text_event(ev)
                else:
                    self.handle_pad(ev)
            now = time.perf_counter()
            acc += now - last
            last = now
            while acc >= FRAME and self.running:
                self.services.scheduler.update(FRAME)
                self.scene.step(FRAME)
                acc -= FRAME
            self.draw()
            time.sleep(0.002)
        if self.scene is not None and hasattr(self.scene, 'stop_audio'):
            self.scene.stop_audio()
        self.pads.close()
        self.services.audio.close()
        pygame.quit()

    PAD_KEYS = {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT, 'right': pygame.K_RIGHT,
                'enter': pygame.K_RETURN, 'space': pygame.K_SPACE, 'escape': pygame.K_ESCAPE, 'l': pygame.K_l,
                'home': pygame.K_HOME, 'end': pygame.K_END}

    def handle_pad(self, ev):
        """A controller event becomes the key events it stands for (nebula/controller/pads.py)."""
        if self.scene is None:
            return
        controls = self.pads.feed(ev, bool(getattr(self.scene, 'in_menu', False)))
        for name, down in controls or ():
            key = pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=self.PAD_KEYS[name], mod=0,
                                     unicode='')
            self.handle(key)
