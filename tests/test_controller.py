"""Game controllers (a port addition): buttons, the stick, motion steering and vibration, with stand-ins for
SDL's controller layer and the motion sensor, so no real pad is touched."""
import pygame
import pytest

from nebula.controller.haptics import PATTERNS
from nebula.controller.pads import Pads
from nebula.game.base_scene import W
from nebula.input import KeyboardTilt
from test_combat import make, run


class FakePad:
    def __init__(self, index, name='DualSense Wireless Controller', instance=None):
        self.id, self.name = index, name
        self.instance = index if instance is None else instance
        self.rumbles = []

    def as_joystick(self):
        pad = self

        class J:
            def get_instance_id(self):
                return pad.instance
        return J()

    def rumble(self, low, high, ms):
        self.rumbles.append((low, high, ms))

    def quit(self):
        pass


class FakeSDL:
    def __init__(self, pads):
        self.pads = pads

    def init(self):
        pass

    def get_count(self):
        return len(self.pads)

    def is_controller(self, i):
        return i < len(self.pads)

    def Controller(self, i):
        return self.pads[i]


class FakeMotion:
    def __init__(self, reading=(0.0, 9.81, 0.0), capable=True):
        self.reading, self.capable, self.enabled = reading, capable, set()

    def has_accelerometer(self, ident):
        return self.capable

    def enable(self, ident, on):
        (self.enabled.add if on else self.enabled.discard)(ident)
        return True

    def acceleration(self, ident):
        return self.reading if ident in self.enabled else None


def pads(*fakes, motion=None):
    said = []
    p = Pads(pygame, sdl=FakeSDL(list(fakes) or [FakePad(0)]), motion=motion or FakeMotion(), say=said.append)
    return p, said


def button(b, down=True, instance=0):
    return pygame.event.Event(pygame.CONTROLLERBUTTONDOWN if down else pygame.CONTROLLERBUTTONUP,
                              button=b, instance_id=instance)


def axis(a, value, instance=0):
    return pygame.event.Event(pygame.CONTROLLERAXISMOTION, axis=a, value=value, instance_id=instance)


def test_cross_is_enter_in_menus_and_fire_in_play():
    p, _ = pads()
    assert p.feed(button(pygame.CONTROLLER_BUTTON_A), True) == [('enter', True), ('enter', False)]
    assert p.feed(button(pygame.CONTROLLER_BUTTON_A), False) == [('space', True), ('space', False)]


def test_circle_backs_out_of_menus_and_options_pauses_play():
    p, _ = pads()
    assert p.feed(button(pygame.CONTROLLER_BUTTON_B), True) == [('escape', True), ('escape', False)]
    assert p.feed(button(pygame.CONTROLLER_BUTTON_B), False) == []
    assert p.feed(button(pygame.CONTROLLER_BUTTON_START), False) == [('escape', True), ('escape', False)]
    assert p.feed(button(pygame.CONTROLLER_BUTTON_START), True) == []


def test_other_buttons():
    p, _ = pads()
    assert p.feed(button(pygame.CONTROLLER_BUTTON_Y), False)[0] == ('l', True)
    assert p.feed(button(pygame.CONTROLLER_BUTTON_LEFTSHOULDER), True)[0] == ('home', True)
    assert p.feed(button(pygame.CONTROLLER_BUTTON_RIGHTSHOULDER), True)[0] == ('end', True)
    assert p.feed(button(pygame.CONTROLLER_BUTTON_DPAD_DOWN), True)[0] == ('down', True)


def test_dpad_sideways_is_held_for_steering():
    p, _ = pads()
    assert p.feed(button(pygame.CONTROLLER_BUTTON_DPAD_LEFT), False) == [('left', True)]
    assert p.feed(button(pygame.CONTROLLER_BUTTON_DPAD_LEFT, down=False), False) == [('left', False)]


