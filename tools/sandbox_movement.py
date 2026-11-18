"""Movement sandbox: steer the player ship by ear. This plays real sound: run it yourself.

Keys:
  Left and right arrows: steer (held keys stand in for tilting the device).
  L: speak your life.
  T: toggle talking movement ("Right", "Left", "Stopped", "End of Screen").
  E: toggle a stationary enemy engine at the top centre, to hear the pan shift as you move.
  Up and down arrows: change the tilt strength in steps of 0.05, announced.
  Escape: quit.

usage: python tools/sandbox_movement.py
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame

from nebula.audio.openal_backend import OpenALBackend
from nebula.engine.nodes import Node
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
    pygame.display.set_caption('Nebula movement sandbox')
    reader = ScreenReader()
    services = Services(OpenALBackend(), PrismRenderer(lang), reader, Strings(lang))
    keys = KeyboardTilt(float(settings.get('tilt', 0.3)))
    scene = BaseScene(services, keys)
    scene.talking_move = True
    engine = None
    reader.say('Movement sandbox. Arrows steer. L life. T talking movement. E enemy engine. '
               'Up and down change tilt, now %.2f. Escape quits.' % keys.tilt)

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
