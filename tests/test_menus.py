"""The startup sequence and the UIKit-style menu screens, driven silently through App."""
from nebula.app import App
from nebula.game.free_mode import FreeModeScene
from nebula.game.services import Services
from nebula.menus.main_menu import MainMenuScreen

FRAME = 1 / 60


class Window:
    """GameWindow's scene switching without pygame."""

    def __init__(self, services):
        self.services, self.scene = services, None

    def set_scene(self, scene):
        old = self.scene
        if old is not None and hasattr(old, 'stop_audio'):
            old.stop_audio()
        self.scene = scene
        scene.did_move_to_view()

    def run(self, seconds):
        for _ in range(int(round(seconds / FRAME))):
            self.services.scheduler.update(FRAME)
            self.scene.step(FRAME)


def make_app():
    services = Services.silent('en')
    window = Window(services)
    app = App(window, services, None)
    return app, window, services


def at_main_menu():
    app, window, services = make_app()
    app.open_main_menu()
    return app, window, services


def said(services):
    return services.screen_reader.said


def test_startup_speaks_the_headphones_notice_then_thunder_then_opens_the_menu():
    app, window, services = make_app()
    app.start()
    assert services.effects.played == []
    window.run(2.0)
    assert 'thunder.mp3' not in services.effects.played
    window.run(8.0)
    assert 'thunder.mp3' in services.effects.played
    assert 'Cilada Games.caf' not in services.effects.played
    window.run(4.5)
    assert isinstance(window.scene, MainMenuScreen)
    assert said(services)[-1] == 'Campaign, button'


def test_main_menu_reads_its_buttons_in_screen_order():
    app, window, services = at_main_menu()
    menu = window.scene
    for _ in range(6):
        menu.menu_next()
    assert said(services) == ['Campaign, button', 'Free Mode, button', 'Tutorial, button', 'Hangar, button',
                              'About, button']
    menu.menu_previous()
    assert said(services)[-1] == 'Hangar, button'


def test_main_menu_plays_the_doors_once_and_resets_chapter_control():
    app, window, services = at_main_menu()
    services.save.set('ControleCapitulo', 'yes')
    window.scene.did_move_to_view()
    assert services.save.get('ControleCapitulo') == 'no'
    window.run(1.1)
    assert services.effects.played.count('closing_doors.caf') == 1
    window.scene.did_move_to_view()
    window.run(1.1)
    assert services.effects.played.count('closing_doors.caf') == 1


def test_free_mode_loads_after_two_seconds_and_returns_to_the_menu():
    app, window, services = at_main_menu()
    menu = window.scene
    menu.menu_next()
    menu.menu_activate()
    assert services.effects.played[-1] == 'acceptButton.mp3'
    menu.menu_next()   # ignored while loading
    window.run(1.9)
    assert window.scene is menu
    window.run(0.2)
    assert isinstance(window.scene, FreeModeScene)
    window.scene.on_menu()
    assert window.scene is menu
    assert said(services)[-1] == 'Campaign, button'