def test_stick_holds_sideways_and_presses_up_and_down_once_per_lean():
    p, _ = pads()
    assert p.feed(axis(pygame.CONTROLLER_AXIS_LEFTX, 0.8), False) == [('right', True)]
    assert p.feed(axis(pygame.CONTROLLER_AXIS_LEFTX, 0.5), False) == []
    assert p.feed(axis(pygame.CONTROLLER_AXIS_LEFTX, 0.1), False) == [('right', False)]
    assert p.feed(axis(pygame.CONTROLLER_AXIS_LEFTY, 0.9), True) == [('down', True), ('down', False)]
    assert p.feed(axis(pygame.CONTROLLER_AXIS_LEFTY, 0.95), True) == []
    assert p.feed(axis(pygame.CONTROLLER_AXIS_LEFTY, 0.0), True) == []
    assert p.feed(axis(pygame.CONTROLLER_AXIS_LEFTY, -0.9), True) == [('up', True), ('up', False)]


def test_only_the_first_pad_is_read():
    p, _ = pads(FakePad(0), FakePad(1, 'Xbox Controller'))
    assert p.feed(button(pygame.CONTROLLER_BUTTON_A, instance=1), True) == []


def test_connecting_and_disconnecting_is_announced_but_not_a_double_listing():
    first = FakePad(0)
    p, said = pads(first)
    p._sdl.pads.append(FakePad(1, instance=5))       # the DualSense listed again
    p.feed(pygame.event.Event(pygame.CONTROLLERDEVICEADDED, device_index=1), True)
    assert said == []
    p.feed(pygame.event.Event(pygame.CONTROLLERDEVICEREMOVED, instance_id=0), True)
    assert said == []
    p.feed(pygame.event.Event(pygame.CONTROLLERDEVICEREMOVED, instance_id=5), True)
    assert said == ['DualSense Wireless Controller disconnected']
    p._sdl.pads.append(FakePad(2, 'Xbox Controller', instance=7))
    p.feed(pygame.event.Event(pygame.CONTROLLERDEVICEADDED, device_index=2), True)
    assert said[-1] == 'Xbox Controller connected'


def test_rolling_the_pad_right_is_tilting_the_phone_right():
    motion = FakeMotion(reading=(-9.81 * 0.4, 9.0, 0.0))     # rolled right, gravity along -x
    p, _ = pads(motion=motion)
    assert p.can_tilt()
    assert p.tilt() == pytest.approx(0.4)
    p.tilt_scale = 2.0
    assert p.tilt() == pytest.approx(0.8)
    p.tilt_scale = 5.0
    assert p.tilt() == 1.0
    p.tilt_enabled = False
    assert p.tilt() is None


def test_a_pad_without_motion_does_not_steer():
    p, _ = pads(FakePad(0, 'Xbox Controller'), motion=FakeMotion(capable=False))
    assert not p.can_tilt() and p.tilt() is None


def test_keys_win_over_the_pad_roll():
    keys = KeyboardTilt(0.3)
    keys.motion = lambda: -0.5
    assert keys() == -0.5
    keys.right = True
    assert keys() == 0.3


def test_rumble_goes_to_the_pad():
    pad = FakePad(0)
    p, _ = pads(pad)
    p.rumble(*PATTERNS['hit'])
    assert pad.rumbles == [PATTERNS['hit']]


def test_vibration_for_hits_explosion_and_power_ups():
    scene, services, keys = make(shield_points=1)
    h = services.haptics
    scene.player.inflict_damage(1)               # the shield takes it
    scene.player.inflict_damage(1)               # life
    assert h.played == ['hit', 'hit']
    while scene.player.life > 1:
        scene.player.inflict_damage(1)
    h.played.clear()
    scene.player.inflict_damage(1)               # fatal
    assert h.played == ['explode']


def test_vibration_at_each_edge_once_on_arrival():
    scene, services, keys = make()
    keys.right = True
    run(scene, services, 6.0)
    assert scene.player.position[0] == pytest.approx(W - scene.player.ship_size[0] * 0.5)
    assert services.haptics.played == ['edge_right']
    keys.right, keys.left = False, True
    run(scene, services, 6.0)
    assert services.haptics.played == ['edge_right', 'edge_left']


def test_vibration_off_buzzes_nothing():
    scene, services, keys = make()
    buzzes = []
    services.haptics.rumble = lambda *a: buzzes.append(a)
    services.haptics.enabled = False
    services.haptics.hit()
    assert buzzes == []
    services.haptics.enabled = True
    services.haptics.power_up()
    assert buzzes == [PATTERNS['power_up']]
