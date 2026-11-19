"""Game controllers (a port addition, DEVIATIONS.md, "Game controllers").

Built on SDL's game controller layer (pygame._sdl2.controller), which gives every pad the same standard
layout. The first pad attached is the one the game reads. Its buttons become the keys the game already
takes, so no screen needs to know about pads:

    D-pad up and down, left stick up and down    Up, Down (menus)
    D-pad left and right, left stick sideways     Left, Right (held: steering; in menus: changing values)
    Cross / A                                     Enter in a menu, Space (fire, skip a cutscene) in play
    Circle / B                                    Escape in a menu (back)
    Options / Start                               Escape in play (pause)
    Triangle / Y                                  L (speak life)
    L1, R1                                        Home, End (first and last menu item)

A pad with an accelerometer (a DualSense, DualShock 4 or Switch Pro pad) also steers by being rolled left
and right, like the phone was tilted: see tilt(). Connecting and disconnecting a pad is announced through
the screen reader.

Two lessons from Sixth Sense Reborn's controller code (MIT License, the same authors): a DualSense on
Windows is listed twice at start, and the removal of the first listing makes pygame.event.get() raise
SystemError (read_events catches it); and pygame's Controller.id is the device index, not SDL's instance id,
which is what events and the sensor calls use (instance_id).
"""
import logging
import math

from .motion import Motion

log = logging.getLogger('controller')

GRAVITY = 9.81
STICK_PRESS = 0.6      # how far the left stick must lean to count as a press
STICK_RELEASE = 0.3    # and how far back it must come before it lets go

_BUTTONS = {
    'CONTROLLER_BUTTON_DPAD_UP': 'up', 'CONTROLLER_BUTTON_DPAD_DOWN': 'down',
    'CONTROLLER_BUTTON_DPAD_LEFT': 'left', 'CONTROLLER_BUTTON_DPAD_RIGHT': 'right',
    'CONTROLLER_BUTTON_A': 'a', 'CONTROLLER_BUTTON_B': 'b', 'CONTROLLER_BUTTON_START': 'start',
    'CONTROLLER_BUTTON_Y': 'y', 'CONTROLLER_BUTTON_LEFTSHOULDER': 'l1',
    'CONTROLLER_BUTTON_RIGHTSHOULDER': 'r1',
}


def read_events(pygame):
    """pygame.event.get(), kept from crashing on the DualSense's double listing at start."""
    try:
        return pygame.event.get()
    except SystemError:
        log.warning('pygame could not read a device event, so it was skipped', exc_info=True)
        return []


def instance_id(pad):
    try:
        return pad.as_joystick().get_instance_id()
    except Exception:
        return pad.id


def axis_value(value):
    value = float(value)
    return value / 32768.0 if abs(value) > 1.0 else value


