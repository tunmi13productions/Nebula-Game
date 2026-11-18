"""Everything a scene needs from the outside world, bundled so tests can build a silent set."""
import os

from ..audio.aureal import Aureal
from ..audio.backend import NullBackend
from ..audio.players import Effects
from ..engine.scheduler import Scheduler
from ..speech.speech import GameVoice, NullRenderer, NullScreenReader
from ..save import SaveData
from ..strings import SOUNDS, Strings
from .globals import GlobalState


class Services:
    def __init__(self, audio, voice_renderer, screen_reader, strings, global_state=None, scheduler=None, save=None):
        self.audio = audio
        self.scheduler = scheduler or Scheduler()
        self.strings = strings
        self.globals = global_state or GlobalState()
        self.aureal = Aureal(audio, self.scheduler, self.sound_path)
        self.effects = Effects(audio, SOUNDS)
        self.voice = GameVoice(audio, self.scheduler, voice_renderer)
        self.screen_reader = screen_reader
        self.save = save if save is not None else SaveData.in_memory()
        self.danger_zone = 1.5  # attack sounds' centred zone, as a multiple of the real hit range

    @staticmethod
    def sound_path(name, ext):
        path = os.path.join(SOUNDS, '%s.%s' % (name, ext))
        return path if os.path.exists(path) else None

    @classmethod
    def silent(cls, language='en'):
        """No sound device, no speech: for tests."""
        return cls(NullBackend(), NullRenderer(), NullScreenReader(), Strings(language))
