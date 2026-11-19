"""The chapter intro cutscenes."""
from nebula.game.chapters import CHAPTERS
from nebula.game.cutscene import CutScene, roman
from nebula.game.services import Services

FRAME = 1 / 30


def run(services, seconds, scene=None):
    for _ in range(int(round(seconds / FRAME))):
        services.scheduler.update(FRAME)
        if scene is not None:
            scene.step(FRAME)


def test_roman_numerals():
    assert [roman(n) for n in (1, 4, 5, 9)] == ['I', 'IV', 'V', 'IX']


def test_title_card_then_the_narration_in_order_then_the_completion():
    services = Services.silent('en')
    done = []
    cs = CutScene(services, 2, lambda: done.append(True))
    cs.start()
    assert services.screen_reader.said == ['Chapter II, DIRECTION']
    assert services.effects.played == ['Deep_Impact_3.mp3']
    run(services, 6.9)
    assert cs.player.played == []
    run(services, 0.2)
    assert cs.player.played == ['chapter2_part1_en.mp3']
    run(services, 600)
    assert cs.player.played == ['chapter2_part1_en.mp3', 'chapter2_part2_en.mp3']
    assert done == [True]


def test_spoken_parts_use_the_game_voice():
    services = Services.silent('en')
    done = []
    cs = CutScene(services, 8, lambda: done.append(True))
    cs.start()
    run(services, 600)
    lines = [line[0] for line in services.voice.spoken]
    assert lines == ['Sending message.', 'Message sent.']
    assert cs.player.played == ['chapter8_part2_en.mp3']
    assert done == [True]


def test_skip_stops_and_completes_at_once():
    services = Services.silent('en')
    done = []
    cs = CutScene(services, 1, lambda: done.append(True))
    cs.start()
    run(services, 8.0)
    cs.skip()
    assert done == [True]
    run(services, 600)
    assert done == [True] and cs.player.played == ['chapter1_part1_en.mp3']


def test_stage_one_plays_the_intro_and_space_skips_it():
    services = Services.silent('en')
    scene = CHAPTERS[3](services, stage=1)
    scene.did_move_to_view()
    run(services, 3.0, scene)
    assert scene.cutscene_running() and not scene.allow_move
    scene.player_shoot()
    assert not scene.cutscene_running()
    assert scene.allow_move


def test_cutscene_pictures_follow_the_narration_and_leave_with_it():
    services = Services.silent('en')
    scene = CHAPTERS[2](services, stage=1)
    scene.did_move_to_view()
    run(services, 7.2, scene)
    pictures = [n.texture for n in scene.cutscene.view.root.walk() if getattr(n, 'texture', None)]
    assert 'shipInterior1.jpg' in pictures
    scene.player_shoot()                     # skip
    assert scene.cutscene.view.root.parent is None
