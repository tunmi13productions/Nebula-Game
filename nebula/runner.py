"""The game window, fixed-step loop and key handling shared by the game and the developer tools.

Keys follow docs/DEVIATIONS.md: arrows steer, Space fires, Escape is swipe up, L speaks life, and in menus
the down and up arrows move (swipe right and left) and Enter activates (double tap). A scene with a
handle_key method gets Escape, Left and Right first (menu screens and the campaign selector use them).
"""
import time

import pygame

FRAME = 1 / 60


class GameWindow:
    def __init__(self, services, tilt, title='Nebula'):
        self.services, self.tilt = services, tilt
        self.scene = None
        self.running = False
        self.extra_keys = {}       # key -> callable, for developer tools
        pygame.init()
        pygame.display.set_mode((320, 240))
        pygame.display.set_caption(title)

    def set_scene(self, scene):
        old = self.scene
        if old is not None and hasattr(old, 'stop_audio'):
            old.stop_audio()
        self.scene = scene
        self.tilt.left = self.tilt.right = False
        scene.did_move_to_view()

    def quit(self):
        self.running = False

    def handle(self, ev):
        s = self.scene
        down = ev.type == pygame.KEYDOWN
        named = {pygame.K_ESCAPE: 'escape', pygame.K_LEFT: 'left', pygame.K_RIGHT: 'right'}.get(ev.key)
        if down and named and hasattr(s, 'handle_key') and s.handle_key(named):
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
        elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            s.menu_activate()

    def run(self):
        self.running = True
        last = time.perf_counter()
        acc = 0.0
        while self.running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                elif ev.type in (pygame.KEYDOWN, pygame.KEYUP):
                    self.handle(ev)
            now = time.perf_counter()
            acc += now - last
            last = now
            while acc >= FRAME and self.running:
                self.services.scheduler.update(FRAME)
                self.scene.step(FRAME)
                acc -= FRAME
            time.sleep(0.002)
        if self.scene is not None and hasattr(self.scene, 'stop_audio'):
            self.scene.stop_audio()
        self.services.audio.close()
        pygame.quit()
