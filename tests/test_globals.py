"""Global init and savePoints: the save keys and defaults of the original."""
from nebula.game.globals import GlobalState
from nebula.save import SaveData


def test_a_fresh_save_starts_at_chapter_one_and_records_it():
    save = SaveData.in_memory()
    g = GlobalState.load(save)
    assert (g.last_chapter, g.last_level) == (1, 1)
    assert (save.integer('last_Chapter'), save.integer('last_Level')) == (1, 1)
    assert (g.life_points, g.win_points) == (0, 0)


def test_points_and_progress_round_trip_with_the_original_keys():
    save = SaveData.in_memory()
    g = GlobalState.load(save)
    g.shot_points, g.time_shot_points, g.life_points = 1, 2, 3
    g.shield_points, g.speed_points, g.win_points = 4, 5, 6
    g.last_chapter, g.last_level = 3, 2
    g.save_points(save)
    g.save_progress(save)
    assert save.integer('Shild_Points') == 4 and save.integer('TimeShoot_Points') == 2
    h = GlobalState.load(save)
    assert (h.shot_points, h.time_shot_points, h.life_points, h.shield_points, h.speed_points, h.win_points) == \
        (1, 2, 3, 4, 5, 6)
    assert (h.last_chapter, h.last_level) == (3, 2)
