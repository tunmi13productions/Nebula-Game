import io
import os
import random
import re
import sys

import pytest

from nebula.data import BOSSES
from nebula.game import rand
from nebula.game.base_scene import BaseScene, H, W
from nebula.game.boss import BOSS_CODE, Boss
from nebula.game.services import Services
from nebula.game.ship import Shot

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINARY = os.path.join(ROOT, 'decompiled', 'ipa', 'Payload', 'BEPiDGame.app', 'BEPiDGame')
FRAME = 1 / 60


class Recording(BaseScene):
    def __init__(self, services):
        self.destroyed = []
        super().__init__(services)

    def destroy_enemy(self, code):
        self.destroyed.append(code)


def make():
    rand.seed(8)
    services = Services.silent('en')
    scene = Recording(services)
    scene.did_move_to_view()
    return scene, services


def run(scene, services, seconds):
    for _ in range(int(round(seconds / FRAME))):
        services.scheduler.update(FRAME)
        scene.step(FRAME)


def test_boss_stats_match_the_original():
    expected = {1: (30, 1), 2: (50, 2), 3: (65, 3), 4: (70, 4), 5: (80, 5), 6: (120, 4), 7: (120, 4), 8: (120, 1),
                9: (180, 9), 10: (70, 4)}
    for code, (life, damage) in expected.items():
        assert (BOSSES[code]['life'], BOSSES[code]['damage'], BOSSES[code]['score']) == (life, damage, 1000)


def test_entrance_then_body_movement_and_attacks():
    scene, services = make()
    boss = scene.spawn_boss(3)
    assert boss.position == (160.0, 2 * H) and boss.physics is None
    run(scene, services, 5.0)
    assert boss.position == pytest.approx((160.0, H), abs=0.5)
    assert boss.physics is not None and boss.code == BOSS_CODE
    run(scene, services, 0.65)
    assert any(isinstance(n, Shot) and n.ship is boss for n in scene.children)
    x0 = boss.position[0]
    run(scene, services, 1.5)
    assert boss.position[0] > x0     # boss 3 sweeps right first


def test_boss_bullets_carry_a_positional_sound():
    scene, services = make()
    boss = scene.spawn_boss(2)
    run(scene, services, 6.1)
    bullets = [n for n in scene.children if isinstance(n, Shot) and n.ship is boss]
    assert bullets
    linked = [s for s in services.aureal.library.values() if s.linked in bullets]
    assert linked and services.audio.state[linked[0].handle]['path'].endswith('Enemy_Shot_1.caf')


def test_boss_laser_beam_is_a_child_column_that_hurts():
    scene, services = make()
    boss = scene.spawn_boss(6)
    scene.player.life = 30
    run(scene, services, 5.0)
    scene.player.position = (boss.position[0], scene.player.position[1])
    beam = None
    for _ in range(40):
        run(scene, services, 0.25)
        beam = next((c for c in boss.children if isinstance(c, Shot)), None)
        if beam is not None and beam.physics is not None:
            break
    assert beam is not None and beam.size == (W / 50, H)
    assert beam.position == pytest.approx((0.0, -141.0 - boss.size[1] / 2))
    life = scene.player.life
    for _ in range(int(1.1 / FRAME)):
        # stay in the beam's column: it moves with the boss
        scene.player.position = (boss.position[0] + beam.position[0], scene.player.position[1])
        scene.current_max_accel_x = 0.0
        run(scene, services, FRAME)
    assert scene.player.life < life


def test_killing_a_boss():
    scene, services = make()
    boss = scene.spawn_boss(1)
    run(scene, services, 5.1)
    services.globals.shot_points = 5
    for _ in range(4):
        hit = boss.inflict_damage(services.globals.get_shot())
    assert not hit
    assert boss.inflict_damage(6)
    run(scene, services, 0.6)
    assert services.effects.played[-3:] == ['explosion_1.caf', 'Explosion_.mp3', 'explosion.mp3']
    run(scene, services, 1.2)
    assert boss.parent is None


def test_boss_leaves_when_the_scene_ends():
    scene, services = make()
    boss = scene.spawn_boss(4)
    run(scene, services, 5.5)
    scene.is_active = False
    run(scene, services, 1.1)
    assert boss.parent is None


@pytest.mark.skipif(not os.path.exists(BINARY), reason='original binary not unpacked')
@pytest.mark.parametrize('code', list(range(1, 11)))
def test_attack_sequence_matches_the_original(code, monkeypatch):
    sys.path.insert(0, os.path.join(ROOT, 'tools', 're'))
    from objc_trace import Tracer, u32f
    buf = io.StringIO()
    t = Tracer(BINARY, out=buf)
    oscene = t.new_object('Chapter1Scene')
    t.send(oscene, 'initWithSize:', u32f(W), u32f(H))
    t.send(oscene, 'setIsActive:', 1)
    t.skip_impl.update({'shootingOnPosition:', 'laserShootOnPosition:', 'entranceAction', 'startingMove', 'defineBody'})
    oboss = t.new_object('Boss')
    first = len(t.blocks)
    t.send(oboss, 'initBoss:onParentScene:', code, oscene)
    t.pos[oboss] = (160.0, 568.0)
    attack = next(i for i, b in enumerate(t.blocks) if i >= first and b[2] == 'runBlock:')
    ro, rp = random.Random(code), random.Random(code)
    t.rand_source = lambda: ro.getrandbits(32)
    monkeypatch.setattr('nebula.game.boss.arc4random', lambda: rp.getrandbits(32))
    monkeypatch.setattr('nebula.game.rand.arc4random', lambda: rp.getrandbits(32))

    scene, services = make()
    boss = Boss(code, scene)
    boss.position = (160.0, 568.0)
    log = []
    boss.shoot_on_position = lambda x, y: log.append(('shot', x, y))
    boss.laser_shoot_on_position = lambda dx, dy: log.append(('laser', dx, dy))
    for _ in range(14):
        buf.seek(0); buf.truncate()
        t.run_block(attack)
        orig = []
        for line in buf.getvalue().splitlines():
            m = re.search(r'(shootingOnPosition|laserShootOnPosition): \(([-\d.e]+), ([-\d.e]+)\)', line)
            if m:
                orig.append(('shot' if m.group(1).startswith('shooting') else 'laser', float(m.group(2)), float(m.group(3))))
        log.clear()
        boss.attack_tick()
        assert [k for k, _, _ in log] == [k for k, _, _ in orig]
        for (_, x, y), (_, ox, oy) in zip(log, orig):
            assert (x, y) == pytest.approx((ox, oy), abs=0.02)
