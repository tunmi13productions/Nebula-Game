import sys
sys.path.insert(0, sys.argv[1])
from objc_trace import Tracer
t = Tracer(sys.argv[2])
code = int(sys.argv[3])
scene = t.new_object('Chapter1Scene')
t.send(scene, 'setIsActive:', 1)
boss = t.new_object('Boss')
t.send(boss, 'initBoss:onParentScene:', code, scene)
n = 0
while n < len(t.blocks) and n < int(sys.argv[4]):
    t.run_block(n); n += 1
