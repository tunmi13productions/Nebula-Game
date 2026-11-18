"""Audio backend interface and a silent recording backend for tests.

Game code talks only to this interface. The OpenAL backend implements it for real playback.
"""


class AudioBackend:
    """Plays decoded sounds. Volume is 0 to 1 and pan is -1 (left) to 1 (right), like AVAudioPlayer."""

    def load(self, path):
        """Loads a sound file and returns a handle used by the other calls."""
        raise NotImplementedError

    def play(self, handle, loops=0):
        """Starts playback from the beginning. loops=-1 repeats forever, as in AVAudioPlayer."""
        raise NotImplementedError

    def stop(self, handle):
        raise NotImplementedError

    def pause(self, handle):
        raise NotImplementedError

    def resume(self, handle):
        raise NotImplementedError

    def set_volume(self, handle, volume):
        raise NotImplementedError

    def set_pan(self, handle, pan):
        raise NotImplementedError

    def is_playing(self, handle):
        raise NotImplementedError

    def release(self, handle):
        """Frees the handle's resources."""
        raise NotImplementedError

    def close(self):
        pass


class NullBackend(AudioBackend):
    """Makes no sound. It records every call in `calls` and tracks state so tests can assert on it."""

    def __init__(self):
        self.calls = []
        self.state = {}
        self._next = 1

    def load(self, path):
        handle = self._next
        self._next += 1
        self.state[handle] = {'path': path, 'playing': False, 'volume': 1.0, 'pan': 0.0, 'loops': 0}
        self.calls.append(('load', handle, path))
        return handle

    def play(self, handle, loops=0):
        self.state[handle].update(playing=True, loops=loops)
        self.calls.append(('play', handle, loops))

    def stop(self, handle):
        self.state[handle]['playing'] = False
        self.calls.append(('stop', handle))

    def pause(self, handle):
        self.calls.append(('pause', handle))

    def resume(self, handle):
        self.calls.append(('resume', handle))

    def set_volume(self, handle, volume):
        self.state[handle]['volume'] = volume
        self.calls.append(('volume', handle, volume))

    def set_pan(self, handle, pan):
        self.state[handle]['pan'] = pan
        self.calls.append(('pan', handle, pan))

    def is_playing(self, handle):
        return self.state[handle]['playing']

    def finish(self, handle):
        """Test helper: marks a sound as having played to its end."""
        self.state[handle]['playing'] = False

    def release(self, handle):
        self.state.pop(handle, None)
        self.calls.append(('release', handle))
