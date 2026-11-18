"""Aureal, the original game's positional audio engine, ported function by function.

Positions are scene points (320 by 568, y up). Every sound has a string key and an AVAudioPlayer-style
volume and pan, which are driven from the sound's position relative to the listener (the player ship).
See docs/NOTES.md, "Recovered mechanics: Aureal audio engine", for the original behaviour.
"""
import math

FADE = 1          # stopSoundNamed:withOptions: value that fades out
UPDATE_INTERVAL = 0.1
FADE_STEP = 1.0 / 6.0
FADE_DELAY = 0.5


def _f32(x):
    """Rounds to float32, as the original stores these values in CGFloat and float ivars on armv7."""
    import struct
    return struct.unpack('<f', struct.pack('<f', x))[0]


def _cbrt(x):
    return math.copysign(abs(x) ** (1.0 / 3.0), x)


class AurealSound:
    """AurealAudioObject: a player plus its key, linked node, max volume and last known position."""

    def __init__(self, key, handle):
        self.key = key
        self.handle = handle
        self.max_audio = 1.0
        self.linked = None
        self.is_linked = False
        self.last_position = (0.0, 0.0)


class Aureal:
    def __init__(self, backend, scheduler, resolve_path):
        """resolve_path(name, ext) returns a file path, or None if the bundle has no such file."""
        self.backend = backend
        self.scheduler = scheduler
        self.resolve_path = resolve_path
        self.library = {}
        self.listener = (0.0, 0.0)
        self.max_distance = 0.0
        self.max_x = 0.0
        self.scene = None
        self.sound_id = 0          # soundIDEnumerator
        self._timer = None

    # configuration

    def configure(self, max_distance, listener, scene, max_x=None):
        """configureMaxDistance (and the max_X variant) and start the 0.1 second update timer.

        The original starts a new NSTimer on every call without stopping the old one. Several timers only
        made updates more frequent, which isn't audible, so one timer is kept here.
        """
        self.max_distance = max_distance
        if max_x is not None:
            self.max_x = max_x
        self.listener = listener
        self.scene = scene
        if self._timer is not None:
            self._timer.invalidate()
        self._timer = self.scheduler.every(UPDATE_INTERVAL, lambda t: self.update())

    # library

    def add_sound(self, name, ext, key):
        """addSoundIntoDictionary:ofType:withKey:. Returns False if the file can't be loaded."""
        path = self.resolve_path(name, ext)
        if path is None:
            return False
        try:
            handle = self.backend.load(path)
        except Exception:
            return False
        old = self.library.get(key)
        if old is not None:
            self.backend.stop(old.handle)
            self.backend.release(old.handle)
        self.library[key] = AurealSound(key, handle)
        return True

    def next_key(self):
        """The `[NSString stringWithFormat:@"%ld", soundIDEnumerator]` pattern used by every caller."""
        return '%d' % self.sound_id

    def play_once(self, key, position):
        s = self.library.get(key)
        if s is None:
            return False
        self.configure_player(s, position)
        self.backend.play(s.handle, loops=0)
        return True

    def play_forever(self, key, position):
        s = self.library.get(key)
        if s is None:
            return False
        self.configure_player(s, position)
        self.backend.play(s.handle, loops=-1)
        return True

    def stop(self, key, option=0):
        s = self.library.get(key)
        if s is None:
            return False
        if option == FADE:
            self._fade_step(s)
        else:
            self.backend.stop(s.handle)
        return True

    def _fade_step(self, s):
        s.max_audio = _f32(s.max_audio - FADE_STEP)
        if s.max_audio <= 0.0:
            self.backend.stop(s.handle)
        else:
            self.scheduler.after(FADE_DELAY, lambda: self._fade_step(s))

    def change_position(self, key, position):
        s = self.library.get(key)
        if s is None:
            return False
        self.configure_player(s, position)
        return True

    def link(self, key, node):
        s = self.library.get(key)
        if s is None:
            return False
        s.linked = node
        s.last_position = node.position if node is not None else (0.0, 0.0)
        s.is_linked = True
        return True

    def stop_all(self):
        for s in list(self.library.values()):
            self.backend.stop(s.handle)
            self.backend.release(s.handle)
        self.library.clear()

    def pause_all(self):
        for s in self.library.values():
            self.backend.pause(s.handle)

    def resume_all(self):
        for s in self.library.values():
            self.backend.resume(s.handle)

    # the 0.1 second update

    def update(self):
        remove = []
        for key in list(self.library.keys()):
            s = self.library[key]
            if s.linked is None:
                if not self.backend.is_playing(s.handle) and s.is_linked:
                    remove.append(key)
                else:
                    self.configure_player(s, s.last_position)
            elif s.linked.parent is None:
                self.stop(key, 2)
                s.linked = None
                remove.append(key)
            else:
                self.configure_player(s, s.linked.position)
        for key in remove:
            s = self.library.pop(key, None)
            if s is not None:
                self.backend.release(s.handle)

    # math, matching the original functions one to one

    def configure_player(self, s, position):
        self.backend.set_pan(s.handle, _f32(self.pan_based_on_max_x(position)))
        s.last_position = position
        angle = self.angle_to(position)
        volume = self.new_volume(position)
        factor = self.mask_normal(angle) if angle < 0.0 else s.max_audio
        self.backend.set_volume(s.handle, _f32(volume * factor))

    def new_volume(self, p):
        lx, ly = self.listener
        d = math.hypot(abs(_f32(p[0] - lx)), abs(_f32(p[1] - ly)))
        v = 1.0 - d / self.max_distance if self.max_distance else 0.0
        return 0.0 if v < 0.0 else v

    def angle_to(self, p):
        lx, ly = self.listener
        return math.atan2(_f32(p[1] - ly), _f32(p[0] - lx))

    def angular_pan(self, p):
        return math.cos(self.angle_to(p))

    def linear_pan(self, p):
        return _f32(p[0] - self.listener[0]) / self.max_x if self.max_x else 0.0

    def pan_based_on_max_x(self, p):
        lx = self.listener[0]
        dx = _f32(p[0] - lx)
        w = self.scene.size[0] if self.scene is not None else 0.0
        n = abs(int(_f32(_f32(w * 0.5) - lx)))
        if not w or not self.max_x:
            return 0.0
        return _cbrt(dx * (2.0 - n / w)) / _cbrt(self.max_x)

    @staticmethod
    def mask_normal(angle):
        v = (math.cos(angle + angle) + 1.0) * 0.5 + 0.2
        return 1.0 if v > 1.0 else v

    mask_muffled = mask_normal    # byte-identical in the original
