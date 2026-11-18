"""Play the tutorial. This plays real sound: run it yourself.

Starts at the given section (1 Movement, 2 Enemies, 3 Attack, 4 Battle, 5 Basic, 6 Special; default 1).
Keys: arrows steer, Space fires, L speaks your life, Escape ends the section (swipe up in the original).
In the Tutorial Completed menu: down and up arrows move, Enter activates. "Next tutorial" starts the next
section. "Select tutorial" quits for now, because the selection screen comes with the menus step.

usage: python tools/play_tutorial.py [section]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nebula.audio.openal_backend import OpenALBackend
from nebula.game.services import Services
from nebula.game.tutorial import TutorialScene
from nebula.input import KeyboardTilt
from nebula.runner import GameWindow
from nebula.settings import load_settings
from nebula.speech.speech import PrismRenderer, ScreenReader
from nebula.strings import Strings, choose_language

NAMES = {1: 'tut_movimento', 2: 'tut_inimigo', 3: 'tut_ataque', 4: 'tut_batalha', 5: 'tut_basico', 6: 'tut_especial'}


def main():
    section = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    settings = load_settings()
    lang = choose_language(settings)
    reader = ScreenReader()
    services = Services(OpenALBackend(), PrismRenderer(lang), reader, Strings(lang))
    tilt = KeyboardTilt(float(settings.get('tilt', 0.3)))
    window = GameWindow(services, tilt, 'Nebula tutorial')

    def start(n):
        reader.say('Tutorial %d, %s' % (n, services.strings.get(NAMES[n]).capitalize()))
        window.set_scene(TutorialScene(services, tilt, n, on_select=window.quit, on_next=lambda: start(n + 1)))

    start(section)
    window.run()


if __name__ == '__main__':
    main()