class Pads:
    def __init__(self, pygame, sdl=None, motion=None, say=None):
        """sdl: pygame's controller module, motion: a Motion, say: speaks a line through the screen reader.
        The tests pass stand-ins, so they never open a real pad."""
        self.pygame = pygame
        self.say = say or (lambda text: None)
        self.motion = motion if motion is not None else Motion()
        self.tilt_enabled = True
        self.tilt_scale = 1.0
        self._pads = {}           # instance id -> Controller, oldest first
        self._sensing = set()     # instance ids whose accelerometer is switched on
        self._lean = {}           # axis -> -1, 0 or 1
        self._buttons = {getattr(pygame, k): v for k, v in _BUTTONS.items()}
        self._sdl = None
        try:
            if sdl is None:
                from pygame._sdl2 import controller as sdl
            sdl.init()
            self._sdl = sdl
            for index in range(sdl.get_count()):
                self._open(index, announce=False)
        except Exception:
            log.exception('controller support is off')

    # pads coming and going

    def _open(self, index, announce=True):
        try:
            if not self._sdl.is_controller(index):
                return
            pad = self._sdl.Controller(index)
        except Exception:
            log.exception('opening controller %s', index)
            return
        ident = instance_id(pad)
        if ident in self._pads:
            return
        name = getattr(pad, 'name', None) or 'controller'
        known = name in self.names
        self._pads[ident] = pad
        if self.motion.has_accelerometer(ident) and self.motion.enable(ident, True):
            self._sensing.add(ident)
        if announce and not known:
            self.say('%s connected' % name)

    def _close(self, ident):
        pad = self._pads.pop(ident, None)
        self._sensing.discard(ident)
        self._lean.clear()
        if pad is not None:
            name = getattr(pad, 'name', None) or 'controller'
            if name not in self.names:      # the DualSense's second listing going is not a pad leaving
                self.say('%s disconnected' % name)

    @property
    def names(self):
        out = []
        for pad in self._pads.values():
            name = getattr(pad, 'name', None) or 'controller'
            if name not in out:
                out.append(name)
        return out

    def active_id(self):
        for ident in self._pads:
            return ident
        return None

    def can_tilt(self):
        return any(i in self._sensing for i in self._pads)

    # input

    def tilt(self):
        """The pad's roll as the phone's acceleration.x, or None when no pad can sense it or tilt steering
        is off. SDL gives the pad's acceleration with gravity in it, x to the pad's right: rolled right,
        gravity pulls along -x, which is the phone's +x tilted right. Scaled by tilt_scale and kept within
        -1 to 1, a phone on its side."""
        if not self.tilt_enabled:
            return None
        for ident in self._pads:
            if ident not in self._sensing:
                continue
            reading = self.motion.acceleration(ident)
            if reading is None:
                continue
            x = -reading[0] / GRAVITY * self.tilt_scale
            if math.isnan(x):
                return None
            return max(-1.0, min(1.0, x))
        return None

    def feed(self, event, in_menu):
        """The controls a pad event stands for, as a list of (name, down) with names from the game's keys:
        'up', 'down', 'left', 'right', 'enter', 'space', 'escape', 'l', 'home', 'end'. None for an event that
        isn't a pad's. in_menu says whether the scene shown is a menu, which decides what Cross and Circle
        and Options mean."""
        pg = self.pygame
        t = event.type
        if t == pg.CONTROLLERDEVICEADDED:
            if self._sdl is not None and getattr(event, 'device_index', None) is not None:
                self._open(event.device_index)
            return []
        if t == pg.CONTROLLERDEVICEREMOVED:
            self._close(getattr(event, 'instance_id', None))
            return []
        if t not in (pg.CONTROLLERBUTTONDOWN, pg.CONTROLLERBUTTONUP, pg.CONTROLLERAXISMOTION):
            return None
        active = self.active_id()
        if active is not None and getattr(event, 'instance_id', active) != active:
            return []
        if t == pg.CONTROLLERAXISMOTION:
            return self._stick(event.axis, axis_value(event.value))
        down = t == pg.CONTROLLERBUTTONDOWN
        button = self._buttons.get(event.button)
        if button in ('left', 'right'):
            return [(button, down)]               # held, for steering
        if not down:
            return []
        name = {'up': 'up', 'down': 'down', 'y': 'l', 'l1': 'home', 'r1': 'end'}.get(button)
        if button == 'a':
            name = 'enter' if in_menu else 'space'
        elif button == 'b':
            name = 'escape' if in_menu else None
        elif button == 'start':
            name = None if in_menu else 'escape'
        return [(name, True), (name, False)] if name else []

    def _stick(self, axis, value):
        """Sideways, the stick holds left or right like the D-pad. Up and down, each lean is one press."""
        pg = self.pygame
        if axis == pg.CONTROLLER_AXIS_LEFTX:
            keys, held = ('left', 'right'), True
        elif axis == pg.CONTROLLER_AXIS_LEFTY:
            keys, held = ('up', 'down'), False
        else:
            return []
        lean = self._lean.get(axis, 0)
        out = []
        if lean and (abs(value) < STICK_RELEASE or (value < 0) != (lean < 0)):
            if held:
                out.append((keys[0] if lean < 0 else keys[1], False))
            lean = 0
        if not lean and abs(value) >= STICK_PRESS:
            lean = -1 if value < 0 else 1
            key = keys[0] if lean < 0 else keys[1]
            out += [(key, True)] if held else [(key, True), (key, False)]
        self._lean[axis] = lean
        return out

    def rumble(self, low, high, ms):
        """Buzzes the pad the game reads: low and high motor strengths 0 to 1, for ms milliseconds."""
        ident = self.active_id()
        if ident is None:
            return
        try:
            self._pads[ident].rumble(low, high, int(ms))
        except Exception:
            log.debug('the pad did not buzz')

    def close(self):
        for ident in list(self._sensing):
            self.motion.enable(ident, False)
        self._sensing.clear()
        for pad in list(self._pads.values()):
            try:
                pad.quit()
            except Exception:
                pass
        self._pads.clear()
