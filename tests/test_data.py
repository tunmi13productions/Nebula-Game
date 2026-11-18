import os

from nebula.data import SHIPS, SHIP_SOUNDS, TEXTURES, engine_sound
from nebula.strings import SOUNDS


def test_ship_table_matches_the_documented_values():
    assert len(SHIPS) == 57
    assert SHIPS[0] == {'life': 2, 'score': 10, 'fire_interval': 2.0, 'move_interval': 0.9, 'damage': 1, 'laser': False}
    assert SHIPS[13]['life'] == 46 and SHIPS[13]['damage'] == 10
    assert SHIPS[37]['score'] == -100
    assert SHIPS[45] == {'life': 140, 'score': 300, 'fire_interval': 0.6, 'move_interval': 1.0, 'damage': 12, 'laser': False}
    assert SHIPS[103]['life'] == 50 and SHIPS[100]['laser'] and not SHIPS[103]['laser']
    assert sorted(c for c, s in SHIPS.items() if s['laser']) == [3, 5, 7, 8, 15, 23, 27, 30, 42, 100, 101, 102]


def test_engine_sounds_exist_with_the_original_extension_rule():
    assert SHIP_SOUNDS[0] == 'Ship_50' and SHIP_SOUNDS[12] == 'Ship_2'
    assert engine_sound(43) == ('Ship_44', 'caf')
    assert engine_sound(48) == ('sonarpedra', 'caf')
    assert engine_sound(10) == ('Ship_11', 'mp3')
    assert engine_sound(100) is None
    for code in range(0, 51):
        name, ext = engine_sound(code)
        assert os.path.exists(os.path.join(SOUNDS, '%s.%s' % (name, ext))), code


def test_texture_sizes():
    assert TEXTURES['Boss_01'] == (481.0, 417.0)
    assert TEXTURES['SpaceShips_1'] == (238.0, 298.0)
