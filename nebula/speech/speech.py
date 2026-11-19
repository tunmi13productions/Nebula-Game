"""Speech.

Two outputs, matching the original's split (see docs/DEVIATIONS.md):
- GameVoice is the original VoiceSynthesizer (AVSpeechSynthesizer). The I.C.A.R.U.S. lines, status lines
  and in-game menus use it. Speech is rendered by a Windows OneCore voice through Prism into memory and
  played through the game's audio, so the game knows exactly when each line ends.
- ScreenReader sends UIKit-style accessibility labels (main menu, Hangar and so on) to the user's screen
  reader through Prism, the way VoiceOver read them in the original.

VoiceSynthesizer behaviour reproduced here:
- speak(text, rate): stops current speech immediately and speaks. It doesn't cancel a pending completion.
- speak_queued(text, rate, pre, post): queued behind whatever is playing, with no completion.
- speak_then(text, rate, pre, post, on_done): stops all speech and cancels any pending completion, then
  speaks. A 0.3 second timer polls for the end of speech. The first two polls are skipped, and the
  completion fires on the first poll that finds nothing speaking, not paused and not stopped.
- pause() and resume() only hold back the completion. The voice itself keeps talking, as in the original.
"""

import re

from ..audio.volumes import VOLUMES

POLL = 0.3
IGNORED_POLLS = 2


class Speaker:
    def speak(self, text, rate=0.55):
        raise NotImplementedError

    def speak_queued(self, text, rate=0.55, pre_delay=0.0, post_delay=0.0):
        raise NotImplementedError

    def speak_then(self, text, rate, pre_delay, post_delay, on_done):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def pause(self):
        raise NotImplementedError

    def resume(self):
        raise NotImplementedError


class NullRenderer:
    """Stand-in for text-to-speech in tests: silent samples whose length scales with text length and rate."""

    def __init__(self, seconds_per_char=0.06):
        self.seconds_per_char = seconds_per_char

    def render(self, text, rate):
        seconds = len(text) * self.seconds_per_char * (0.5 / max(rate, 0.05))
        sample_rate = 1000
        return [0.0] * max(1, int(seconds * sample_rate)), 1, sample_rate


# Silence after a clause, by the punctuation that ends it. AVSpeechSynthesizer paused clearly at punctuation;
# the OneCore voice barely does at these rates, so each clause is rendered on its own and these gaps are added.
PAUSES = {',': 0.25, ';': 0.3, ':': 0.3, '.': 0.45, '!': 0.45, '?': 0.45}
_CLAUSE = re.compile(r'(.*?[,;:.!?]+)(?:\s+|$)', re.S)


def split_clauses(text):
    """Splits text after punctuation that is followed by a space (or ends the text). Returns a list of
    (clause, pause seconds). Runs like "., " count once, with the longest of their pauses. Numbers such as
    "1.5" stay whole."""
    out, pos = [], 0
    for m in _CLAUSE.finditer(text):
        if m.start() != pos:
            break
        clause = m.group(1).strip()
        marks = clause[len(clause.rstrip(',;:.!?')):]
        if clause:
            out.append((clause, max(PAUSES[c] for c in marks)))
        pos = m.end()
    rest = text[pos:].strip()
    if rest:
        out.append((rest, 0.0))
    return out


def render_with_pauses(render_one, text, rate):
    """render_one(text, rate) -> (samples, channels, sample_rate). Renders clause by clause, adding the
    silences, and drops the pause after the last clause so the end of speech stays where it was."""
    clauses = split_clauses(text) or [(text, 0.0)]
    pcm, channels, sample_rate = [], 1, 16000
    for i, (clause, pause) in enumerate(clauses):
        samples, channels, sample_rate = render_one(clause, rate)
        pcm.extend(samples)
        if i < len(clauses) - 1 and pause > 0:
            pcm.extend([0.0] * int(pause * sample_rate) * channels)
    return pcm or [0.0], channels, sample_rate


# The text-to-speech engines tried for the game voice, in order: Windows (OneCore, then SAPI), macOS
# (AVSpeech) and Linux (Spiel, then Speech Dispatcher). The game voice stands for the original's
# AVSpeechSynthesizer, so plain engines come before screen readers.
VOICE_BACKENDS = ('ONE_CORE', 'SAPI', 'AV_SPEECH', 'SPIEL', 'SPEECH_DISPATCHER')
CHARS_PER_SECOND = 15.0   # a live engine's speed at rate 0.5, for timing lines it can't render


