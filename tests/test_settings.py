"""The Settings screen (a port addition): moving, changing values, saving and applying them."""
import json

import pytest

from nebula.app import App
from nebula.audio.volumes import VOLUMES
from nebula.game.services import Services
from nebula.input import KeyboardTilt
from nebula.menus.settings_screen import SettingsScreen
from nebula.settings import apply_settings
from test_menus import Window


@pytest.fixture(autouse=True)
def reset_volumes():
    yield
    VOLUMES.sounds = VOLUMES.music = VOLUMES.speech = VOLUMES.speech_rate = 1.0


def open_settings(tmp_path, settings=None):
    services = Services.silent('en')
    window = Window(services)
    tilt = KeyboardTilt()
    apply_settings(settings or {}, services, tilt)     # as nebula/__main__.py does at start
    path = str(tmp_path / 'settings.json')
    app = App(window, services, tilt, settings=dict(settings or {}), settings_path=path)
    services.save.set_integer('primeiraVez', 1)
    app.open_main_menu()
    window.run(4.0)
    window.scene.handle_key('f1')
    return app, window, services, tilt, path


def test_f1_opens_settings_and_reads_the_first_option_with_a_hint(tmp_path):
    app, window, services, tilt, path = open_settings(tmp_path)
    assert isinstance(window.scene, SettingsScreen)
    first = services.screen_reader.said[-1]
    assert first.startswith('Systems. Steering speed, 0.3. How fast the ship slides')
    assert first.endswith('Left and right arrows change it')


def test_up_and_down_move_left_and_right_change_the_value(tmp_path):
    app, window, services, tilt, path = open_settings(tmp_path)
    screen = window.scene
    screen.handle_key('right')
    screen.handle_key('right')
    assert services.screen_reader.said[-1] == '0.4'
    assert tilt.tilt == pytest.approx(0.4)
    screen.menu_next()
    assert services.screen_reader.said[-1] == ('Fast steering speed, with Shift, 0.6. '
                                               'The same, while you also hold Shift.')
    screen.handle_key('left')
    assert tilt.fast_tilt == pytest.approx(0.55)
    with open(path, encoding='utf-8') as f:
        saved = json.load(f)
    assert saved['tilt'] == pytest.approx(0.4) and saved['fast_tilt'] == pytest.approx(0.55)


def test_values_stop_at_their_limits(tmp_path):
    app, window, services, tilt, path = open_settings(tmp_path, {'tilt': 1.0})
    window.scene.handle_key('right')
    assert tilt.tilt == pytest.approx(1.0)
    assert services.screen_reader.said[-1] == '1'


def test_volumes_and_language(tmp_path):
    app, window, services, tilt, path = open_settings(tmp_path)
    screen = window.scene
    for _ in range(6):
        screen.menu_next()
    screen.handle_key('left')
    assert services.screen_reader.said[-1] == '90%'
    assert VOLUMES.sounds == pytest.approx(0.9)
    for _ in range(5):
        screen.menu_next()
    assert 'Language, Follow Windows, takes effect after a restart' in services.screen_reader.said[-1]
    screen.handle_key('right')
    assert services.screen_reader.said[-1] == 'English'


def test_back_returns_to_the_main_menu(tmp_path):
    app, window, services, tilt, path = open_settings(tmp_path)
    window.scene.handle_key('escape')
    assert type(window.scene).__name__ == 'MainMenuScreen'


def test_settings_file_values_apply_at_start(tmp_path):
    services = Services.silent('en')
    tilt = KeyboardTilt()
    apply_settings({'tilt': 0.5, 'speech_volume': 0.3, 'laser_zone': 2.0}, services, tilt)
    assert tilt.tilt == 0.5 and tilt.fast_tilt == 0.6
    assert VOLUMES.speech == 0.3 and services.danger_zone == 2.0


def test_systems_is_spoken_after_about_and_the_doors_keep_multiplayer(tmp_path):
    from test_menus import at_main_menu
    app, window, services = at_main_menu()
    window.run(4.0)
    textures = {n.texture for n in window.scene.view.walk() if getattr(n, 'texture', None)}
    assert 'rightDoor_en_4' in textures and 'rightDoorSystems_en_4' not in textures
    menu = window.scene
    for _ in range(6):
        menu.menu_next()
    menu.menu_activate()
    assert isinstance(window.scene, SettingsScreen)


def test_screen_reader_game_voice_option(tmp_path):
    app, window, services, tilt, path = open_settings(tmp_path)
    screen = window.scene
    for _ in range(10):
        screen.menu_next()
    assert services.screen_reader.said[-1].startswith('Game voice, Built-in voice. Experimental')
    screen.handle_key('right')
    assert services.screen_reader.said[-1] == 'Screen reader, experimental'
    assert services.voice.reader_mode
    screen.handle_key('right')
    assert not services.voice.reader_mode
