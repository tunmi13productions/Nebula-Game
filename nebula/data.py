"""Game data tables built from the original bundle by tools/extract_data.py."""
import json
import os

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


def _load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


SHIPS = {int(k): v for k, v in _load('ships.json').items()}
SHIP_SOUNDS = {int(k): v for k, v in _load('ship_sounds.json').items()}
TEXTURES = {k: tuple(v) for k, v in _load('textures.json').items()}
BOSSES = {int(k): v for k, v in _load('bosses.json').items()}


def engine_sound(code):
    """The engine loop for a ship code as (name, extension), following BaseScene createEnemyWithType:.

    The extension is caf for code 43 and codes above 46, otherwise mp3. Codes without an entry, such as the
    boss parts 100 to 105, return None, as the original found no sound for them.
    """
    name = SHIP_SOUNDS.get(code)
    if name is None:
        return None
    return name, ('caf' if code == 43 or code > 46 else 'mp3')
