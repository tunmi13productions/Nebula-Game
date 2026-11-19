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
from .settings import apply_settings, load_settings, setting
from .speech.speech import PrismRenderer, ScreenReader
from .strings import Strings, choose_language


def main():
    settings = load_settings()
    lang = choose_language(settings)
    save = SaveData.default()
    services = Services(OpenALBackend(), PrismRenderer(lang), ScreenReader(), Strings(lang),
                        GlobalState.load(save), save=save)
    tilt = KeyboardTilt()
    window = GameWindow(services, tilt, 'Nebula', float(setting(settings, 'scale')))
    apply_settings(settings, services, tilt, window)
    App(window, services, tilt, settings=settings).start()
    window.run()


if __name__ == '__main__':
    main()
