"""The campaign chapters. The kill rules are compared with the original's destroyEnemy: running in the emulator,
both from random counter states and along whole simulated stages."""
import os
import random
import sys

import pytest

from nebula.game import rand
from nebula.game.chapters import CHAPTERS
from nebula.game.powerups import LIFE
from nebula.game.services import Services

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINARY = os.path.join(ROOT, 'decompiled', 'ipa', 'Payload', 'BEPiDGame.app', 'BEPiDGame')
FRAME = 1 / 60
needs_binary = pytest.mark.skipif(not os.path.exists(BINARY), reason='original binary not unpacked')

IVARS = {'small': 'smallEnemy', 'medium': 'mediumEnemy', 'laser': 'laserEnemy', 'small_in': 'smallEnemyInScene',
         'medium_in': 'mediumEnemyInScene', 'laser_in': 'laserEnemyInScene', 'inocent': 'inocentCounter'}
TERMINAL = {'default_victorious_animation': 'defaultVictoriousAnimation', 'end_lvl': 'endLvl', 'end_game': 'endGame',
            'end_stage1': 'endStage1', 'enter_ground': 'enterGround'}
DRIFTERS = {37, 38, 39, 50}   # allies and rocks: they can also leave the screen, which reports code 90


def make(chapter, stage=1):
    rand.seed(3)
    services = Services.silent('en')
    scene = CHAPTERS[chapter](services, stage=stage)
    return scene, services


def recorder(scene):
    """Replaces the scene's outward actions with a log, the way the oracle sees them."""
    log = []
    scene.create_enemy_with_type = lambda code: log.append(('spawn', code))
    scene.release_power_up = lambda kind: log.append(('powerup', kind))
    for py, objc in TERMINAL.items():
        if hasattr(scene, py):
            setattr(scene, py, (lambda name: lambda: log.append(('call', name)))(objc))
    return log


def state_of(scene):
    return {objc: getattr(scene, py) for py, objc in IVARS.items() if hasattr(scene, py)}


@pytest.fixture(scope='module')
def oracles():
    sys.path.insert(0, os.path.join(ROOT, 'tools', 're'))
    from chapter_oracle import Oracle
    return {c: Oracle(BINARY, c) for c in CHAPTERS}


def apply_deviations(chapter, stage, code, life, want, after):
    """Adjusts the original's outcome for the documented deviations in docs/DEVIATIONS.md."""
    if (chapter, stage, code) == (7, 1, 34) and life <= 4 and want == [('powerup', LIFE)]:
        # "Chapter 7 stage 1 softlock is fixed": the medium respawns even when the player is hurt.
        want.append(('spawn', 34))
        after['mediumEnemy'] += 1
        after['mediumEnemyInScene'] += 1


def kill_both(oracle, scene, log, code, seed):
    state = state_of(scene)
    ro, rp = random.Random(seed), random.Random(seed)
    oracle.t.rand_source = lambda: ro.getrandbits(32)
    want, after = oracle.kill(scene.stage_number, code, state, life=scene.player.life)
    want = [e for e in want if e[0] in ('spawn', 'powerup', 'call')]
    apply_deviations(scene.CHAPTER, scene.stage_number, code, scene.player.life, want, after)
    del log[:]
    saved = rand.arc4random
    rand.arc4random = lambda: rp.getrandbits(32)
    try:
        scene.destroy_enemy(code)
    finally:
        rand.arc4random = saved
    return want, after


def codes_of(chapter):
    return sorted({code for _, code in CHAPTERS[chapter].SPAWNS.values()} | {50, 90, 100, 1})


def random_state(rng):
    s = {}
    for py in ('small', 'medium', 'laser'):
        s[py] = rng.choice([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 19, 20, 21])
    for py in ('small_in', 'medium_in', 'laser_in'):
        s[py] = rng.choice([-1, 0, 0, 1, 1, 2, 3])
    s['inocent'] = rng.randint(0, 6)
    return s


