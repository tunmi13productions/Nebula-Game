import math
import os
import random
import struct
import sys

import pytest

from nebula.audio.aureal import Aureal, FADE
from nebula.audio.backend import NullBackend
from nebula.audio.openal_backend import BALANCE, CONSTANT_POWER, pan_gains
from nebula.engine.nodes import Node, Scene
from nebula.engine.scheduler import Scheduler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINARY = os.path.join(ROOT, 'decompiled', 'ipa', 'Payload', 'BEPiDGame.app', 'BEPiDGame')
W, H = 320.0, 568.0
LISTENER = (160.0, 108.0)


def make(listener=LISTENER):
    audio, clock, scene = NullBackend(), Scheduler(), Scene(W, H)
    a = Aureal(audio, clock, lambda name, ext: '%s.%s' % (name, ext))
    a.configure(H * 1.25, listener, scene, max_x=W)
    return a, audio, clock, scene


def test_volume_falls_linearly_to_zero_at_max_distance():
    a, *_ = make()
    assert a.new_volume(LISTENER) == pytest.approx(1.0)
    assert a.new_volume((LISTENER[0], LISTENER[1] + H * 1.25 / 2)) == pytest.approx(0.5, abs=1e-5)
    assert a.new_volume((LISTENER[0], LISTENER[1] + H * 2)) == 0.0


def test_pan_is_a_cube_root_curve_of_the_offset():
    a, *_ = make()
    assert a.pan_based_on_max_x((320.0, 400.0)) == pytest.approx(1.0)
    assert a.pan_based_on_max_x((0.0, 400.0)) == pytest.approx(-1.0)
    assert a.pan_based_on_max_x((180.0, 400.0)) == pytest.approx(0.5)


def test_behind_mask():
    assert Aureal.mask_normal(-math.pi / 2) == pytest.approx(0.2)
    assert Aureal.mask_normal(-math.pi / 4) == pytest.approx(0.7)
    assert Aureal.mask_normal(0.0) == 1.0


def test_sound_in_front_uses_max_audio_but_behind_ignores_it():
    a, audio, *_ = make()
    a.add_sound('Ship_10', 'mp3', 'front')
    a.add_sound('Ship_10', 'mp3', 'behind')
    for key in ('front', 'behind'):
        a.library[key].max_audio = 0.5
    a.play_forever('front', (160.0, 108.0 + 100))
    a.play_forever('behind', (160.0, 108.0 - 100))
    front = audio.state[a.library['front'].handle]['volume']
    behind = audio.state[a.library['behind'].handle]['volume']
    dist = 1 - 100 / (H * 1.25)
    assert front == pytest.approx(dist * 0.5, abs=1e-5)
    assert behind == pytest.approx(dist * 0.2, abs=1e-5)


def test_linked_sound_follows_its_node_and_stops_when_the_node_leaves_the_scene():
    a, audio, clock, scene = make()
    ship = Node(position=(40.0, 450.0))
    scene.add_child(ship)
    a.add_sound('Ship_10', 'mp3', '0')
    a.link('0', ship)
    a.play_forever('0', ship.position)
    handle = a.library['0'].handle
    ship.position = (280.0, 450.0)
    clock.update(0.1)
    assert audio.state[handle]['pan'] > 0.9
    ship.remove_from_parent()
    clock.update(0.1)
    assert '0' not in a.library
    assert ('stop', handle) in audio.calls


def test_finished_sounds_are_dropped_only_if_they_were_linked():
    a, audio, clock, scene = make()
    a.add_sound('explosion', 'mp3', 'boom')
    a.play_once('boom', (100.0, 300.0))
    audio.finish(a.library['boom'].handle)
    clock.update(0.1)
    assert 'boom' in a.library   # original quirk: unlinked one-shots stay in the library


def test_fade_out_drops_max_audio_by_a_sixth_every_half_second_then_stops():
    a, audio, clock, scene = make()
    a.add_sound('Laser_Firing', 'mp3', 'laser')
    a.play_once('laser', (160.0, 400.0))
    s = a.library['laser']
    a.stop('laser', FADE)
    assert s.max_audio == pytest.approx(5 / 6, abs=1e-6)
    clock.update(1.0)
    assert s.max_audio == pytest.approx(3 / 6, abs=1e-6)
    clock.update(3.0)
    assert not audio.is_playing(s.handle)


def test_pan_laws():
    assert pan_gains(0.0, BALANCE, False) == (1.0, 1.0)
    assert pan_gains(-1.0, BALANCE, False) == (1.0, 0.0)
    assert pan_gains(0.5, BALANCE, False) == (0.5, 1.0)
    l, r = pan_gains(0.0, CONSTANT_POWER, False)
    assert l == pytest.approx(math.sqrt(0.5)) and r == pytest.approx(math.sqrt(0.5))
    assert pan_gains(0.3, CONSTANT_POWER, True) == pan_gains(0.3, BALANCE, True)


@pytest.mark.skipif(not os.path.exists(BINARY), reason='original binary not unpacked')
def test_matches_the_original_aureal_in_the_emulator():
    sys.path.insert(0, os.path.join(ROOT, 'tools', 're'))
    import io
    from objc_trace import Tracer, u32f, f64
    t = Tracer(BINARY, out=io.StringIO())
    orig = t.new_object('Aureal')
    scene = t.new_object('Chapter1Scene')
    t.send(scene, 'initWithSize:', u32f(W), u32f(H))
    rng = random.Random(7)
    for _ in range(40):
        listener = (rng.uniform(20, 300), rng.uniform(40, 200))
        lo_d, hi_d = struct.unpack('<II', struct.pack('<d', H * 1.25))
        lo_x, hi_x = struct.unpack('<II', struct.pack('<d', W))
        # configureMax_Y_Distance:(double)max_X_distance:(double)andListenerPosition:(CGPoint)inScene:
        t.send(orig, 'configureMax_Y_Distance:max_X_distance:andListenerPosition:inScene:',
               lo_d, hi_d, lo_x, hi_x, u32f(listener[0]), u32f(listener[1]), scene)
        a, *_ = make(listener)
        for _ in range(10):
            p = (rng.uniform(-50, 370), rng.uniform(-50, 650))
            args = (u32f(p[0]), u32f(p[1]))

            def call_double(sel):
                t.send(orig, sel, *args)
                return f64(t.mu.reg_read(t.regs_r0), t.mu.reg_read(t.regs_r1))
            assert call_double('getNewVolume:') == pytest.approx(a.new_volume(p), abs=1e-5)
            assert call_double('getPanBasedOnMaxX:') == pytest.approx(a.pan_based_on_max_x(p), abs=1e-5)
            angle = call_double('getAngleBetweenListenerAndObjectWithPosition:')
            assert angle == pytest.approx(a.angle_to(p), abs=1e-5)
            assert f64(*_double_args(t, orig, 'maskNormalSound:', angle)) == pytest.approx(Aureal.mask_normal(angle), abs=1e-9)


def _double_args(t, obj, sel, value):
    lo, hi = struct.unpack('<II', struct.pack('<d', value))
    t.send(obj, sel, lo, hi)
    return t.mu.reg_read(t.regs_r0), t.mu.reg_read(t.regs_r1)
