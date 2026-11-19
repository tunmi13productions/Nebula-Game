"""Everything a scene needs from the outside world, bundled so tests can build a silent set."""
import os

from ..audio.aureal import Aureal
from ..audio.backend import NullBackend
from ..audio.players import Effects
from ..engine.scheduler import Scheduler
from ..speech.speech import CONTINUE_TEXT, GameVoice, NullRenderer, NullScreenReader
from ..save import SaveData
from ..strings import SOUNDS, Strings
from .globals import GlobalState
from ..controller.haptics import Haptics

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
        self.voice.screen_reader = screen_reader
        self.voice.continue_text = CONTINUE_TEXT.get(strings.language, CONTINUE_TEXT['en'])
        self.save = save if save is not None else SaveData.in_memory()
        self.danger_zone = 1.5  # attack sounds' centred zone, as a multiple of the real hit range
        self.haptics = Haptics()  # controller vibration; the window connects it to a pad

    @staticmethod
    def sound_path(name, ext):
        path = os.path.join(SOUNDS, '%s.%s' % (name, ext))
        return path if os.path.exists(path) else None

    @classmethod
    def silent(cls, language='en'):
        """No sound device, no speech: for tests."""
        return cls(NullBackend(), NullRenderer(), NullScreenReader(), Strings(language))
