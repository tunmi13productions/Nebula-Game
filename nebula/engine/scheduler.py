"""Delayed and repeating calls on the game clock: performSelector afterDelay, dispatch_after and NSTimer.

These keep running while a scene is paused, as they did in the original, because they aren't SpriteKit actions.
"""
import heapq
import itertools


class Timer:
    def __init__(self, scheduler, fn, interval, repeats):
        self.scheduler, self.fn, self.interval, self.repeats = scheduler, fn, interval, repeats
        self.valid = True

    def invalidate(self):
        self.valid = False


class Scheduler:
    def __init__(self):
        self.now = 0.0
        self._queue = []
        self._order = itertools.count()

    def after(self, delay, fn):
        """Calls fn() once, delay seconds from now. Returns a Timer that can be invalidated."""
        return self._push(Timer(self, fn, delay, False), self.now + delay)

    def every(self, interval, fn):
        """Calls fn(timer) every interval seconds until invalidated, like a repeating NSTimer."""
        return self._push(Timer(self, fn, interval, True), self.now + interval)

    def _push(self, timer, when):
        heapq.heappush(self._queue, (when, next(self._order), timer))
        return timer

    def update(self, dt):
        """Advances the clock by dt and fires everything due, in time order, including calls scheduled meanwhile."""
        end = self.now + dt
        while self._queue and self._queue[0][0] <= end + 1e-12:
            when, _, timer = heapq.heappop(self._queue)
            if not timer.valid:
                continue
            self.now = max(self.now, when)
            if timer.repeats:
                timer.fn(timer)
                if timer.valid:
                    self._push(timer, when + timer.interval)
            else:
                timer.valid = False
                timer.fn()
        self.now = end
