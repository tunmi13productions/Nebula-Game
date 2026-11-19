# Traces a chapter intro cutscene: runs CutScene playIntroCutSceneChapter:completition: with audio playback mocked,
# then runs every captured block in order.
# usage: python tools/re/trace_cutscene.py <chapter 1-9>
import sys, io
sys.path.insert(0, 'tools/re')
from objc_trace import Tracer, u32f
n = int(sys.argv[1])
buf = io.StringIO()
t = Tracer('decompiled/ipa/Payload/BEPiDGame.app/BEPiDGame', out=buf)
scene = t.new_object('Chapter1Scene'); t.send(scene, 'initWithSize:', u32f(320.0), u32f(568.0))
cs = t.new_object('CutScene'); t.send(cs, 'init')
t.pos[cs] = (0.0, 0.0); t.sizes[cs] = (320.0, 568.0)
t.skip_impl.update({'playAudioFileNamed:completion:', 'runBlockOnDifferentThread:withPriority:'})
buf.seek(0); buf.truncate()
t.send(cs, 'playIntroCutSceneChapter:completition:', n, 0)
i = 0
while i < len(t.blocks) and i < 200:
    t.run_block(i); i += 1
keep = ('setSize', 'setPosition', 'setZPosition', 'setAlpha', 'setAnchor', 'moveBy', 'fadeAlpha', 'resize', 'rotate', 'sequence', 'group', 'removeFromParent', 'setZRotation', 'setXScale', 'setYScale', 'colorize', '!!', 'playAudioFileNamed', 'speakSentence', 'performSelector', 'waitForDuration', '-> <CutScene', 'playSoundFileNamed',
        'BLOCK#', 'fadeIn', 'fadeOut', 'moveTo', 'scaleTo', 'presentText', 'showText', 'initWithImageNamed', 'spriteNodeWithImageNamed', 'getTextureWithName')
skip = ('from runAction:completion:)',)
for l in buf.getvalue().splitlines():
    if any(k in l for k in keep) and not any(k in l for k in skip): print(l.split('  =>')[0].rstrip())
