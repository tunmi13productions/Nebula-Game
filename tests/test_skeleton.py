import os

from nebula.audio.backend import NullBackend
from nebula.audio.openal_backend import open_device


def test_tests_run_on_the_null_driver():
    assert os.environ['ALSOFT_DRIVERS'] == 'null'


def test_openal_soft_opens_silently():
    device, context = open_device()
    assert 'OpenAL Soft' in device.name


def test_null_backend_records_and_tracks_state():
    audio = NullBackend()
    h = audio.load('sounds/beep_radar.caf')
    audio.play(h, loops=-1)
    audio.set_pan(h, -0.5)
    audio.set_volume(h, 0.25)
    assert audio.is_playing(h)
    assert audio.state[h]['loops'] == -1 and audio.state[h]['pan'] == -0.5 and audio.state[h]['volume'] == 0.25
    audio.finish(h)
    assert not audio.is_playing(h)
    assert audio.calls[0] == ('load', h, 'sounds/beep_radar.caf')
