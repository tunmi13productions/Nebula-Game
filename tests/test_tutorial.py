import pytest

from nebula.game import rand
from nebula.game.services import Services
from nebula.game.tutorial import TutorialScene

FRAME = 1 / 60


def make(section, life_points=5):
    rand.seed(4)
    services = Services.silent('en')
    services.globals.life_points = life_points
    calls = []
    scene = TutorialScene(services, tutorial_type=section,
                          on_select=lambda: calls.append('select'), on_next=lambda: calls.append('next'))
    scene.did_move_to_view()
    return scene, services, calls


def run(scene, services, seconds):
    for _ in range(int(round(seconds / FRAME))):
        services.scheduler.update(FRAME)
        scene.step(FRAME)


def lines(services):
    return [s[0] for s in services.voice.spoken]


def test_movement_section_plays_four_clips_then_frees_movement():
    scene, services, calls = make(1)
    assert not scene.allow_move and scene.talking_move
    run(scene, services, 120)
    assert scene.voice_player.played == ['tut_1.0_en.mp3', 'tut_1.1_en.mp3', 'tut_1.2_en.mp3', 'tut_1.3_en.mp3']
    assert scene.allow_move and not scene.allow_shoot


def test_escape_ends_the_tutorial_and_the_menu_works_like_the_original():
    scene, services, calls = make(1)
    run(scene, services, 2)
    scene.swipe_up()
    assert scene.in_menu and lines(services)[-1] == 'Tutorial Completed, Select tutorial button'
    scene.menu_previous()
    assert services.effects.played[-1] == 'errorButton.mp3'
    scene.menu_next()
    assert services.effects.played[-1] == 'chageButton.mp3' and lines(services)[-1] == 'Next tutorial button'
    scene.menu_next()
    assert services.effects.played[-1] == 'errorButton.mp3'
    scene.menu_activate()
    assert services.effects.played[-1] == 'acceptButton.mp3' and calls == ['next']


def test_last_section_next_goes_back_to_selection():
    scene, services, calls = make(6)
    scene.swipe_up()
    scene.menu_next()
    scene.menu_activate()
    assert calls == ['select']


def test_enemies_section_choreography():
    scene, services, calls = make(2)
    run(scene, services, 70)
    narration = scene.voice_player.played + [f for f in services.effects.played if f.startswith('tut_')]
    for clip in ('tut_2.0_en.mp3', 'tut_2.3_en.mp3', 'tut_2.4_en.mp3', 'tut_2.7_en.mp3'):
        assert clip in narration
    e = scene.first_enemy
    assert scene.allow_move and not scene.allow_shoot
    assert e.has_action('MovingAction') and e.has_action('ShootingAction')


def test_battle_section_enemy_is_invulnerable_and_power_ups_drop():
    scene, services, calls = make(4)
    drops = []
    original = scene.release_power_up
    scene.release_power_up = lambda kind: drops.append(kind) or original(kind)
    run(scene, services, 100)
    assert scene.first_enemy.receive_damage is False
    assert not scene.first_enemy.inflict_damage(1000)
    assert drops and set(drops) <= {3, 4}


def test_basic_section_after_the_laser_ship_is_three_fuel_tanks_without_a_gun():
    scene, services, calls = make(5, life_points=5)
    scene.player.receive_damage = False
    run(scene, services, 60)
    laser = scene.first_enemy
    assert laser.code == 7 and scene.allow_shoot
    laser.inflict_damage(1000)
    spawned = []
    original = scene.create_enemy_with_type
    scene.create_enemy_with_type = lambda code: spawned.append(code) or original(code)
    scene.destroy_enemy(7)
    assert not scene.allow_shoot
    run(scene, services, 120)
    tanks = [c for c in spawned if c == 46]
    assert 'tut_5.4_en.mp3' in scene.voice_player.played
    assert len(tanks) == 3 and scene.in_menu


def test_special_section_keeps_the_tut_6_2_mixup():
    scene, services, calls = make(6)
    run(scene, services, 400)
    played = scene.voice_player.played
    assert played[:4] == ['tut_6.0_en.mp3', 'tut_6.1_en.mp3', 'tut_6.0_en.mp3', 'tut_6.3_en.mp3']
    assert len(played) == 11


def test_dying_in_the_tutorial_shows_the_completion_menu_after_the_delay():
    scene, services, calls = make(3, life_points=0)
    scene.player.life = 1
    scene.player.inflict_damage(5)
    scene._schedule_end_game()
    run(scene, services, 1.6)
    assert scene.in_menu
