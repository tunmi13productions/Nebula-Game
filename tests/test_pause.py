"""The pause menu (callPause): swipe up, which is Escape here."""
from nebula.game.chapters import CHAPTERS
from nebula.game.free_mode import FreeModeScene
from nebula.game.services import Services

FRAME = 1 / 60


def run(scene, services, seconds):
    for _ in range(int(round(seconds / FRAME))):
        services.scheduler.update(FRAME)
        scene.step(FRAME)


def chapter(calls):
    services = Services.silent('en')
    scene = CHAPTERS[1](services, stage=2, on_select=lambda: calls.append('select'),
                        on_restart=lambda: calls.append('restart'))
    scene.did_move_to_view()
    return scene, services


def test_pause_speaks_the_title_and_first_item_and_freezes_the_scene():
    calls = []
    scene, services = chapter(calls)
    run(scene, services, 1.0)
    scene.swipe_up()
    assert services.voice.spoken[-1][0] == 'Game paused, Continue, button'
    assert scene.in_menu and scene.game_paused and scene.paused
    before = scene.time
    run(scene, services, 1.0)
    assert scene.time == before
    scene.swipe_up()                  # ignored while paused
    assert scene.menu_selection == 1


def test_continue_resumes():
    calls = []
    scene, services = chapter(calls)
    scene.swipe_up()
    scene.menu_activate()
    assert not (scene.in_menu or scene.game_paused or scene.paused)
    assert services.effects.played[-1] == 'acceptButton.mp3'
    assert not services.voice.should_pause


def test_restart_and_leave():
    calls = []
    scene, services = chapter(calls)
    scene.swipe_up()
    scene.menu_next()
    assert services.voice.spoken[-1][0] == 'Restart, button'
    scene.menu_activate()
    scene2, services2 = chapter(calls)
    scene2.swipe_up()
    scene2.menu_next()
    scene2.menu_next()
    assert services2.voice.spoken[-1][0] == 'Leave game, button'
    scene2.menu_activate()
    assert calls == ['restart', 'select']
    assert not services2.voice.should_pause


def test_no_pause_on_an_end_screen():
    calls = []
    scene, services = chapter(calls)
    scene.mission_complete()
    scene.menu_activate()            # the menu closes, the end screen stays
    scene.in_menu = False
    scene.swipe_up()
    assert not scene.game_paused


def test_free_mode_pause_leaves_to_the_menu():
    services = Services.silent('en')
    calls = []
    scene = FreeModeScene(services, on_menu=lambda: calls.append('menu'), on_new_game=lambda: calls.append('new'))
    scene.did_move_to_view()
    scene.swipe_up()
    scene.menu_next()
    scene.menu_next()
    scene.menu_activate()
    assert calls == ['menu']


def test_control_silences_an_open_menu_but_not_play():
    calls = []
    scene, services = chapter(calls)
    scene.services.voice.speak('a long line of play speech')
    scene.handle_key('control')
    assert services.voice.speaking          # during play nothing is cut
    scene.swipe_up()
    scene.handle_key('control')
    assert not services.voice.speaking


def test_home_and_end_in_the_pause_menu():
    scene, services = chapter([])
    run(scene, services, 1.0)
    scene.swipe_up()
    count = len(scene.menu_items)
    scene.menu_last()
    assert scene.menu_selection == count
    assert services.voice.spoken[-1][0] == scene.menu_items[-1][0]
    scene.menu_last()
    assert services.effects.played[-1] == 'errorButton.mp3'
    scene.menu_first()
    assert scene.menu_selection == 1
    assert services.voice.spoken[-1][0] == scene.menu_items[0][0]


def test_control_in_the_pause_menu_keeps_a_line_s_follow_up():
    scene, services = chapter([])
    run(scene, services, 1.0)
    done = []
    services.voice.speak_then('Commander, enemies ahead.', 0.55, 0.0, 0.0, lambda: done.append(True))
    scene.swipe_up()
    scene.handle_key('control')
    scene.menu_activate()                    # Continue
    run(scene, services, 3.0)
    assert done == [True]