@needs_binary
@pytest.mark.parametrize('chapter', sorted(CHAPTERS))
def test_kill_rules_match_the_original_from_random_states(chapter, oracles):
    rng = random.Random(chapter * 101)
    oracle = oracles[chapter]
    codes = codes_of(chapter)
    for i in range(700):
        scene, services = make(chapter, rng.randint(1, 4))
        log = recorder(scene)
        for k, v in random_state(rng).items():
            if hasattr(scene, k):
                setattr(scene, k, v)
        scene.player.life = rng.randint(1, 6)
        code = rng.choice(codes)
        want, after = kill_both(oracle, scene, log, code, seed=i)
        where = 'chapter %d stage %d code %d from %s' % (chapter, scene.stage_number, code, want)
        assert log == want, where
        assert state_of(scene) == {k: after[k] for k in state_of(scene)}, where


BOSS_STAGES = {(4, 1), (4, 3)}   # chapter 4 fights bosses in stages 1, 3 and 4


@needs_binary
@pytest.mark.parametrize('chapter, stage', [(c, s) for c in sorted(CHAPTERS) for s in (1, 2, 3) if (c, s) not in BOSS_STAGES])
def test_whole_stages_match_the_original(chapter, stage, oracles):
    """Plays a stage by killing random ships that are in the scene, comparing every kill with the original,
    until the stage ends."""
    rng = random.Random(chapter * 10 + stage)
    oracle = oracles[chapter]
    scene, services = make(chapter, stage)
    log = recorder(scene)
    scene.say = lambda key, pre=0.0, post=0.0, then=None: then and then()
    scene.later = lambda seconds, fn: fn()
    scene.player.life = 5
    scene.next_stage()
    alive = [code for kind, code in log if kind == 'spawn']
    ended = False
    for step in range(600):
        if not alive:
            break
        code = rng.choice(alive)
        alive.remove(code)
        reported = 90 if code in DRIFTERS and rng.random() < 0.5 else code
        want, after = kill_both(oracle, scene, log, reported, seed=step)
        where = 'chapter %d stage %d step %d code %d' % (chapter, stage, step, reported)
        assert log == want, where
        assert state_of(scene) == {k: after[k] for k in state_of(scene)}, where
        alive += [c for kind, c in log if kind == 'spawn']
        if any(kind == 'call' for kind, _ in log):
            ended = True
            break
    assert ended, 'chapter %d stage %d never ended; ships left: %s' % (chapter, stage, alive)


# behaviour


def run(scene, services, seconds):
    for _ in range(int(round(seconds / FRAME))):
        services.scheduler.update(FRAME)
        scene.step(FRAME)


def spoken(services):
    return [t for t in services.renderer.spoken] if hasattr(services.renderer, 'spoken') else []


def test_opening_speaks_then_spawns():
    scene, services = make(1, 3)
    scene.did_move_to_view()
    assert scene.small == 0
    run(scene, services, 8.0)
    assert (scene.small, scene.laser) == (1, 1)
    assert scene.allow_move and scene.allow_shoot


def test_stage_one_waits_for_the_intro_cutscene():
    services = Services.silent('en')
    started = []
    scene = CHAPTERS[1](services, stage=1, play_intro=lambda chapter, done: started.append((chapter, done)))
    scene.did_move_to_view()
    assert started and started[0][0] == 1
    assert not scene.allow_move
    started[0][1]()
    assert scene.allow_move


def test_victory_flies_off_and_opens_mission_complete_with_progress():
    scene, services = make(1, 2)
    services.globals.last_chapter, services.globals.last_level = 1, 2
    scene.did_move_to_view()
    scene.default_victorious_animation()
    assert not scene.allow_move
    run(scene, services, 6.9)
    assert not scene.in_menu
    run(scene, services, 2.3)
    assert scene.in_menu
    assert services.globals.last_level == 3
    assert services.save.get('Missao 3 Capitulo 1 Completa') is True
    assert services.save.integer('last_Level') == 3
    labels = [label for label, _ in scene.menu_items]
    assert labels == ['Select level button', 'Next level button']


