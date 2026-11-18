import pytest

from nebula.game.base_scene import BaseScene, H, RIGHT, STOPPED, W
from nebula.game.services import Services
from nebula.input import KeyboardTilt

FRAME = 1 / 60


def make(talking=False):
    services = Services.silent('en')
    keys = KeyboardTilt(0.3)
    scene = BaseScene(services, keys)
    scene.talking_move = talking
    return scene, services, keys


def run(scene, services, seconds):
    for _ in range(int(round(seconds / FRAME))):
        services.scheduler.update(FRAME)
        scene.step(FRAME)


def test_player_starts_where_the_original_puts_it():
    scene, services, keys = make()
    w = W / 4.5
    assert scene.player.position == pytest.approx((160.0, w + H / 3 * 0.17))
    assert services.aureal.listener == pytest.approx(scene.player.position, abs=0.01)
    assert services.aureal.max_distance == pytest.approx(710.0)


def test_holding_right_moves_at_accel_times_w_over_speed_per_frame():
    scene, services, keys = make()
    keys.right = True
    run(scene, services, 0.2)        # the first accelerometer sample lands at 0.2 s
    x0 = scene.player.position[0]
    run(scene, services, 0.5)
    assert scene.movement_state == RIGHT
    assert scene.player.position[0] - x0 == pytest.approx(0.3 * (W / 50) * 30, abs=0.5)
    assert services.aureal.listener[0] == pytest.approx(scene.player.position[0])


def test_movement_clamps_half_a_ship_from_the_edges():
    scene, services, keys = make()
    keys.left = True
    run(scene, services, 6.0)
    assert scene.player.position[0] == pytest.approx(W / 4.5 / 2)


def test_dead_zone_and_release():
    scene, services, keys = make()
    keys.tilt = 0.03
    keys.right = True
    run(scene, services, 1.0)
    assert scene.player.position[0] == pytest.approx(160.0) and scene.movement_state == STOPPED
    keys.tilt = 0.3
    run(scene, services, 0.4)
    keys.right = False
    run(scene, services, 0.4)
    assert scene.movement_state == STOPPED


def test_edge_plays_the_boundary_sound_once_per_touch():
    scene, services, keys = make()
    keys.left = True
    run(scene, services, 6.0)
    assert services.effects.played == ['bound_left.mp3']
    keys.left, keys.right = False, True
    run(scene, services, 1.5)
    keys.left, keys.right = True, False
    run(scene, services, 3.0)
    assert services.effects.played == ['bound_left.mp3', 'bound_left.mp3']
    keys.left, keys.right = False, True
    run(scene, services, 8.0)
    assert services.effects.played[-1] == 'bound_right.mp3'


def test_talking_movement_announces_changes_and_the_edge():
    scene, services, keys = make(talking=True)
    run(scene, services, 1.2)
    keys.right = True
    run(scene, services, 0.5)   # short enough to stay clear of the right wall
    keys.right = False
    run(scene, services, 1.0)
    keys.left = True
    run(scene, services, 6.0)
    lines = [s[0] for s in services.voice.spoken]
    assert lines[:3] == ['Right', 'Stopped', 'Left']
    assert 'End of Screen' in lines


def test_no_movement_talk_unless_enabled():
    scene, services, keys = make(talking=False)
    keys.right = True
    run(scene, services, 3.0)
    assert services.voice.spoken == []


def test_speak_life():
    scene, services, keys = make()
    scene.speak_life()
    run(scene, services, 0.1)
    assert services.voice.spoken[0][:2] == ('Your life is 5', 0.55)


def test_shift_steers_twice_as_fast():
    from nebula.input import KeyboardTilt
    keys = KeyboardTilt()
    keys.right = True
    assert keys() == 0.3
    keys.fast = True
    assert keys() == 0.6
    keys.right, keys.left = False, True
    assert keys() == -0.6
