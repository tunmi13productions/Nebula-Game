# Traces a tutorial section: runs TutorialScene tutorialN in the emulator with audio playback mocked,
# then runs every captured block in order (audio completions, delays, waits for player actions).
# usage: python tools/re/trace_tutorial.py <section 1-6>
import sys, io
sys.path.insert(0, 'tools/re')
from objc_trace import Tracer, u32f
n = int(sys.argv[1])
buf = io.StringIO()
t = Tracer('decompiled/ipa/Payload/BEPiDGame.app/BEPiDGame', out=buf)
s = t.new_object('TutorialScene')
t.send(s, 'initWithSize:', u32f(320.0), u32f(568.0)); t.send(s, 'setIsActive:', 1); t.send(s, 'setTutorialType:', n)
t.skip_impl.update({'playAudioFileNamed:completion:', 'createEnemyWithType:', 'baseActions', 'releasePowerUpOfType:',
                    'didBeginStage:onChapter:onMode:', 'blockTouch:'})
buf.seek(0); buf.truncate()
t.send(s, 'tutorial%d' % n)
i = 0
while i < len(t.blocks) and i < 120:
    if 'BaseActions' not in t.blocks[i][2]: t.run_block(i)
    i += 1
keep = ('!!', 'moveTo', 'moveBy', 'moveTo', 'moveBy', 'playAudioFileNamed', 'speakSentence', 'performSelector', 'createEnemyWithType', 'waitForDuration', '-> <TutorialScene',
        'initBoss', 'releasePowerUp', 'playSoundFileNamed', 'BLOCK#', 'checkIfEnded', 'setAllow', 'scheduledTimer', 'wait:toExecute',
        'initEnemyOfType', 'manualShot', 'inflictDamage', 'endTutorial', 'tutorialCompleto', 'dispatch')
skip = ('isActive', ' stageNumber', 'synthesizer', 'gamePaused', 'talkingMove', 'playerShip', 'timeBetween', 'audioManager',
        'fadeOutWithDuration', 'from runAction:completion:)')
for l in buf.getvalue().splitlines():
    if any(k in l for k in keep) and not any(k in l for k in skip): print(l.rstrip())
