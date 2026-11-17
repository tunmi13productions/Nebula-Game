# Lists, in address order, each method of a class and the selectors, strings, constants and calls it references,
# including code in blocks that sit between the methods.
# usage: python -I tools/re/scan_class.py <ClassName>   (run from the repository root)
import re, subprocess, sys
cls = sys.argv[1]
B = 'decompiled/ipa/Payload/BEPiDGame.app/BEPiDGame'
heads = [(int(m.group(2), 16), m.group(1)) for m in
         re.finditer(r'^// ==== (\S+) @ ([0-9a-f]+)', open('decompiled/analysis/decompiled.c', encoding='utf-8').read(), re.M)]
heads.sort()
mine = [(a, n) for a, n in heads if n.startswith(cls + '::')]
start = mine[0][0]
end = next(a for a, n in heads if a > mine[-1][0] and not n.startswith('FUN_'))
out = subprocess.run([sys.executable, '-I', 'tools/re/refs.py', B, hex(start), hex(end)], capture_output=True, text=True).stdout
skip = re.compile(r"sel (release|retain|alloc|init|mainBundle|frame|size|position|synthesizer|stageNumber|introCutScene|playerShip|"
                  r"audioManager|generator|soundIDEnumerator|localizedStringForKey:value:table:|setZPosition:|addChild:|setSize:|"
                  r"setPosition:|removeAllActions|removeAllChildren|removeFromParent|setScale:|initWithTexture:|getTextureWithName:|"
                  r"initMessageWindowOnScene:|showMessageWindow|presentText:withSpeaker:|currentDevice|userInterfaceIdiom|"
                  r"spaceshipNode|arrayWithObjects:count:|sequence:)$|str ''$|str 'I.C.A.R.U.S.'|ivar@|: ptr$|int \w+, #0$|class |call _objc|"
                  r"call ___stack")
mi = 0
for line in out.splitlines():
    a = int(line.split(':')[0], 16)
    while mi < len(mine) and mine[mi][0] <= a:
        print('### ' + mine[mi][1].split('::', 1)[1]); mi += 1
    body = line.split(': ', 1)[1]
    if not skip.search(body): print('  ' + body)
