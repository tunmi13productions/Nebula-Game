import random

import pytest

from nebula.game.base_scene import BaseScene, H
from nebula.game.services import Services
from nebula.game.ship import SpaceShip
from nebula.input import KeyboardTilt

FRAME = 1 / 60


class Recording(BaseScene):
    def __init__(self, services, keys):
        self.destroyed, self.ended = [], []
        super().__init__(services, keys)

    def destroy_enemy(self, code):
        self.destroyed.append(code)

    def end_game(self):
        super().end_game()
        self.ended.append(self.time)


def make(shield_points=0, life_points=0):
    services = Services.silent('en')
    services.globals.shield_points = shield_points
    services.globals.life_points = life_points
    keys = KeyboardTilt(0.3)
    scene = Recording(services, keys)
    scene.did_move_to_view()
    return scene, services, keys


def run(scene, services, seconds):
    for _ in range(int(round(seconds / FRAME))):
        services.scheduler.update(FRAME)
        scene.step(FRAME)


def target(scene, code=9, x=160.0, y=450.0):
    ship = SpaceShip.enemy(code, scene, entrance=False)
    ship.position = (x, y)
    ship.set_physics_body_specs()
    scene.add_child(ship)
    return ship


def lines(services):
    return [s[0] for s in services.voice.spoken]


def test_one_shot_per_auto_fire_interval():
    scene, services, keys = make()
    run(scene, services, FRAME)
    assert scene.player_shoot() is not None
    assert scene.player_shoot() is None
    assert services.effects.played == ['PlayerGun.caf']
    run(scene, services, 1.0)
    assert scene.player_shoot() is not None


def test_player_shot_flies_off_the_top_in_one_second():
    scene, services, keys = make()
    run(scene, services, FRAME)
    shot = scene.player_shoot()
    assert shot.position[1] == pytest.approx(scene.player.position[1] * 1.2)
    run(scene, services, 1.0)
    assert shot.parent is None and shot.position[1] == pytest.approx(H + 20)


def test_enemy_bullet_hits_the_player_with_sound_and_speech():
    scene, services, keys = make()
    enemy = target(scene, code=9)
    bullet = enemy.fire_bullet()
    assert any(s.linked is bullet for s in services.aureal.library.values())
    run(scene, services, 1.5)
    assert 'player_hit.caf' in services.effects.played
    assert scene.player.life == 4
    assert 'Your life is 4' in lines(services)
    assert bullet.parent is None
    run(scene, services, 0.3)
    assert not any(s.linked is bullet for s in services.aureal.library.values())


def test_shield_absorbs_one_hit_each_whatever_the_damage():
    scene, services, keys = make(shield_points=2)
    heavy = target(scene, code=16)    # damage 12
    for _ in range(3):
        heavy.fire_bullet()
        run(scene, services, 1.6)
    run(scene, services, 1.6)   # the fatal third hit ends the stage 1.5 s later
    assert lines(services)[:2] == ['Your shield is 1', 'Shield Down.']
    assert scene.player.shield == 0 and scene.ended


def test_alarm_repeats_every_four_seconds_at_one_life():
    scene, services, keys = make()
    scene.player.life = 2
    scene.player.inflict_damage(1)
    run(scene, services, 8.5)
    assert services.effects.played.count('alarm.caf') == 3
    scene.player.restore_life()
    run(scene, services, 8.0)
    assert services.effects.played.count('alarm.caf') == 3


def test_half_health_line_also_fires_for_the_player():
    scene, services, keys = make(life_points=1)   # 10 life
    scene.player.inflict_damage(5)
    assert lines(services)[0] == 'Enemy with less than 50% health.'


def test_near_miss_plays_the_side_whoosh():
    scene, services, keys = make()
    px, py = scene.player.position
    w = scene.player.ship_size[0]
    left = target(scene, code=9, x=px - w * 0.5 - w * 0.35, y=400)
    left.receive_damage = False
    left.fire_bullet()
    run(scene, services, 1.6)
    assert 'Swoosh_Left.caf' in services.effects.played
    assert 'player_hit.caf' not in services.effects.played


def test_shots_colliding():
    scene, services, keys = make()
    run(scene, services, FRAME)
    enemy = target(scene, code=9, x=160, y=560)
    enemy.receive_damage = False
    enemy.physics = None
    enemy.fire_bullet()
    run(scene, services, 0.3)
    scene.player_shoot()
    run(scene, services, 1.0)
    assert 'colisaoTiro.mp3' in services.effects.played


def test_killing_an_enemy():
    random.seed(1)
    scene, services, keys = make()
    services.globals.shot_points = 5     # 6 damage
    enemy = target(scene, code=0, x=160, y=300)   # life 2
    run(scene, services, FRAME)
    scene.player_shoot()
    run(scene, services, 0.5)
    assert 'enemy_hit.caf' in services.effects.played
    assert scene.destroyed == [0] and enemy.physics is None
    run(scene, services, 1.0)
    assert scene.score_counter == 10 and scene.death_counter == 1


def test_death_stops_movement_and_ends_the_stage_after_a_delay():
    scene, services, keys = make()
    scene.player.life = 1
    enemy = target(scene, code=16)
    enemy.fire_bullet()
    run(scene, services, 1.5)
    assert not scene.allow_move and scene.ended == []
    run(scene, services, 1.6)
    assert len(scene.ended) == 1 and not scene.is_active
