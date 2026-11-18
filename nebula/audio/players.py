"""Non-positional playback: SKAction playSoundFileNamed (effects) and plain AVAudioPlayer use (music, narration).

These play centred at full volume, as in the original. Stereo files keep their own left and right content.
"""
import os


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

    def _sweep(self):
        keep = []
        for h in self._live:
            if self.backend.is_playing(h):
                keep.append(h)
            else:
                self.backend.release(h)
        self._live = keep
