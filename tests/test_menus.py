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
    app = App(window, services, None, open_url=lambda url: opened.append(url))
    app.opened = opened = []
    return app, window, services


def at_main_menu(first_launch=False):
    app, window, services = make_app()
    if not first_launch:
        services.save.set_integer('primeiraVez', 1)
    app.open_main_menu()
    return app, window, services


def said(services):
    return services.screen_reader.said


def test_startup_speaks_the_headphones_notice_then_thunder_then_opens_the_menu():
    app, window, services = make_app()
    services.save.set_integer('primeiraVez', 1)
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
    for _ in range(7):
        menu.menu_next()
    assert said(services) == ['Campaign, button', 'Free Mode, button', 'Tutorial, button', 'Systems, button',
                              'Hangar, button', 'About, button']   # Systems is a port addition
    menu.menu_previous()
    assert said(services)[-1] == 'Hangar, button'


def test_main_menu_plays_the_doors_once_and_resets_chapter_control():
    app, window, services = at_main_menu()
    services.save.set('ControleCapitulo', 'yes')
    window.scene.did_move_to_view()
    assert services.save.get('ControleCapitulo') == 'no'
    window.run(1.9)
    assert 'closing_doors.caf' not in services.effects.played
    window.run(0.2)
    assert services.effects.played.count('closing_doors.caf') == 1
    window.scene.did_move_to_view()
    window.run(2.1)
    assert services.effects.played.count('closing_doors.caf') == 1


def test_menu_music_starts_after_the_opening_and_stops_for_gameplay():
    app, window, services = at_main_menu()
    window.run(3.3)
    assert app.menu_music is None
    window.run(0.2)
    music = app.menu_music
    assert music.playing and services.audio.state[music.handle]['loops'] == -1
    app.open_free_mode()
    assert not music.playing
    app.back_to_screen()
    assert music.playing


def test_first_launch_alert_and_its_buttons():
    from nebula.menus.main_menu import TutorialAlert
    from nebula.menus.tutorial_selection import TutorialSelectionScreen
    app, window, services = at_main_menu(first_launch=True)
    window.run(3.5)
    assert isinstance(window.scene, TutorialAlert)
    assert said(services)[-1] == ('Welcome, beginner!, For a better game experience, consider playing the basic '
                                  'tutorial., Go to tutorial, button')
    window.scene.menu_next()
    window.scene.menu_activate()
    assert isinstance(window.scene, MainMenuScreen) and services.save.get('primeiraVez') == 1
    assert said(services)[-1] == 'Campaign, button'
    app2, window2, services2 = at_main_menu(first_launch=True)
    window2.run(3.5)
    window2.scene.menu_activate()
    assert isinstance(window2.scene, TutorialSelectionScreen)


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
    app, window, services = at_main_menu(first_launch=first_visit)
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
    assert said(services)[-7:] == ['BACK, button', 'MOVEMENT, button', 'ENEMIES, button', 'ATTACK, button',
                                   'BATTLE, button', 'BASIC, button', 'SPECIAL, button']


def test_choosing_a_tutorial_loads_it_and_select_tutorial_comes_back():
    from nebula.game.tutorial import TutorialScene
    app, window, services = open_tutorials()
    screen = window.scene
    screen.menu_next()
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


def test_campaign_moving_on_cuts_off_the_item_being_read():
    app, window, services, spoken = campaign(2, 4)
    window.scene.menu_next()
    window.scene.menu_next()
    assert window.scene.selection == 2
    assert spoken.lines[-2:] == ['Back', 'Level 1: The Coordinates']


def test_campaign_control_silences_and_unlocks():
    app, window, services, spoken = campaign(2, 4)
    window.scene.menu_next()
    assert window.scene.swiping
    window.scene.handle_key('control')
    assert not window.scene.swiping and not services.voice.speaking
    window.scene.handle_key('left')
    window.run(1.1)
    assert window.scene.chapter == 1


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


# Hangar


def open_hangar(points=3):
    from nebula.menus.hangar import HangarScreen
    app, window, services = at_main_menu()
    services.globals.win_points = points
    for _ in range(4):
        window.scene.menu_next()
    window.scene.menu_activate()
    assert isinstance(window.scene, HangarScreen)
    return app, window, services


def test_hangar_reads_back_the_points_and_each_stat():
    app, window, services = open_hangar()
    for _ in range(4):
        window.scene.menu_next()
    assert said(services)[-5:] == ['BACK, button', '3 AVAILABLE POINTS', 'Life, 0 points',
                                   'Life, 0 points. 3 available points. Add points., button', 'Shield, 0 points']


def test_adding_a_point_spends_it_and_saves():
    app, window, services = open_hangar(1)
    screen = window.scene
    for _ in range(3):
        screen.menu_next()
    screen.menu_activate()
    g = services.globals
    assert (g.life_points, g.win_points) == (1, 0)
    assert services.save.integer('Life_Points') == 1 and services.save.integer('Win_Points') == 0
    assert services.effects.played[-1] == 'acceptButton.mp3'
    # with no points left the plus buttons leave the reading order
    screen.menu_next()
    assert said(services)[-1] == 'Shield, 0 points'
    screen.menu_previous()
    assert said(services)[-1] == 'Life, 1 points'


