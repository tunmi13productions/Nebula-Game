"""Listening check for the Aureal port. This plays real sound: run it yourself, not from tests.

An enemy engine loop moves around the listener (the player ship near the bottom of the screen) through
three paths, first with the balance pan law and then with the constant-power law. Each part is announced
through the screen reader. Press Ctrl+C to stop early.

usage: python tools/demo_aureal.py
"""
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import prism

from nebula.audio.aureal import Aureal
from nebula.audio.openal_backend import BALANCE, CONSTANT_POWER, OpenALBackend
from nebula.engine import actions as A
from nebula.engine.nodes import Node, Scene
from nebula.engine.scheduler import Scheduler

BUNDLE = os.path.join(ROOT, 'decompiled', 'ipa', 'Payload', 'BEPiDGame.app')
W, H = 320.0, 568.0
LISTENER = (160.0, 100.0)


def main():
    speech = prism.Context().acquire_best()
    audio = OpenALBackend()
    clock = Scheduler()
    scene = Scene(W, H)
    aureal = Aureal(audio, clock, lambda name, ext: os.path.join(BUNDLE, '%s.%s' % (name, ext)))
    aureal.configure(H * 1.25, LISTENER, scene, max_x=W)

    enemy = Node(position=(0.0, H * 0.8))
    scene.add_child(enemy)
    aureal.add_sound('Ship_2', 'mp3', 'engine')
    aureal.link('engine', enemy)
    aureal.play_forever('engine', enemy.position)

    def say(text):
        speech.speak(text, True)

    def circle(seconds):
        steps = 120
        moves = []
        for i in range(1, steps + 1):
            a = math.pi / 2 - 2 * math.pi * i / steps
            moves.append(A.move_to(LISTENER[0] + 150 * math.cos(a), LISTENER[1] + 150 * math.sin(a), seconds / steps))
        return A.sequence(moves)

    def part(law, label):
        return [
            A.run_block(lambda: setattr(audio, 'pan_law', law)),
            A.run_block(lambda: say(label + '. Sweeping left to right, in front of you.')),
            A.move_to(0.0, H * 0.8, 0.0), A.wait(3.0),
            A.move_to(W, H * 0.8, 6.0), A.move_to(0.0, H * 0.8, 6.0),
            A.run_block(lambda: say('From far in front, to behind you, centred.')),
            A.move_to(160.0, H, 0.0), A.wait(3.0),
            A.move_to(160.0, -60.0, 8.0),
            A.run_block(lambda: say('Circling around you, starting in front, going right.')),
            A.move_to(160.0, LISTENER[1] + 150, 1.0), A.wait(2.0),
            circle(10.0), circle(10.0),
        ]

    done = []
    enemy.run(A.sequence(part(BALANCE, 'Pan law one, balance') + part(CONSTANT_POWER, 'Pan law two, constant power') +
                         [A.run_block(lambda: say('End of demo.')), A.wait(2.0), A.run_block(lambda: done.append(1))]))

    dt = 1 / 60
    last = time.perf_counter()
    acc = 0.0
    try:
        while not done:
            now = time.perf_counter()
            acc += now - last
            last = now
            while acc >= dt:
                clock.update(dt)
                scene.step(dt)
                acc -= dt
            time.sleep(0.002)
    except KeyboardInterrupt:
        pass
    aureal.stop_all()
    audio.close()


if __name__ == '__main__':
    main()
