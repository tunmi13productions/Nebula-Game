"""Runs the original ChapterNScene destroyEnemy: in the emulator from a given counter state and reports what it
did: ships spawned, power-ups released, the scene methods it ended in, and the counters afterwards.
Used by tests/test_chapters.py for differential testing of the port's kill rules."""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objc_trace import Tracer, u32f  # noqa: E402

COUNTERS = ('smallEnemy', 'mediumEnemy', 'laserEnemy', 'smallEnemyInScene', 'mediumEnemyInScene', 'laserEnemyInScene')
EXTRA = ('inocentCounter', 'releasedPowerUp', 'theEnd', 'remove')
SKIP = {'createEnemyWithType:', 'releasePowerUpOfType:', 'initPowerUpOfType:inParentScene:', 'initBoss:onParentScene:',
        'didBeginStage:onChapter:onMode:', 'didWinStage:onChapter:onMode:', 'didFailStage:onChapter:onMode:',
        'blockTouch:'}
# scene methods that end or redirect the stage; they're recorded and not run
TERMINAL = {'defaultVictoriousAnimation', 'endLvl', 'endGame', 'endStage1', 'endGameVictorious', 'enterGround',
            'endItAll', 'makePlayerTurnAround', 'stage4Loop', 'makeBossEntrance'}


class Oracle:
    def __init__(self, binary, chapter):
        self.buf = io.StringIO()
        t = self.t = Tracer(binary, out=self.buf)
        self.chapter = chapter
        s = self.scene = t.new_object('Chapter%dScene' % chapter)
        t.send(s, 'initWithSize:', u32f(320.0), u32f(568.0))
        t.send(s, 'setIsActive:', 1)
        ship = self.ship = t.new_object('SpaceShip')
        t.set_ivar(s, '_playerShip', ship)
        t.skip_impl.update(SKIP | TERMINAL)

    def ivars(self):
        return {k: self.t.get_ivar(self.scene, k) for k in COUNTERS + EXTRA if self._has(k)}

    def _has(self, k):
        try:
            self.t.ivar_offset(self.scene, k)
            return True
        except KeyError:
            return False

    def kill(self, stage, code, state, life=3, rand_value=None):
        t, s = self.t, self.scene
        t.send(s, 'setStageNumber:', stage)
        for k, v in state.items():
            if self._has(k):
                t.set_ivar(s, k, v)
        t.set_ivar(self.ship, 'spaceshipLife', life)
        if rand_value is not None:
            t.rand_value = rand_value
        first = len(t.blocks)
        self.buf.seek(0); self.buf.truncate()
        t.send(s, 'destroyEnemy:', code)
        log = self.buf.getvalue()
        return self.events(log, first), self.ivars()

    def events(self, log, first):
        out = []
        for line in log.splitlines():
            m = re.search(r'createEnemyWithType: (\d+)', line)
            if m:
                out.append(('spawn', int(m.group(1))))
                continue
            m = re.search(r'(?:releasePowerUpOfType:|initPowerUpOfType:inParentScene:) (\d+)', line)
            if m:
                out.append(('powerup', int(m.group(1))))
                continue
            m = re.search(r'Scene 0x[0-9a-f]+> (\w+)\s*(?:=>|$)', line)
            if m and m.group(1) in TERMINAL:
                out.append(('call', m.group(1)))
                continue
            m = re.search(r'performSelector:withObject:afterDelay: (\S+) \S+ ([\d.]+)', line)
            if m:
                out.append(('later', m.group(1).strip("'"), float(m.group(2))))
                continue
            if 'waitForDuration:' in line:
                m = re.search(r'waitForDuration: ([\d.]+)', line)
                out.append(('wait', float(m.group(1))))
        return out