def test_a_full_stat_hides_its_plus_button():
    app, window, services = open_hangar(2)
    services.globals.life_points = 5
    screen = window.scene
    for _ in range(3):
        screen.menu_next()
    assert said(services)[-1] == 'Shield, 0 points'


def test_hangar_after_a_new_chapter_returns_to_the_campaign():
    from nebula.menus.campaign import CampaignSelectScene
    from nebula.menus.hangar import HangarScreen
    app, window, services = at_main_menu()
    services.globals.last_chapter = 2
    services.save.set('ControleCapitulo', 'yes')
    app.back_to_campaign()
    assert isinstance(window.scene, HangarScreen)
    assert said(services)[-1] == 'BACK, button'
    window.scene.menu_activate()
    window.run(1.1)
    assert isinstance(window.scene, CampaignSelectScene)
    assert services.save.get('ControleCapitulo') == 'no'
    window.scene.did_swipe_up()
    window.run(4.0)
    assert isinstance(window.scene, MainMenuScreen)


# About


def open_about():
    from nebula.menus.about import AboutScreen
    app, window, services = at_main_menu()
    for _ in range(5):
        window.scene.menu_next()
    window.scene.menu_activate()
    assert isinstance(window.scene, AboutScreen)
    return app, window, services


def test_about_reads_its_elements_in_screen_order():
    app, window, services = open_about()
    for _ in range(4):
        window.scene.menu_next()
    assert said(services)[-4:] == ['BACK, button', 'About', 'CREDITS, button',
                                   'GRAY COMPANY © All Rights Reserved']


def test_credits_swap_in_and_their_sources_open():
    app, window, services = open_about()
    screen = window.scene
    screen.menu_next()
    screen.menu_next()
    screen.menu_activate()
    for _ in range(9):
        screen.menu_next()
    assert said(services)[-9:] == [' DEVELOPERS', 'Bruno Moreira', 'Diego Pereira', 'Felipe Delazeri',
                                   'Leonardo Gubert', 'Lucas Carletti', ' SOUND DESIGN', 'FreeSFX, button',
                                   'OpenGameArt, button']
    screen.menu_activate()
    assert app.opened == ['http://opengameart.org']
    for _ in range(20):
        screen.menu_next()
    assert said(services)[-2:] == ['Ricardo Rauber', 'GRAY COMPANY © All Rights Reserved']


def test_campaign_keys_during_a_chapter_slide_finish_it_and_act():
    app, window, services, spoken = campaign(3, 1)
    scene = window.scene
    scene.handle_key('left')
    window.run(0.3)
    scene.menu_next()                       # finishes the slide, then moves to Back
    assert scene.chapter == 2 and scene.selection == 1
    scene.menu_activate()
    window.run(4.0)
    assert isinstance(window.scene, MainMenuScreen)


def test_campaign_escape_during_a_slide_leaves():
    app, window, services, spoken = campaign(3, 1)
    window.scene.handle_key('left')
    window.run(0.3)
    window.scene.handle_key('escape')
    window.run(4.0)
    assert isinstance(window.scene, MainMenuScreen)


def test_campaign_back_is_not_restarted_by_more_presses():
    app, window, services, spoken = campaign(2, 4)
    scene = window.scene
    scene.menu_next()
    window.run(3.0)
    scene.menu_activate()
    for _ in range(5):
        window.run(0.2)
        scene.menu_activate()
        scene.handle_key('escape')
    assert spoken.lines.count('Back') == 2      # the item, then the one goodbye
    window.run(2.0)
    assert isinstance(window.scene, MainMenuScreen)


def test_screens_draw_their_pictures():
    import pygame
    from nebula.render.renderer import Renderer
    from nebula.render.textures import TextureStore
    app, window, services = at_main_menu()
    window.run(3.0)
    textures = {n.texture for n in window.scene.view.walk() if getattr(n, 'texture', None)}
    assert {'nebulaMenu1', 'leftDoor_en_4', 'rightDoorSystems_en_4'} <= textures
    surface = pygame.Surface((320, 568))
    window.scene.draw(surface, Renderer(TextureStore(), 1.0))
    window.scene.menu_activate()
    assert any(n.name == 'loading' for n in window.scene.view.children)


def test_campaign_spells_its_chapter_in_letter_pictures():
    from nebula.menus.view import glyph_name
    app, window, services, spoken = campaign(2, 2)
    textures = {n.texture for n in window.scene.view.walk() if getattr(n, 'texture', None)}
    assert 'portaLisaCampanha' in textures and 'AlfabetoAct_D' in textures   # DIRECTION, unlocked
    assert any(t.startswith('Alfabeto_') for t in textures)                    # the locked levels
    assert glyph_name('\u00e3', True) == 'AlfabetoAct_A\u2560\u00e2'          # a with tilde
