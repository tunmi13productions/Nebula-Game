"""Sandbox: steer, dodge and shoot by ear. This plays real sound: run it yourself.

Keys:
  Left and right arrows: steer (held keys stand in for tilting the device).
  Space: fire.
  F: spawn a fighter. It enters from the top, wanders and shoots.
  G: spawn a laser ship. It parks near a side and fires its laser: charge, firing sound, then the beam.
  B: spawn the next boss (1 to 10 in turn). Bosses are heard through their bullets and lasers.
  P: drop a random power-up (life, shield, speed or fast shot). Follow its radar beep to collect it.
  R: spawn a rock, A: spawn an ally. Both fall past you. Allies are worth minus 100 points if destroyed.
  S: speak the score.
  L: speak your life.
  T: toggle talking movement ("Right", "Left", "Stopped", "End of Screen").
  E: toggle a stationary enemy engine at the top centre, to hear the pan shift as you move.
  Up and down arrows: change the tilt strength in steps of 0.05, announced.
  Escape: quit.

usage: python tools/sandbox.py
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame

from nebula.audio.openal_backend import OpenALBackend
from nebula.engine.nodes import Node
import random

from nebula.game.base_scene import BaseScene, H
from nebula.game.services import Services
from nebula.input import KeyboardTilt
from nebula.settings import load_settings
from nebula.speech.speech import PrismRenderer, ScreenReader
from nebula.strings import Strings, choose_language

FRAME = 1 / 60


def main():
    settings = load_settings()
    lang = choose_language(settings)
    pygame.init()
    pygame.display.set_mode((320, 240))
    pygame.display.set_caption('Nebula sandbox')
    reader = ScreenReader()
    services = Services(OpenALBackend(), PrismRenderer(lang), reader, Strings(lang))
    keys = KeyboardTilt(float(settings.get('tilt', 0.3)))

    class Sandbox(BaseScene):
        def destroy_enemy(self, code):
            reader.say('Drifter left the screen' if code == 90 else 'Ship %d destroyed' % code)

        def end_game(self):
            reader.say('You were destroyed. Life restored.')
            self.player.life = self.player.max_life
            self.player.remove_action('alarme')
            self.allow_move = True

    scene = Sandbox(services, keys)
    scene.did_move_to_view()
    scene.talking_move = True
    engine = None
    reader.say('Sandbox. Arrows steer, Space fires. F fighter, G laser ship, R rock, A ally, B boss, P power-up. L life, S score, '
               'T talking movement, E enemy engine, up and down change tilt, now %.2f. Escape quits.' % keys.tilt)

    groups = {pygame.K_f: ('Fighter', [0, 1, 2, 9, 10, 11]), pygame.K_g: ('Laser ship', [3, 7, 8]),
              pygame.K_r: ('Rock', [47, 48, 49, 50]), pygame.K_a: ('Ally', [37, 38, 39])}

    boss_turn = [0]

    def spawn(key):
        label, codes = groups[key]
        scene.create_enemy_with_type(random.choice(codes))
        reader.say(label + ' incoming')

    last = time.perf_counter()
    acc = 0.0
    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type in (pygame.KEYDOWN, pygame.KEYUP):
                down = ev.type == pygame.KEYDOWN
                if ev.key == pygame.K_LEFT:
                    keys.left = down
                elif ev.key == pygame.K_RIGHT:
                    keys.right = down
                elif down and ev.key == pygame.K_ESCAPE:
                    running = False
                elif down and ev.key == pygame.K_SPACE:
                    scene.player_shoot()
                elif down and ev.key in groups:
                    spawn(ev.key)
                elif down and ev.key == pygame.K_b:
                    boss_turn[0] = boss_turn[0] % 10 + 1
                    scene.spawn_boss(boss_turn[0])
                    reader.say('Boss %d incoming' % boss_turn[0])
                elif down and ev.key == pygame.K_p:
                    scene.release_power_up(random.randint(1, 4))
                    reader.say('Power-up dropped')
                elif down and ev.key == pygame.K_s:
                    reader.say('Score %d' % scene.score_counter)
                elif down and ev.key == pygame.K_l:
                    scene.speak_life()
                elif down and ev.key == pygame.K_t:
                    scene.talking_move = not scene.talking_move
                    reader.say('Talking movement %s' % ('on' if scene.talking_move else 'off'))
                elif down and ev.key == pygame.K_e:
                    if engine is None:
                        engine = Node(position=(160.0, H * 0.8))
                        scene.add_child(engine)
                        key = services.aureal.next_key()
                        services.aureal.sound_id += 1
                        services.aureal.add_sound('Ship_2', 'mp3', key)
                        services.aureal.link(key, engine)
                        services.aureal.play_forever(key, engine.position)
                        reader.say('Enemy engine on')
                    else:
                        engine.remove_from_parent()
                        engine = None
                        reader.say('Enemy engine off')
                elif down and ev.key in (pygame.K_UP, pygame.K_DOWN):
                    step = 0.05 if ev.key == pygame.K_UP else -0.05
                    keys.tilt = round(min(1.0, max(0.1, keys.tilt + step)), 2)
                    reader.say('Tilt %.2f' % keys.tilt)
        now = time.perf_counter()
        acc += now - last
        last = now
        while acc >= FRAME:
            services.scheduler.update(FRAME)
            scene.step(FRAME)
            acc -= FRAME
        time.sleep(0.002)
    services.aureal.stop_all()
    services.audio.close()
    pygame.quit()


if __name__ == '__main__':
    main()
