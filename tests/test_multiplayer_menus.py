"""The way into versus mode: the first-visit name choice, the multiplayer screen, and starting a match, with a
stand-in for the relay client."""
import random

import pygame

from nebula.game.versus import VersusScene
from nebula.menus.multiplayer import MultiplayerScreen, NameChoiceScreen, generate_name, spelled
from test_menus import at_main_menu, said


class FakeClient:
    def __init__(self):
        self.calls, self.opponent, self.name = [], None, None
        for h in ('welcome', 'waiting', 'code', 'matched', 'data', 'opponent_left', 'error'):
            setattr(self, 'on_' + h, None)

    def connect(self, name):
        self.calls.append(('connect', name))
        self.name = name

    def quick(self):
        self.calls.append(('quick',))

    def host(self):
        self.calls.append(('host',))

    def join(self, code):
        self.calls.append(('join', code))

    def send(self, payload):
        return True

    def poll(self):
        pass

    def leave(self):
        self.calls.append(('leave',))

    def close(self):
        pass


def open_multiplayer(tmp_path, name=None):
    app, window, services = at_main_menu()
    app.settings_path = str(tmp_path / 'settings.json')
    if name:
        app.settings['player_name'] = name
    client = FakeClient()
    app.make_relay_client = lambda address: client
    for _ in range(3):
        window.scene.menu_next()
    window.scene.menu_activate()
    return app, window, services, client


def test_generated_names_are_game_things_with_a_number():
    name = generate_name('en', random.Random(1))
    word, number = name.rsplit(' ', 1)
    assert word in ('Pilot', 'Starship', 'Nebula', 'Planet', 'Thunder', 'Laser', 'Shield', 'Fireball', 'Star',
                    'Fuel Tank')
    assert 1 <= int(number) <= 999
    assert spelled('4821') == '4 8 2 1'


def test_the_first_visit_asks_for_a_name_and_generating_one_moves_on(tmp_path):
    app, window, services, client = open_multiplayer(tmp_path)
    assert isinstance(window.scene, NameChoiceScreen)
    assert said(services)[-1] == 'Choose a pilot name for multiplayer. Enter a name, button'
    window.scene.menu_next()
    window.scene.menu_activate()
    assert isinstance(window.scene, MultiplayerScreen)
    assert app.player_name() and said(services)[-1] == 'Pilot: %s' % app.player_name()
    window.scene.handle_key('escape')
    assert type(window.scene).__name__ == 'MainMenuScreen'


def test_a_typed_name_is_kept(tmp_path):
    app, window, services, client = open_multiplayer(tmp_path)
    window.scene.menu_activate()                     # Enter a name
    for ch in 'Ace':
        window.scene.handle_text_event(pygame.event.Event(pygame.TEXTINPUT, text=ch))
    window.scene.menu_activate()
    assert app.player_name() == 'Ace' and isinstance(window.scene, MultiplayerScreen)
    assert app.stack[-2].__class__.__name__ == 'MainMenuScreen'


def test_quick_match_connects_waits_and_starts_the_scene(tmp_path):
    app, window, services, client = open_multiplayer(tmp_path, 'Nebula 482')
    assert isinstance(window.scene, MultiplayerScreen)
    window.scene.menu_next()
    window.scene.menu_activate()                     # Quick match
    assert isinstance(window.scene, VersusScene) and client.calls == [('connect', 'Nebula 482')]
    client.on_welcome('Nebula 482')
    assert client.calls[-1] == ('quick',)
    client.on_waiting()
    assert said(services)[-1] == 'Waiting for another pilot.'
    client.opponent = 'Starship 17'
    client.on_matched('Starship 17')
    assert window.scene.lobby is None


def test_hosting_reads_the_code_and_a_bad_code_returns(tmp_path):
    app, window, services, client = open_multiplayer(tmp_path, 'Nebula 482')
    window.scene.menu_next()
    window.scene.menu_next()
    window.scene.menu_activate()                     # Invite a friend
    client.on_welcome('Nebula 482')
    assert client.calls[-1] == ('host',)
    client.on_code('4821')
    assert said(services)[-1].startswith('Your code is 4 8 2 1.')
    client.on_error('unreachable')
    assert said(services)[-1] == "Can't reach the multiplayer server."
    assert isinstance(window.scene, MultiplayerScreen)
