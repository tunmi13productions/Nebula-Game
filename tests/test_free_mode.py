import io
import os
import random
import re
import sys

import pytest

from nebula.game import rand
from nebula.game.free_mode import BASE_POOL, FreeModeScene
from nebula.game.services import Services
from nebula.save import SaveData

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINARY = os.path.join(ROOT, 'decompiled', 'ipa', 'Payload', 'BEPiDGame.app', 'BEPiDGame')
FRAME = 1 / 60


def run(scene, services, seconds):
    for _ in range(int(round(seconds / FRAME))):
        services.scheduler.update(FRAME)
        scene.step(FRAME)


def make(save=None):
    rand.seed(6)
    services = Services.silent('en')
    if save is not None:
        services.save = save
    calls = []
    scene = FreeModeScene(services, on_menu=lambda: calls.append('menu'), on_new_game=lambda: calls.append('new'))
    scene.did_move_to_view()
    return scene, services, calls


def test_countdown_then_start_then_first_enemy():
    scene, services, calls = make()
    run(scene, services, 0.9)
    assert services.voice.spoken == []
    run(scene, services, 3.2)
    assert [s[0] for s in services.voice.spoken] == ['3', '2', '1', 'Start!']
    assert not any(n.name == 'SpaceShip' and n is not scene.player for n in scene.children)
    run(scene, services, 0.6)
    enemies = [n for n in scene.children if n.name == 'SpaceShip' and n is not scene.player]
    assert len(enemies) == 1 and enemies[0].code in BASE_POOL[0:4]
    assert scene.time_between_power_ups == 60 and scene.power_up_type2 == 4


def test_kill_announces_the_score():
    scene, services, calls = make()
    run(scene, services, 5)
    enemy = next(n for n in scene.children if n.name == 'SpaceShip' and n is not scene.player)
    enemy.inflict_damage(1000)
    scene.destroy_enemy(enemy.code)
    scene.add_score(enemy)
    assert services.voice.spoken[-1][0] == 'Score: %d.' % enemy.score


def test_game_over_saves_the_best_score_and_offers_the_menu(tmp_path):
    save = SaveData(str(tmp_path / 'save.json'))
    scene, services, calls = make(save)
    scene.score_counter = 120
    scene.end_game()
    assert SaveData(str(tmp_path / 'save.json')).integer('bestScore') == 120
    assert services.voice.spoken[-1][0] == 'Game Over. You scored 120 points! Best score: 120 points. , Back to menu button'
    scene.menu_next()
    scene.menu_activate()
    assert calls == ['new']
    scene2, services2, _ = make(SaveData(str(tmp_path / 'save.json')))
    scene2.score_counter = 50
    scene2.end_game()
    assert SaveData(str(tmp_path / 'save.json')).integer('bestScore') == 120


@pytest.mark.skipif(not os.path.exists(BINARY), reason='original binary not unpacked')
def test_spawning_matches_the_original_in_the_emulator(monkeypatch):
    sys.path.insert(0, os.path.join(ROOT, 'tools', 're'))
    from objc_trace import Tracer, u32f

    buf = io.StringIO()
    t = Tracer(BINARY, out=buf)
    orig = t.new_object('FreeModeScene')
    t.send(orig, 'initWithSize:', u32f(320.0), u32f(568.0))
    t.skip_impl.update({'createEnemyWithType:', 'initBoss:onParentScene:'})
    rng_orig, rng_port = random.Random(11), random.Random(11)
    t.rand_source = lambda: rng_orig.getrandbits(32)
    monkeypatch.setattr(rand, 'arc4random', lambda: rng_port.getrandbits(32))

    services = Services.silent('en')
    port = FreeModeScene(services)
    port_log = []
    port.create_enemy_with_type = lambda code: port_log.append(('ship', code))
    port.spawn_boss = lambda code: port_log.append(('boss', code))

    def orig_spawns():
        out = []
        for line in buf.getvalue().splitlines():
            m = re.search(r'createEnemyWithType: (\d+)', line)
            if m:
                out.append(('ship', int(m.group(1))))
            m = re.search(r'initBoss:onParentScene: (\d+)', line)
            if m:
                out.append(('boss', int(m.group(1))))
        buf.seek(0)
        buf.truncate()
        return out

    buf.seek(0); buf.truncate()
    t.send(orig, 'createFirstEnemy')
    port.create_first_enemy()
    assert orig_spawns() == port_log
    alive = list(port_log)
    choose = random.Random(5)
    for _ in range(400):
        assert alive, 'nothing left to kill'
        kind, code = alive.pop(choose.randrange(len(alive)))
        code = 100 if kind == 'boss' else code
        before = len(port_log)
        t.send(orig, 'destroyEnemy:', code)
        port.destroy_enemy(code)
        new = port_log[before:]
        assert orig_spawns() == new, (code, new)
        alive.extend(new)
    bosses = [c for k, c in port_log if k == 'boss']
    assert len(bosses) >= 3 and bosses[0] == 2          # Boss 1 is skipped, as in the original
    assert port.fin_special > 5 and port.fin_base > 5    # both pools advanced
