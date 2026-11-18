"""SpriteKit-style actions.

An Action is a reusable description. Running it on a node creates a fresh runner, so one Action can be
used by several nodes, or repeated, without sharing state. Runners consume frame time and hand any
leftover time to the next action, which keeps long sequences exact regardless of frame boundaries.
"""
import math
import random

LINEAR, EASE_IN, EASE_OUT, EASE_IN_EASE_OUT = 0, 1, 2, 3


def ease(mode, t):
    """Maps linear progress t (0 to 1) through an SKActionTimingMode curve.

    Apple doesn't publish the exact curves. These are the sine curves commonly used to match them.
    """
    if mode == EASE_IN:
        return 1.0 - math.cos(t * math.pi / 2)
    if mode == EASE_OUT:
        return math.sin(t * math.pi / 2)
    if mode == EASE_IN_EASE_OUT:
        return (1.0 - math.cos(t * math.pi)) / 2
    return t


class Action:
    duration = 0.0
    timing_mode = LINEAR

    def runner(self, node):
        raise NotImplementedError

    def with_timing(self, mode):
        """Sets the timing mode (SKAction.timingMode) and returns self, for chaining."""
        self.timing_mode = mode
        return self


class Runner:
    """Advances one running action. update() returns leftover time once finished, or None while still running."""

    def update(self, dt):
        raise NotImplementedError


# Instant actions

class _Instant(Action):
    def __init__(self, fn):
        self.fn = fn

    def runner(self, node):
        action = self

        class R(Runner):
            def update(self, dt):
                action.fn(node)
                return dt
        return R()


def run_block(fn):
    """SKAction runBlock: calls fn() when reached."""
    return _Instant(lambda node: fn())


def remove_from_parent():
    return _Instant(lambda node: node.remove_from_parent())


def play_sound(fn):
    """playSoundFileNamed with waitForCompletion NO: an instant action. The caller supplies the play function."""
    return _Instant(lambda node: fn())


# Timed actions

class _Timed(Action):
    """A tween over `duration`. Subclasses implement begin(node) and apply(node, previous, current)."""

    def runner(self, node):
        action = self
        state = {'elapsed': 0.0, 'p': 0.0, 'duration': action.duration, 'started': False}

        class R(Runner):
            def update(self, dt):
                if not state['started']:
                    # Like SpriteKit, a tween reads its start values when it begins, not when it was built.
                    state['started'] = True
                    action.begin(node, state)
                duration = state['duration']
                if duration <= 0:
                    action.apply(node, state, 0.0, 1.0)
                    return dt
                step = min(dt, duration - state['elapsed'])
                state['elapsed'] += step
                t = min(state['elapsed'] / duration, 1.0)
                p = ease(action.timing_mode, t)
                action.apply(node, state, state['p'], p)
                state['p'] = p
                if state['elapsed'] >= duration - 1e-12:
                    return dt - step
                return None
        return R()

    def begin(self, node, state):
        pass


class wait(_Timed):
    """SKAction waitForDuration, optionally withRange (uniform in duration +/- range/2)."""

    def __init__(self, duration, range_=0.0):
        self.duration, self.range_ = duration, range_

    def begin(self, node, state):
        if self.range_:
            state['duration'] = max(0.0, self.duration + random.uniform(-self.range_ / 2, self.range_ / 2))

    def apply(self, node, state, p0, p1):
        pass


class move_to(_Timed):
    def __init__(self, x=None, y=None, duration=0.0):
        self.x, self.y, self.duration = x, y, duration

    def begin(self, node, state):
        state['start'] = node.position

    def apply(self, node, state, p0, p1):
        sx, sy = state['start']
        x = sx + (self.x - sx) * p1 if self.x is not None else node.position[0]
        y = sy + (self.y - sy) * p1 if self.y is not None else node.position[1]
        node.position = (x, y)


def move_to_x(x, duration):
    return move_to(x=x, duration=duration)


def move_to_y(y, duration):
    return move_to(y=y, duration=duration)


