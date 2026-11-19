"""Checks a motion-sensing controller's roll direction, silently: python tools/pad_probe.py

Prints instructions, then reads the pad's tilt (as the game would see it) while you hold it level, rolled
right and rolled left, and says whether right reads as right. No sound is played.
"""
import os
import sys
import time

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from nebula.controller.pads import Pads, read_events  # noqa: E402


def wait(seconds):
    end = time.time() + seconds
    while time.time() < end:
        read_events(pygame)
        time.sleep(0.02)


def average(pads, seconds):
    values = []
    end = time.time() + seconds
    while time.time() < end:
        read_events(pygame)
        v = pads.tilt()
        if v is not None:
            values.append(v)
        time.sleep(0.05)
    return sum(values) / len(values) if values else None


def main():
    pygame.init()
    pads = Pads(pygame, say=print)
    wait(0.5)
    if not pads.names:
        print('No controller found.')
        return
    print('Controller:', pads.names[0])
    if not pads.can_tilt():
        print('This controller has no motion sensor.')
        return
    steps = (('level', 'Hold the controller level, as you normally would.'),
             ('right', 'Now roll it to the right, right hand down, and hold it there.'),
             ('left', 'Now roll it to the left, left hand down, and hold it there.'))
    results = {}
    for name, text in steps:
        print(text)
        print('Reading in 3 seconds.')
        wait(3.0)
        results[name] = average(pads, 1.5)
        print('Read %s: %.2f' % (name, results[name] if results[name] is not None else float('nan')))
    pads.close()
    right, left = results['right'], results['left']
    if right is None or left is None:
        print('The sensor gave no readings.')
    elif right > 0.1 and left < -0.1:
        print('Correct: rolling right steers right.')
    elif right < -0.1 and left > 0.1:
        print('Reversed: rolling right would steer left. Tell Claude.')
    else:
        print('Unclear: the readings were too small. Try rolling further.')


if __name__ == '__main__':
    main()
