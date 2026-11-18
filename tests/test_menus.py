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


# tutorial selection


def open_tutorials(first_visit=False):
    app, window, services = at_main_menu()
    if not first_visit:
        services.save.set_integer('primeiraVez', 1)
    menu = window.scene
    menu.menu_next()
    menu.menu_next()
    menu.menu_activate()
    return app, window, services


def test_tutorial_selection_lists_the_six_tutorials_and_back():
    from nebula.menus.tutorial_selection import TutorialSelectionScreen
    app, window, services = open_tutorials()
    screen = window.scene
    assert isinstance(screen, TutorialSelectionScreen)
    for _ in range(7):
        screen.menu_next()
    assert said(services)[-7:] == ['MOVEMENT, button', 'ENEMIES, button', 'ATTACK, button', 'BATTLE, button',
                                   'BASIC, button', 'SPECIAL, button', 'BACK, button']


def test_choosing_a_tutorial_loads_it_and_select_tutorial_comes_back():
    from nebula.game.tutorial import TutorialScene
    app, window, services = open_tutorials()
    screen = window.scene
    screen.menu_next()
    screen.menu_activate()
    window.run(2.1)
    assert isinstance(window.scene, TutorialScene) and window.scene.tutorial_type == 2
    window.scene.on_next()
    assert window.scene.tutorial_type == 3 and services.save.get('tutorial') == '3'
    window.scene.on_select()
    assert window.scene is screen


def test_the_first_visit_starts_the_movement_tutorial():
    from nebula.game.tutorial import TutorialScene
    app, window, services = open_tutorials(first_visit=True)
    assert services.save.get('primeiraVez') == 1
    window.run(2.1)
    assert isinstance(window.scene, TutorialScene) and window.scene.tutorial_type == 1


def test_back_closes_the_doors_then_returns_to_the_main_menu():
    app, window, services = open_tutorials()
    window.scene.handle_key('escape')
    window.run(0.9)
    assert not isinstance(window.scene, MainMenuScreen)
    window.run(0.2)
    assert isinstance(window.scene, MainMenuScreen)


# campaign selector


class Spoken:
    """Records what the game voice is asked to say."""

    def __init__(self, services):
        self.lines = []
        voice = services.voice
        speak, speak_then = voice.speak, voice.speak_then

        def rec_speak(text, rate=0.55):
            self.lines.append(text)
            speak(text, rate)

        def rec_then(text, rate, pre, post, done):
            self.lines.append(text)
            speak_then(text, rate, pre, post, done)
        voice.speak, voice.speak_then = rec_speak, rec_then


def campaign(last_chapter=1, last_level=1):
    from nebula.menus.campaign import CampaignSelectScene
    app, window, services = at_main_menu()
    services.globals.last_chapter, services.globals.last_level = last_chapter, last_level
    spoken = Spoken(services)
    window.scene.menu_activate()
    window.run(2.1)
    assert isinstance(window.scene, CampaignSelectScene)
    return app, window, services, spoken


def test_campaign_opens_on_the_furthest_chapter_and_reads_its_items():
    app, window, services, spoken = campaign(2, 2)
    assert spoken.lines[-1] == 'Chapter 2: DIRECTION'
    for _ in range(5):
        window.scene.menu_next()
        window.run(4.0)
    assert spoken.lines[-5:] == ['Back', 'Level 1: The Coordinates', 'Level 2: The Path',
                                 'Level 3: Approximation, Locked', 'Level 4: Deception, Locked']
    window.scene.menu_next()
    assert services.effects.played[-1] == 'errorButton.mp3'


def test_campaign_ignores_input_until_the_item_is_spoken():
    app, window, services, spoken = campaign()
    window.scene.menu_next()
    window.scene.menu_next()
    assert window.scene.selection == 1


def test_campaign_changes_chapter_only_up_to_the_furthest():
    app, window, services, spoken = campaign(3, 1)
    scene = window.scene
    scene.handle_key('right')
    assert spoken.lines[-1] == 'Locked'
    window.run(0.5)
    scene.handle_key('left')
    window.run(1.1)
    assert scene.chapter == 2 and spoken.lines[-1].startswith('Chapter 2:')
    scene.handle_key('right')
    window.run(1.1)
    assert scene.chapter == 3 and spoken.lines[-1].startswith('Chapter 3:')


def test_going_back_from_chapter_one_leaves_to_the_main_menu():
    app, window, services, spoken = campaign()
    window.scene.handle_key('left')
    assert spoken.lines[-1] == 'Back'
    window.run(4.0)
    assert isinstance(window.scene, MainMenuScreen)


def test_a_locked_level_cannot_start():
    app, window, services, spoken = campaign(1, 1)
    scene = window.scene
    for _ in range(3):
        scene.menu_next()
        window.run(4.0)
    scene.menu_activate()
    assert services.effects.played[-1] == 'errorButton.mp3'


def test_choosing_a_level_says_its_name_then_starts_it():
    from nebula.game.chapters import ChapterScene
    app, window, services, spoken = campaign(1, 1)
    scene = window.scene
    scene.menu_next()
    window.run(4.0)
    scene.menu_next()
    window.run(4.0)
    scene.menu_activate()
    assert spoken.lines[-1] == 'The Beginning'
    window.run(4.0)
    assert isinstance(window.scene, ChapterScene) and window.scene.stage_number == 1
    assert (services.save.integer('capitulo'), services.save.integer('fase')) == (1, 1)


def test_select_level_returns_to_the_chapter_just_played():
    app, window, services, spoken = campaign(3, 1)
    services.save.set_integer('capitulo', 2)
    app.back_to_campaign()
    assert window.scene.chapter == 2


def test_a_newly_completed_chapter_awards_points():
    app, window, services, spoken = campaign(4, 1)
    services.save.set('ControleCapitulo', 'yes')
    services.globals.last_chapter = 5
    app.back_to_campaign()
    assert services.globals.win_points == 4 and services.save.integer('Win_Points') == 4
