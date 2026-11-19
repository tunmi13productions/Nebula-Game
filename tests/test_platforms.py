"""macOS and Linux paths, checked on any system by standing in for the platform: where saves go, the
language from the locale, and the game voice speaking live when no engine can render to memory."""
import os

from nebula import settings, strings
from nebula.speech.speech import GameVoice, PrismRenderer
from nebula.engine.scheduler import Scheduler
from nebula.audio.backend import NullBackend


def test_save_folder_per_system(monkeypatch):
    monkeypatch.setattr(settings.sys, 'platform', 'darwin')
    assert settings.user_dir() == os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'Nebula')
    monkeypatch.setattr(settings.sys, 'platform', 'linux')
    monkeypatch.setenv('XDG_DATA_HOME', '/tmp/xdg')
    assert settings.user_dir() == os.path.join('/tmp/xdg', 'Nebula')
    monkeypatch.delenv('XDG_DATA_HOME')
    assert settings.user_dir() == os.path.join(os.path.expanduser('~'), '.local', 'share', 'Nebula')


def test_language_from_the_locale_off_windows(monkeypatch):
    for name in ('LC_ALL', 'LC_MESSAGES', 'LANG', 'LANGUAGE'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('LANG', 'pt_BR.UTF-8')
    assert strings._locale_language() == 'pt'
    monkeypatch.setenv('LANG', 'en_US.UTF-8')
    assert strings._locale_language() == 'en'


class LiveEngine:
    def __init__(self):
        self.said, self.stopped, self.rate = [], 0, None

    def speak(self, text, interrupt=False):
        self.said.append(text)

    def stop(self):
        self.stopped += 1


def live_renderer():
    r = PrismRenderer.__new__(PrismRenderer)
    r.backend, r.live = LiveEngine(), True
    return r


def test_a_live_engine_speaks_the_whole_line_and_times_it():
    r = live_renderer()
    samples, channels, rate = r.render('Put your headphones, for a better experience.', 0.5)
    assert r.backend.said == ['Put your headphones, for a better experience.']   # one line, not clauses
    seconds = len(samples) / rate
    assert 2.0 < seconds < 5.0


def test_stopping_the_game_voice_silences_a_live_engine():
    r = live_renderer()
    scheduler = Scheduler()
    voice = GameVoice(NullBackend(), scheduler, r)
    voice.speak('Thunder at the right side.', 0.55)
    scheduler.update(0.01)
    voice.stop()
    assert r.backend.stopped == 1
