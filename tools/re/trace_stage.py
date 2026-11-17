# Traces a campaign stage opening: runs nextStage for ChapterNScene at the given stage, then runs every captured
# block in order (speech completions, delayed actions), skipping spawning internals and boss construction.
# usage: python tools/re/trace_stage.py <chapter> <stage> [method]
import sys, io
sys.path.insert(0, 'tools/re')
from objc_trace import Tracer
c, st = int(sys.argv[1]), int(sys.argv[2]); method = sys.argv[3] if len(sys.argv) > 3 else 'nextStage'
buf = io.StringIO()
t = Tracer('decompiled/ipa/Payload/BEPiDGame.app/BEPiDGame', out=buf)
s = t.new_object('Chapter%dScene' % c)
from objc_trace import u32f
t.send(s, 'initWithSize:', u32f(320.0), u32f(568.0))
t.send(s, 'setIsActive:', 1); t.send(s, 'setStageNumber:', st)
t.skip_impl.update({'createEnemyWithType:', 'didBeginStage:onChapter:onMode:', 'blockTouch:', 'initBoss:onParentScene:',
                    'defaultVictoriousAnimation', 'endGameVictorious', 'releasePowerUpOfType:', 'baseActions'})
buf.seek(0); buf.truncate()
t.send(s, method)
i = 0
while i < len(t.blocks) and i < 40:
    t.run_block(i); i += 1
keep = ("!!", 'speakSentence', 'performSelector', 'createEnemyWithType', 'waitForDuration', '-> <Chapter', 'initBoss', 'releasePowerUp',
        'playSoundFileNamed', 'BLOCK#', 'defaultVictorious', 'endGameVictorious', 'presentText')
for l in buf.getvalue().splitlines():
    if any(k in l for k in keep) and 'isActive' not in l and ' stageNumber' not in l and 'synthesizer' not in l: print(l.rstrip())
