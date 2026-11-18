"""MapGenerator: the backgrounds, their timers and their random draws."""
from nebula.game import rand
from nebula.game.chapters import CHAPTERS
from nebula.game.free_mode import FreeModeScene
from nebula.game.map_generator import MapGenerator
from nebula.game.services import Services

FRAME = 1 / 60


def test_arc4random_uniform_rejects_the_biased_low_values():
    values = iter([0, 5, 2 ** 32 - 1])
    saved = rand.arc4random
    rand.arc4random = lambda: next(values)
    try:
        # bound 3: (2**32 - 3) % 3 == 1, so 0 is redrawn and 5 % 3 is returned
        assert rand.arc4random_uniform(3) == 2
        assert rand.arc4random_uniform(1) == 0
    finally:
        rand.arc4random = saved


def test_free_mode_map_scrolls_and_places_its_first_detail_and_planet():
    services = Services.silent('en')
    scene = FreeModeScene(services)
    names = [n.texture for n in scene.children if getattr(n, 'texture', None)]
    assert names.count('starfieldBG') == 4
    assert any(t.startswith('MapDetails_') for t in names) and any(t.startswith('planet') for t in names)
    layer = [n for n in scene.children if getattr(n, 'texture', None) == 'starfieldBG' and n.z == 2][0]
    y = layer.position[1]
    for _ in range(40):
        services.scheduler.update(0.025)
    assert abs((y - layer.position[1]) - 40 * 568 / 800) < 1e-6     # 0.71 points a tick
    scene.stop_audio()
    assert scene.map.timers == []


def test_the_map_draws_from_the_game_random_numbers_in_the_original_order():
    services = Services.silent('en')
    drawn = []
    saved = rand.arc4random
    rand.arc4random = lambda: drawn.append(1) or 0x7FFFFFFF
    try:
        FreeModeScene(services)
    finally:
        rand.arc4random = saved
    # the first map detail (3 uniform draws) and the first planet (1 plain and 1 uniform draw)
    assert len(drawn) == 5


def test_every_chapter_stage_builds_its_map():
    for chapter in CHAPTERS:
        for stage in (1, 2, 3, 4):
            services = Services.silent('en')
            scene = CHAPTERS[chapter](services, stage=stage, play_intro=lambda c, done: None)
            scene.did_move_to_view()
            for _ in range(int(3 / FRAME)):
                services.scheduler.update(FRAME)
                scene.step(FRAME)
            assert isinstance(scene.map, MapGenerator)
            assert scene.background == (0.0, 0.0, 0.0)
            scene.stop_audio()