def test_finishing_a_chapter_unlocks_the_next():
    scene, services = make(1, 4)
    g = services.globals
    g.last_chapter, g.last_level = 1, 4
    scene.mission_complete()
    assert (g.last_chapter, g.last_level) == (2, 1)
    assert services.save.get('ControleCapitulo') == 'yes'
    assert services.save.get('Missao 1 Capitulo 2 Completa') is True


def test_replaying_an_earlier_level_records_nothing():
    scene, services = make(1, 2)
    g = services.globals
    g.last_chapter, g.last_level = 3, 2
    scene.mission_complete()
    assert (g.last_chapter, g.last_level) == (3, 2)


def test_dying_opens_the_campaign_game_over_menu():
    scene, services = make(1, 2)
    scene.did_move_to_view()
    assert scene.player.inflict_damage(1000)
    scene._schedule_end_game()      # what a fatal hit does
    run(scene, services, 1.6)
    assert scene.in_menu and not scene.is_active
    assert [label for label, _ in scene.menu_items] == ['Select level button', 'New game button']


def test_boss_stage_spawns_the_boss_after_the_lines_and_the_approach():
    scene, services = make(1, 4)
    scene.did_move_to_view()
    assert not scene.allow_move
    run(scene, services, 30.0)
    assert scene.the_boss is not None and scene.the_boss.boss_code == 1
    assert scene.allow_move


def test_killing_the_boss_runs_end_lvl_once_and_docks():
    scene, services = make(1, 4)
    calls = []
    scene.end_game_victorious = lambda: calls.append('victory')
    scene.destroy_enemy(100)
    scene.destroy_enemy(100)
    run(scene, services, 16.5)
    assert calls == []
    run(scene, services, 1.0)
    assert calls == ['victory']


# chapter 2


def test_chapter2_end_lvl_speaks_then_flies_off_once():
    scene, services = make(2, 4)
    calls = []
    scene.default_victorious_animation = lambda: calls.append('victory')
    scene.destroy_enemy(100)
    scene.destroy_enemy(100)
    run(scene, services, 12.0)
    assert calls == ['victory']


# chapter 4


def test_chapter4_rocks_are_always_the_big_one():
    scene, services = make(4, 2)
    spawned = []
    scene.create_enemy_with_type = spawned.append
    for _ in range(20):
        scene.create_small()
    assert set(spawned) == {50}


# chapter 6


def test_chapter6_loses_on_the_fifth_ally():
    scene, services = make(6, 2)
    ended = []
    scene.end_game = lambda: ended.append(True)
    scene.medium = 3
    scene.medium_in = 3
    for _ in range(4):
        scene.destroy_enemy(38)
    assert not ended
    scene.destroy_enemy(38)
    assert ended


# chapter 7


def test_chapter7_stage1_can_be_won_when_hurt():
    """The original softlocked here (see docs/DEVIATIONS.md): with life 4 or less, no medium ever respawned."""
    scene, services = make(7, 1)
    log = recorder(scene)
    scene.say = lambda key, pre=0.0, post=0.0, then=None: then and then()
    scene.player.life = 3
    scene.next_stage()
    alive = [code for kind, code in log if kind == 'spawn']
    for _ in range(200):
        if any(kind == 'call' for kind, _ in log) or not alive:
            break
        code = alive.pop(0)
        del log[:]
        scene.destroy_enemy(code)
        alive += [c for kind, c in log if kind == 'spawn']
    assert ('call', 'defaultVictoriousAnimation') in log


# chapter 9


def test_chapter9_finale_reaches_mission_complete():
    scene, services = make(9, 4)
    services.globals.last_chapter, services.globals.last_level = 9, 4
    scene.did_move_to_view()
    scene.end_lvl()
    run(scene, services, 90.0)
    assert 'endingSound.mp3' in services.effects.played
    assert scene.in_menu
