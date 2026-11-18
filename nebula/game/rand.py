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


def arc4random_uniform(upper_bound):
    """libc arc4random_uniform: a value below upper_bound without modulo bias, drawing arc4random() until it
    reaches (2**32 - upper_bound) % upper_bound. Bounds below 2 return 0 without drawing."""
    upper_bound = int(upper_bound) & 0xFFFFFFFF
    if upper_bound < 2:
        return 0
    least = (0x100000000 - upper_bound) % upper_bound
    while True:
        r = arc4random()
        if r >= least:
            return r % upper_bound