class PrismRenderer:
    """Renders the game voice with a Prism engine that supports speak_to_memory, so the game hears the exact
    end of each line and plays it through its own audio.

    Where no engine can render to memory, the first engine that works speaks live instead, and render()
    returns silence of the line's estimated length, so the game's timing still has an end to wait for
    (`live` is then True)."""

    def __init__(self, language='en', backend_names=VOICE_BACKENDS):
        import prism
        from prism import core
        self._lib, self._ffi = core.lib, core.ffi
        ctx = prism.Context()
        self.backend = None
        self.live = False
        fallback = None
        for name in backend_names:
            try:
                b = ctx.create(getattr(prism.BackendId, name))
            except Exception:
                continue
            if b.features.supports_speak_to_memory:
                self.backend = b
                break
            fallback = fallback or b
        if self.backend is None:
            if fallback is None:
                raise RuntimeError('No text-to-speech engine is available for the game voice')
            self.backend, self.live = fallback, True
        self._context = ctx
        self.select_language(language)

    def select_language(self, language):
        """Picks the first voice whose language starts with the code ('en', 'pt'). It keeps the default if none matches."""
        b = self.backend
        for i in range(b.voices_count):
            if b.get_voice_language(i).lower().startswith(language.lower()):
                b.voice = i
                return True
        return False

    def render(self, text, rate):
        if self.live:
            return self._speak_live(text, rate)
        return render_with_pauses(self._render_one, text, rate)

    def _speak_live(self, text, rate):
        """Speaks the line now and returns silence as long as it should take."""
        try:
            self.backend.rate = max(0.0, min(1.0, rate))
            self.backend.speak(text, interrupt=False)
        except Exception:
            pass
        seconds = len(text) / (CHARS_PER_SECOND * (0.5 + max(0.0, min(1.0, rate))))
        sample_rate = 16000
        return [0.0] * max(1, int(seconds * sample_rate)), 1, sample_rate

    def stop(self):
        """Silences a live engine (a rendered line is stopped with its sound)."""
        if self.live:
            try:
                self.backend.stop()
            except Exception:
                pass

    def _render_one(self, text, rate):
        self.backend.rate = max(0.0, min(1.0, rate))
        out = {'pcm': [], 'channels': 1, 'rate': 16000}
        ffi = self._ffi

        @ffi.callback('void(void *, const float *, size_t, size_t, size_t)')
        def on_audio(_user, ptr, count, channels, rate_hz):
            if count:
                out['pcm'].extend(ffi.unpack(ptr, count))
            out['channels'], out['rate'] = channels, rate_hz

        # prismatoid 0.18.3's speak_to_memory passes str where the C API needs bytes, so it's called directly.
        self._lib.prism_backend_speak_to_memory(self.backend._raw, text.encode('utf-8'), on_audio, ffi.NULL)
        if not out['pcm']:
            out['pcm'] = [0.0]
        return out['pcm'], out['channels'], out['rate']


class GameVoice(Speaker):
    def __init__(self, audio, scheduler, renderer):
        self.audio, self.scheduler, self.renderer = audio, scheduler, renderer
        self._queue = []          # utterances waiting: (text, rate, pre, post)
        self._current = None      # {'handle', 'timer'} while an utterance (with its delays) is in progress
        self._poll = None
        self._ignore = 0
        self._on_done = None
        self.should_stop = False
        self.should_pause = False
        self.spoken = []          # every line started, in order, for tests and debugging

    @property
    def speaking(self):
        return self._current is not None or bool(self._queue)

    # VoiceSynthesizer API

    def speak(self, text, rate=0.55):
        self._cut()
        self._enqueue(text, rate, 0.0, 0.0)

    def speak_queued(self, text, rate=0.55, pre_delay=0.0, post_delay=0.0):
        self._enqueue(text, rate, pre_delay, post_delay)

    def speak_then(self, text, rate, pre_delay, post_delay, on_done):
        self.stop()
        self.should_stop = False
        self.should_pause = False
        self._ignore = IGNORED_POLLS
        self._on_done = on_done
        self._poll = self.scheduler.every(POLL, self._check_finished)
        self.speak_queued(text, rate, pre_delay, post_delay)

    def stop(self):
        self.should_stop = True
        if self._poll is not None:
            self._poll.invalidate()
            self._poll = None
        self._cut()

    def pause(self):
        self.should_pause = True

    def resume(self):
        self.should_pause = False

    # internals

    def _check_finished(self, timer):
        if self._ignore > 0:
            self._ignore -= 1
            return
        if self.should_stop:
            timer.invalidate()
            return
        if not self.speaking and not self.should_pause:
            timer.invalidate()
            self._poll = None
            done, self._on_done = self._on_done, None
            if done is not None:
                done()

    def _cut(self):
        self._queue.clear()
        if self._current is not None:
            if self._current['timer'] is not None:
                self._current['timer'].invalidate()
            if self._current['handle'] is not None:
                self.audio.stop(self._current['handle'])
                self.audio.release(self._current['handle'])
            self._current = None
            stop = getattr(self.renderer, 'stop', None)
            if stop is not None:
                stop()                  # an engine speaking live

    def _enqueue(self, text, rate, pre, post):
        self._queue.append((text, rate, pre, post))
        if self._current is None:
            self._next()

    def _next(self):
        if not self._queue:
            self._current = None
            return
        text, rate, pre, post = self._queue.pop(0)
        cur = self._current = {'handle': None, 'timer': None}

        def start():
            samples, channels, sample_rate = self.renderer.render(text, min(1.0, rate * VOLUMES.speech_rate))
            cur['handle'] = self.audio.load_samples(samples, channels, sample_rate)
            if VOLUMES.speech != 1.0:
                self.audio.set_volume(cur['handle'], VOLUMES.speech)
            self.audio.play(cur['handle'])
            self.spoken.append((text, rate, pre, post))
            seconds = len(samples) / max(channels, 1) / sample_rate
            cur['timer'] = self.scheduler.after(seconds + post, finish)

        def finish():
            if self._current is cur:
                self.audio.release(cur['handle'])
                self._current = None
                self._next()

        if pre > 0:
            cur['timer'] = self.scheduler.after(pre, start)
        else:
            start()


class ScreenReader:
    """Accessibility-label output through the user's screen reader (Prism's best backend, NVDA here)."""

    def __init__(self):
        import prism
        self._context = prism.Context()
        self.backend = self._context.acquire_best()

    def say(self, text, interrupt=True):
        self.backend.speak(text, interrupt)

    def stop(self):
        self.backend.stop()


class NullScreenReader:
    def __init__(self):
        self.said = []

    def say(self, text, interrupt=True):
        self.said.append(text)

    def stop(self):
        pass
