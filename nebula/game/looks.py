"""What the original's nodes looked like: texture frame lists and colours. Visual only; no game logic reads these.

Frame lists are built the way BaseScene initializingTexture built them, from the sorted "PlayerPower_" and
"Fireball_" textures (Global getTexturesWithPrefix:).
"""


def _prefixed(prefix, count):
    return ['%s%02d' % (prefix, i) for i in range(1, count + 1)]


PLAYER_POWER = _prefixed('PlayerPower_', 15)
FIREBALL = _prefixed('Fireball_', 15)            # Global EnemyShoot, and BaseScene arrayPower_2


def _array_power_1():
    """Remove index 0, then indexes 13 down to 6: PlayerPower_02 to 07."""
    a = list(PLAYER_POWER)
    del a[0]
    for i in range(13, 5, -1):
        del a[i]
    return a


def _array_power_3():
    """Remove index 0, then index 0, 1, 2, 3 and 4 of the shrinking list, as the original loop does."""
    a = list(PLAYER_POWER)
    del a[0]
    for i in range(5):
        del a[i]
    return a


ARRAY_POWER_1 = _array_power_1()   # the player's shot in flight
ARRAY_POWER_2 = FIREBALL           # an enemy bullet bursting
ARRAY_POWER_3 = _array_power_3()   # the player's shot bursting

EXPLOSION_1 = _prefixed('Explosion02_', 24)    # Global Explosion_1, a destroyed ship
EXPLOSION_2 = ['Explosion03_%02d' % i for i in range(1, 33) if i != 21]   # Global Explosion_2 (there is no 21)
EXPLOSION_FRAME = 0.032

PLAYER_SHOT_FRAME = 0.04
BULLET_FRAME = 0.8                  # SpaceShip shoot: animateWithTextures:timePerFrame: 0.8, repeated
BOSS_BULLET_FRAME = 0.03


def ui_color(r, g, b, a=1.0):
    """UIColor colorWithRed:green:blue:alpha: clamps each component to 0 to 1. The original passed values
    such as 229 and 153 meaning 0 to 255, so most of its colours clamp to full strength."""
    return tuple(min(1.0, max(0.0, float(v))) for v in (r, g, b, a))


ORANGE = (1.0, 0.5, 0.0, 1.0)
GREEN = (0.0, 1.0, 0.0, 1.0)
BLACK = (0.0, 0.0, 0.0, 1.0)


def ship_color(code):
    """SpaceShip getSpaceShipColor: the tint of an enemy's bullets."""
    if code < 7:
        return ORANGE
    if 7 <= code < 12:
        return GREEN
    if 12 <= code < 17:
        return ui_color(56, 148, 240)
    if 17 <= code < 20:
        return ui_color(204, 0, 102)
    if code & ~3 == 28:
        return ui_color(32, 32, 32)
    if code & ~3 == 24:
        return ui_color(0, 0, 204)
    if code & ~3 == 20:
        return ui_color(0, 128, 255)
    if 32 <= code < 37:
        return ui_color(204, 102, 0)
    if 37 <= code < 40:
        return ui_color(224, 224, 224)
    if code & ~1 == 40:
        return ui_color(153, 0, 0)
    if code == 44:
        return ui_color(51, 51, 0)
    return BLACK
