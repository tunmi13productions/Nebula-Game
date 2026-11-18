r"""Starts Nebula: python -m nebula

Progress is saved in %APPDATA%\Nebula\save.json and settings are read from %APPDATA%\Nebula\settings.json.
"""
from .app import App
from .audio.openal_backend import OpenALBackend
from .game.globals import GlobalState
from .game.services import Services
from .input import KeyboardTilt
from .runner import GameWindow
from .save import SaveData
from .settings import load_settings
from .speech.speech import PrismRenderer, ScreenReader
from .strings import Strings, choose_language


def main():
    settings = load_settings()
    lang = choose_language(settings)
    save = SaveData.default()
    services = Services(OpenALBackend(), PrismRenderer(lang), ScreenReader(), Strings(lang),
                        GlobalState.load(save), save=save)
    services.laser_zone = float(settings.get('laser_zone', 1.5))
    tilt = KeyboardTilt(float(settings.get('tilt', 0.3)), float(settings.get('fast_tilt', 0.6)))
    window = GameWindow(services, tilt, 'Nebula', float(settings.get('scale', 1.5)))
    App(window, services, tilt).start()
    window.run()


if __name__ == '__main__':
    main()
