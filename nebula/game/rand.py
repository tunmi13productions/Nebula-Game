"""The original's random numbers: arc4random and BaseScene getRandomNumberBetween:maxNumber:.

One shared generator so tests can seed it and replay a run exactly.
"""
import random

rng = random.Random()


def seed(value):
    rng.seed(value)


def arc4random():
    return rng.getrandbits(32)


def between(lo, hi):
    """getRandomNumberBetween:maxNumber:, inclusive: arc4random() % (hi - lo + 1) + lo, with unsigned modulo."""
    lo, hi = int(lo), int(hi)
    if lo == hi:
        return lo
    span = (1 - lo + hi) & 0xFFFFFFFF
    return (arc4random() % span + lo) if span else lo
