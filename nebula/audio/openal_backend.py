"""OpenAL Soft output through cyal.

Each sound plays through two sources: one placed hard left (90 degrees) carrying the file's left channel,
one hard right carrying its right channel. For mono files both carry the same data. OpenAL Soft renders
sources at +/-90 degrees to a single output channel, so left and right gains are set exactly from the pan
value, independent of OpenAL's own panning curve. That reproduces AVAudioPlayer's volume and pan controls.
"""
import math

import cyal
import numpy as np
import soundfile

from .backend import AudioBackend

BALANCE = 'balance'                # the quieter side fades out, the nearer side stays at full level
CONSTANT_POWER = 'constant_power'  # sine and cosine law, about -3 dB per side at the centre


def open_device():
    """Opens the default OpenAL device and a current context. Raises if the library isn't OpenAL Soft."""
    device = cyal.Device()
    if 'OpenAL Soft' not in device.name:
        raise RuntimeError('OpenAL Soft is required, found: %s' % device.name)
    context = cyal.Context(device, make_current=True)
    return device, context


def pan_gains(pan, law, stereo):
    """Left and right gains for an AVAudioPlayer pan from -1 to 1. Stereo files always use balance."""
    pan = max(-1.0, min(1.0, pan))
    if stereo or law == BALANCE:
        return (1.0 if pan <= 0 else 1.0 - pan), (1.0 if pan >= 0 else 1.0 + pan)
    a = (pan + 1.0) * math.pi / 4
    return math.cos(a), math.sin(a)


class _Voice:
    def __init__(self, clip):
        self.clip = clip
        self.volume = 1.0
        self.pan = 0.0
        self.sources = None
        self.paused = False


class OpenALBackend(AudioBackend):
    def __init__(self, pan_law=BALANCE):
        self.device, self.context = open_device()
        self.pan_law = pan_law
        self._clips = {}     # path -> (left buffer, right buffer, stereo)
        self._voices = {}
        self._next = 1

    def _clip(self, path):
        clip = self._clips.get(path)
        if clip is None:
            data, rate = soundfile.read(path, dtype='int16', always_2d=True)
            clip = self._clips[path] = self._make_clip(data, rate)
        return clip

    def _make_clip(self, data, rate):
        stereo = data.shape[1] > 1
        bufs = []
        for ch in ((0, 1) if stereo else (0, 0)):
            b = self.context.gen_buffer()
            b.set_data(np.ascontiguousarray(data[:, ch]).tobytes(), sample_rate=rate, format=cyal.BufferFormat.MONO16)
            bufs.append(b)
        return (bufs[0], bufs[1], stereo)

    def load_samples(self, samples, channels, rate):
        pcm = np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0)
        data = (pcm * 32767).astype(np.int16).reshape(-1, max(channels, 1))
        handle = self._next
        self._next += 1
        self._voices[handle] = _Voice(self._make_clip(data, rate))
        return handle

    def load(self, path):
        handle = self._next
        self._next += 1
        self._voices[handle] = _Voice(self._clip(path))
        return handle

    def _apply(self, v):
        if v.sources is None:
            return
        gl, gr = pan_gains(v.pan, self.pan_law, v.clip[2])
        v.sources[0].gain = max(0.0, v.volume * gl)
        v.sources[1].gain = max(0.0, v.volume * gr)

    def _free(self, v):
        if v.sources is not None:
            for s in v.sources:
                s.stop()
            v.sources = None

    def play(self, handle, loops=0):
        v = self._voices[handle]
        self._free(v)
        left = self.context.gen_source()
        right = self.context.gen_source()
        for src, buf, x in ((left, v.clip[0], -1.0), (right, v.clip[1], 1.0)):
            src.buffer = buf
            src.relative = True
            src.rolloff_factor = 0.0
            src.position = (x, 0.0, 0.0)
            src.looping = loops < 0
        v.sources = (left, right)
        v.paused = False
        self._apply(v)
        self.context.play_sources(left, right)

    def stop(self, handle):
        v = self._voices.get(handle)
        if v is not None:
            self._free(v)

    def pause(self, handle):
        v = self._voices.get(handle)
        if v is not None and v.sources is not None:
            self.context.pause_sources(*v.sources)
            v.paused = True

    def resume(self, handle):
        v = self._voices.get(handle)
        if v is not None and v.sources is not None and v.paused:
            self.context.play_sources(*v.sources)
            v.paused = False

    def set_volume(self, handle, volume):
        v = self._voices[handle]
        v.volume = volume
        self._apply(v)

    def set_pan(self, handle, pan):
        v = self._voices[handle]
        v.pan = pan
        self._apply(v)

    def is_playing(self, handle):
        v = self._voices.get(handle)
        if v is None or v.sources is None:
            return False
        if v.paused:
            return False
        if v.sources[0].state == cyal.SourceState.STOPPED:
            self._free(v)   # finished: give the sources back
            return False
        return True

    def release(self, handle):
        v = self._voices.pop(handle, None)
        if v is not None:
            self._free(v)

    def close(self):
        for v in self._voices.values():
            self._free(v)
        self._voices.clear()
        self._clips.clear()
