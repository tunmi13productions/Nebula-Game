"""Listening check for the game voice. This plays real sound: run it yourself, not from tests.

It speaks two I.C.A.R.U.S. lines through the OneCore game voice at the original rate, waits for the
completion the way the chapter scripts do, then says through your screen reader that the demo is over.

usage: python tools/demo_speech.py
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nebula.audio.openal_backend import OpenALBackend
from nebula.engine.scheduler import Scheduler
from nebula.speech.speech import GameVoice, PrismRenderer, ScreenReader


def main():
    audio, clock = OpenALBackend(), Scheduler()
    voice = GameVoice(audio, clock, PrismRenderer('en'))
    reader = ScreenReader()
    done = []
    line1 = "You have less than 5% of fuel. I strongly recommend you to go to the closest refuelling base. Warning: Mercenaries spaceships approaching"
    line2 = "There are many fuel tanks on space, avoid them as much as possible. Colliding with them may be fatal."
    voice.speak_then(line1, 0.55, 1.0, 0.0, lambda: voice.speak_then(line2, 0.55, 1.0, 0.0, lambda: done.append(1)))
    last = time.perf_counter()
    while not done:
        now = time.perf_counter()
        clock.update(now - last)
        last = now
        time.sleep(0.01)
    reader.say('Game voice demo finished.')
    time.sleep(1.5)
    audio.close()


if __name__ == '__main__':
    main()
