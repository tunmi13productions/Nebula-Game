"""Non-positional playback: SKAction playSoundFileNamed (effects) and plain AVAudioPlayer use (music, narration).

These play centred at full volume, as in the original. Stereo files keep their own left and right content.
"""
import os

import soundfile

_lengths = {}


def clip_seconds(path):
    """Length of an audio file in seconds, cached."""
    if path not in _lengths:
        _lengths[path] = soundfile.info(path).duration
    return _lengths[path]


class Narration:
    """One AVAudioPlayer for narration clips, as the tutorial and cutscenes use it: playing a new clip
    replaces (and stops) the previous one, and the completion runs when the clip ends."""

    def __init__(self, backend, scheduler):
        self.backend, self.scheduler = backend, scheduler
        self._handle = None
        self._timer = None
        self.played = []

    def play(self, path, on_done=None):
        self.stop()
        self._handle = self.backend.load(path)
        self.backend.play(self._handle)
        self.played.append(os.path.basename(path))
        if on_done is not None:
            self._timer = self.scheduler.after(clip_seconds(path), on_done)

    def stop(self):
        if self._timer is not None:
            self._timer.invalidate()
            self._timer = None
        if self._handle is not None:
            self.backend.stop(self._handle)
            self.backend.release(self._handle)
            self._handle = None


class Effects:
    """Fire-and-forget sounds, like `[self runAction:[SKAction playSoundFileNamed:@"x.caf" waitForCompletion:NO]]`."""

    def __init__(self, backend, sounds_dir):
        self.backend, self.sounds_dir = backend, sounds_dir
        self._live = []
        self.played = []   # file names, in order, for tests and debugging

    def play(self, filename):
        self._sweep()
        handle = self.backend.load(os.path.join(self.sounds_dir, filename))
        self.backend.play(handle)
        self._live.append(handle)
        self.played.append(filename)
        return handle

    def stop_all(self):
        for h in self._live:
            self.backend.stop(h)
            self.backend.release(h)
        self._live = []

    def play_then(self, filename, on_done, scheduler):
        """playSoundFileNamed with waitForCompletion YES inside a sequence: on_done runs when the file ends."""
        self.play(filename)
        scheduler.after(clip_seconds(os.path.join(self.sounds_dir, filename)), on_done)

    def _sweep(self):
        keep = []
        for h in self._live:
            if self.backend.is_playing(h):
                keep.append(h)
            else:
                self.backend.release(h)
        self._live = keep
