r"""Play the parts of the game that are built so far. This plays real sound: run it yourself.

usage:
  python tools/play.py tutorial [section]   sections: 1 Movement, 2 Enemies, 3 Attack, 4 Battle, 5 Basic, 6 Special
  python tools/play.py free                 free mode

Keys: arrows steer, Space fires, L speaks your life, Escape is swipe up (it ends a tutorial section).
In menus: down and up arrows move, Enter activates. Menu items that lead to screens not built yet quit.
The free mode best score is saved in %APPDATA%\Nebula\save.json.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nebula.audio.openal_backend import OpenALBackend
from nebula.game.free_mode import FreeModeScene
from nebula.game.services import Services
from nebula.game.tutorial import TutorialScene
from nebula.input import KeyboardTilt
from nebula.runner import GameWindow
from nebula.save import SaveData
from nebula.settings import load_settings
from nebula.speech.speech import PrismRenderer, ScreenReader
from nebula.strings import Strings, choose_language

NAMES = {1: 'tut_movimento', 2: 'tut_inimigo', 3: 'tut_ataque', 4: 'tut_batalha', 5: 'tut_basico', 6: 'tut_especial'}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'tutorial'
    settings = load_settings()
    lang = choose_language(settings)
    reader = ScreenReader()
    services = Services(OpenALBackend(), PrismRenderer(lang), reader, Strings(lang), save=SaveData.default())
    tilt = KeyboardTilt(float(settings.get('tilt', 0.3)))
    window = GameWindow(services, tilt, 'Nebula')

    def tutorial(n):
        reader.say('Tutorial %d, %s' % (n, services.strings.get(NAMES[n]).capitalize()))
        window.set_scene(TutorialScene(services, tilt, n, on_select=window.quit, on_next=lambda: tutorial(n + 1)))

    def free():
        reader.say('Free mode')
        window.set_scene(FreeModeScene(services, tilt, on_menu=window.quit, on_new_game=free))

    if mode == 'free':
        free()
    else:
        tutorial(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    window.run()


if __name__ == '__main__':
    main()
