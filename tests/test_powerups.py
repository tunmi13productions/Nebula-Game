import pytest

from nebula.game import rand
from nebula.game.base_scene import BaseScene, H, W
from nebula.game.powerups import FAST_SHOT, LIFE, SHIELD, SPEED, PowerUp
from nebula.game.services import Services

FRAME = 1 / 60


def make(shield_points=0):
    rand.seed(2)
    services = Services.silent('en')
    services.globals.shield_points = shield_points
    scene = BaseScene(services)
    scene.did_move_to_view()
    return scene, services


def run(scene, services, seconds):
    for _ in range(int(round(seconds / FRAME))):
        services.scheduler.update(FRAME)
        scene.step(FRAME)


def lines(services):
    return [s[0] for s in services.voice.spoken]


def beep_for(services, p):
    return next(s for s in services.aureal.library.values() if s.linked is p)


def test_power_up_drifts_down_with_a_radar_beep_and_leaves_after_ten_seconds():
    scene, services = make()
    scene.player.physics = None
    p = scene.release_power_up(LIFE)
    assert 50 <= p.position[0] <= W - 50 and p.position[1] == H
    beep = beep_for(services, p)
    assert services.audio.state[beep.handle]['path'].endswith('beep_radar.caf')
    assert services.audio.state[beep.handle]['loops'] == -1
    run(scene, services, 10.2)
    assert p.parent is None
    assert not services.audio.state.get(beep.handle, {'playing': False})['playing']


def test_collecting_life_and_shield():
    scene, services = make(shield_points=2)
    scene.player.life = 3
    scene.player.shield = 0
    scene.collect_power_up(PowerUp(LIFE, scene))
    scene.collect_power_up(PowerUp(SHIELD, scene))
    run(scene, services, 0.1)
    assert scene.player.life == 4 and scene.player.shield == 1
    assert services.effects.played.count('Power-Up.caf') == 2
    assert 'Life collected!' in lines(services) or 'Your life is 4' in lines(services)


def test_shield_cube_does_nothing_without_shield_upgrades():
    scene, services = make(shield_points=0)
    scene.collect_power_up(PowerUp(SHIELD, scene))
    assert scene.player.shield == 0 and scene.player.max_shield == 0


def test_speed_lasts_ten_seconds():
    scene, services = make()
    scene.collect_power_up(PowerUp(SPEED, scene))
    assert scene.velocidade == pytest.approx(W / 10)
    run(scene, services, 10.0)
    assert scene.velocidade == pytest.approx(W / 10)
    run(scene, services, 0.5)
    assert scene.velocidade == pytest.approx(W / 50)
    assert 'SpeedUp ended' in lines(services)


def test_fast_shot_lifts_the_fire_limit_for_ten_seconds():
    scene, services = make()
    run(scene, services, FRAME)
    scene.player_shoot()
    assert scene.player_shoot() is None
    scene.collect_power_up(PowerUp(FAST_SHOT, scene))
    assert scene.player_shoot() is not None and scene.player_shoot() is not None
    run(scene, services, 10.5)
    assert not scene.power_up_shot and 'Fast shooting ended' in lines(services)


def test_touching_a_power_up_collects_it():
    scene, services = make()
    p = scene.release_power_up(LIFE)
    p.remove_all_actions()
    p.position = scene.player.position
    run(scene, services, 2 * FRAME)
    assert p.parent is None and 'Power-Up.caf' in services.effects.played


def test_timed_drops_follow_the_base_loop():
    scene, services = make()
    scene.player.physics = None
    scene.time_between_power_ups, scene.time_to_next_power_up = 60, 60
    scene.power_up_type1, scene.power_up_type2 = 1, 4
    drops = []
    original = scene.release_power_up
    scene.release_power_up = lambda kind: drops.append((round(scene.time), kind)) or original(kind)
    run(scene, services, 200.0)
    assert drops[0][0] in (60, 61)
    gap = drops[1][0] - drops[0][0]
    assert 60 <= gap <= 121
    assert all(1 <= k <= 4 for _, k in drops)
