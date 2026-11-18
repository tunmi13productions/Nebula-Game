import pytest

from nebula.game import rand
from nebula.game.base_scene import BaseScene, H, W
from nebula.game.services import Services
from nebula.game.ship import DRIFTER_OFFSCREEN

FRAME = 1 / 60


class Recording(BaseScene):
    def __init__(self, services):
        self.destroyed = []
        super().__init__(services)

    def destroy_enemy(self, code):
        self.destroyed.append(code)


def make(seed=3):
    rand.seed(seed)
    services = Services.silent('en')
    scene = Recording(services)
    scene.did_move_to_view()
    return scene, services


def run(scene, services, seconds):
    for _ in range(int(round(seconds / FRAME))):
        services.scheduler.update(FRAME)
        scene.step(FRAME)


def engine(services, ship):
    return services.aureal.library.get(ship.sound_id)


def test_normal_enemy_enters_from_the_top_then_fights():
    scene, services = make()
    ship = scene.create_enemy_with_type(9)
    assert ship.position == pytest.approx((160.0, H + ship.ship_size[1]))
    snd = engine(services, ship)
    assert snd.linked is ship and services.audio.state[snd.handle]['loops'] == -1
    assert services.audio.state[snd.handle]['path'].endswith('Ship_10.mp3')
    run(scene, services, 1.6)
    x, y = ship.position
    assert ship.ship_size[0] - 1 <= x <= W - ship.ship_size[0] + 1
    assert H * 0.75 - 1 <= y <= H * 0.9 + 1
    assert ship.has_action('ShootingAction') and ship.has_action('MovingAction') and ship.physics is not None


def test_wandering_stays_in_the_upper_band():
    scene, services = make()
    ship = scene.create_enemy_with_type(12)   # moves every 0.3 s
    for _ in range(40):
        run(scene, services, 0.5)
        if ship.parent is None:
            break
        assert H * 0.7 - 1 <= ship.position[1] <= H + ship.ship_size[1] + 1


def test_laser_ship_parks_at_a_side_and_runs_its_laser_cycle():
    scene, services = make(seed=5)
    ship = scene.create_enemy_with_type(7)
    run(scene, services, 1.05)
    sw = ship.ship_size[0]
    assert ship.position[0] in (pytest.approx(int(sw * 1.8), abs=0.01), pytest.approx(int(W - sw * 1.8), abs=0.01))
    assert H * 0.8 - 1 <= ship.position[1] <= H * 0.85 + 1
    assert not ship.has_action('MovingAction')
    for _ in range(40):
        run(scene, services, 0.25)
        if ship.laser_active:
            break
    assert ship.laser_active
    paths = [st['path'] for st in services.audio.state.values()]
    assert any(p.endswith('Laser_Charge.caf') for p in paths)
    run(scene, services, 2.6)
    beam = ship.laser_body
    assert any(p.endswith('Laser_Firing.mp3') for p in (st['path'] for st in services.audio.state.values()))
    assert beam.physics is not None and beam.position[0] == pytest.approx(ship.position[0])
    assert beam.size == (6.0, 568.0)
    assert not any(isinstance(n, type(beam)) and n is not beam for n in scene.children)   # no bullets from lasers


def test_standing_in_a_laser_hurts_on_contact_and_every_second():
    scene, services = make(seed=5)
    ship = scene.create_enemy_with_type(5)    # damage 3
    scene.player.life = 30
    for _ in range(80):
        run(scene, services, 0.25)
        if ship.laser_active and ship.laser_body.physics is not None:
            break
    scene.player.position = (ship.position[0], scene.player.position[1])
    scene.current_max_accel_x = 0.0
    life0 = scene.player.life
    run(scene, services, 2.05)
    assert life0 - scene.player.life in (6, 9)


def test_rock_falls_and_reports_code_90_when_it_leaves():
    scene, services = make()
    scene.player.physics = None          # keep the rock from ramming the player on its way down
    rock = scene.create_enemy_with_type(48)
    run(scene, services, 1.6)
    assert rock.position[1] > H        # parked above the screen, then falling
    run(scene, services, 7.0)
    assert scene.destroyed == [DRIFTER_OFFSCREEN] and rock.parent is None
    run(scene, services, 0.2)
    assert rock.sound_id not in services.aureal.library


def test_fuel_tank_explodes_at_the_bottom_and_reports_itself():
    scene, services = make()
    scene.player.physics = None
    tank = scene.create_enemy_with_type(46)
    run(scene, services, 11.0)
    assert scene.destroyed == [46]
    assert any(st['path'].endswith(('explosion_1.caf', 'Explosion_.mp3', 'explosion.mp3')) for st in services.audio.state.values())


def test_allies_do_not_spin_but_rocks_do():
    scene, services = make()
    ally = scene.create_enemy_with_type(37)
    rock = scene.create_enemy_with_type(47)
    run(scene, services, 2.5)
    assert ally.rotation == 0.0 and rock.rotation != 0.0


def test_killing_a_ship_stops_its_engine():
    scene, services = make()
    ship = scene.create_enemy_with_type(0)
    run(scene, services, 1.6)
    handle = engine(services, ship).handle
    ship.inflict_damage(100)
    assert not services.audio.state[handle]['playing']


def test_random_helper_is_inclusive():
    rand.seed(1)
    values = {rand.between(-2, 2) for _ in range(500)}
    assert values == {-2, -1, 0, 1, 2}