class move_by(_Timed):
    """Relative move applied incrementally, so concurrent relative moves add up as in SpriteKit."""

    def __init__(self, dx, dy, duration):
        self.dx, self.dy, self.duration = dx, dy, duration

    def apply(self, node, state, p0, p1):
        x, y = node.position
        node.position = (x + self.dx * (p1 - p0), y + self.dy * (p1 - p0))


class _PropertyTo(_Timed):
    def __init__(self, attr, target, duration):
        self.attr, self.target, self.duration = attr, target, duration

    def begin(self, node, state):
        state['start'] = getattr(node, self.attr)

    def apply(self, node, state, p0, p1):
        setattr(node, self.attr, state['start'] + (self.target - state['start']) * p1)


class _PropertyBy(_Timed):
    def __init__(self, attr, delta, duration, multiply=False):
        self.attr, self.delta, self.duration, self.multiply = attr, delta, duration, multiply

    def begin(self, node, state):
        state['start'] = getattr(node, self.attr)

    def apply(self, node, state, p0, p1):
        if self.multiply:
            s = state['start']
            setattr(node, self.attr, s + (s * self.delta - s) * p1)
        else:
            setattr(node, self.attr, getattr(node, self.attr) + self.delta * (p1 - p0))


def fade_alpha_to(alpha, duration):
    return _PropertyTo('alpha', alpha, duration)


def fade_in(duration):
    return _PropertyTo('alpha', 1.0, duration)


def fade_out(duration):
    return _PropertyTo('alpha', 0.0, duration)


def scale_to(scale, duration):
    return _PropertyTo('scale', scale, duration)


def scale_by(factor, duration):
    return _PropertyBy('scale', factor, duration, multiply=True)


def rotate_by(angle, duration):
    return _PropertyBy('rotation', angle, duration)


def resize_to_width(width, duration):
    return _PropertyTo('width', width, duration)


# Composites

class sequence(Action):
    def __init__(self, actions):
        self.actions = list(actions)
        self.duration = sum(a.duration for a in self.actions)

    def runner(self, node):
        actions = self.actions

        class R(Runner):
            def __init__(self):
                self.i = 0
                self.current = actions[0].runner(node) if actions else None

            def update(self, dt):
                while self.current is not None:
                    left = self.current.update(dt)
                    if left is None:
                        return None
                    dt = left
                    self.i += 1
                    self.current = actions[self.i].runner(node) if self.i < len(actions) else None
                return dt
        return R()


class group(Action):
    """All actions run at once. The group ends with its longest member."""

    def __init__(self, actions):
        self.actions = list(actions)
        self.duration = max((a.duration for a in self.actions), default=0.0)

    def runner(self, node):
        runners = [a.runner(node) for a in self.actions]

        class R(Runner):
            def __init__(self):
                self.live = list(runners)
                self.left = []

            def update(self, dt):
                still = []
                for r in self.live:
                    left = r.update(dt)
                    if left is None:
                        still.append(r)
                    else:
                        self.left.append(left)
                self.live = still
                if still:
                    return None
                return min(self.left) if self.left else dt
        return R()


class repeat(Action):
    """Repeats an action `count` times, or forever when count is None."""

    def __init__(self, action, count=None):
        self.action, self.count = action, count
        self.duration = float('inf') if count is None else action.duration * count

    def runner(self, node):
        action, count = self.action, self.count

        class R(Runner):
            def __init__(self):
                self.done = 0
                self.current = action.runner(node) if count != 0 else None

            def update(self, dt):
                while self.current is not None:
                    before = dt
                    left = self.current.update(dt)
                    if left is None:
                        return None
                    self.done += 1
                    if count is not None and self.done >= count:
                        self.current = None
                        return left
                    self.current = action.runner(node)
                    if left >= before:
                        # A pass that used no time: run it once per frame instead of spinning forever.
                        return None
                    dt = left
                return dt
        return R()


def repeat_forever(action):
    return repeat(action, None)
