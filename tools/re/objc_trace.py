# Tracing emulator for BEPiDGame (armv7 Thumb, Objective-C).
# Runs original functions under Unicorn. Methods implemented in the binary execute for real,
# framework calls (SpriteKit, Foundation, UIKit...) are mocked and logged with decoded arguments.
import struct, re, sys, lief, plistlib, os
from unicorn import *
from unicorn.arm_const import *

SCENE_W, SCENE_H = 320.0, 568.0

def f32(u): return struct.unpack('<f', struct.pack('<I', u & 0xffffffff))[0]
def u32f(f): return struct.unpack('<I', struct.pack('<f', f))[0]
def f64(lo, hi): return struct.unpack('<d', struct.pack('<II', lo, hi))[0]

# Argument signatures for framework selectors: P=CGPoint/CGSize (2 floats), f=float, d=double,
# i=int, @=object, B=block, R=CGRect (4 floats). Unknown selectors print raw words.
FW_SIG = {
    'moveTo:duration:': 'Pd', 'moveToX:duration:': 'fd', 'moveToY:duration:': 'fd', 'moveByX:y:duration:': 'ffd',
    'moveBy:duration:': 'Pd', 'waitForDuration:': 'd', 'waitForDuration:withRange:': 'dd',
    'rotateByAngle:duration:': 'fd', 'rotateToAngle:duration:': 'fd', 'scaleBy:duration:': 'fd', 'scaleTo:duration:': 'fd',
    'fadeInWithDuration:': 'd', 'fadeOutWithDuration:': 'd', 'fadeAlphaTo:duration:': 'fd',
    'resizeToWidth:duration:': 'fd', 'resizeToHeight:duration:': 'fd',
    'animateWithTextures:timePerFrame:': '@d', 'animateWithTextures:timePerFrame:resize:restore:': '@dii',
    'playSoundFileNamed:waitForCompletion:': '@i', 'runBlock:': 'B', 'runAction:': '@', 'runAction:completion:': '@B',
    'runAction:withKey:': '@@', 'sequence:': '@', 'group:': '@', 'repeatActionForever:': '@', 'repeatAction:count:': '@i',
    'setPosition:': 'P', 'setSize:': 'P', 'setAnchorPoint:': 'P', 'setZPosition:': 'f', 'setScale:': 'f', 'setAlpha:': 'f',
    'setZRotation:': 'f', 'setXScale:': 'f', 'setYScale:': 'f', 'setColorBlendFactor:': 'f',
    'spriteNodeWithColor:size:': '@P', 'initWithColor:size:': '@P', 'spriteNodeWithTexture:size:': '@P',
    'initWithTexture:color:size:': '@@P', 'bodyWithRectangleOfSize:': 'P', 'bodyWithCircleOfRadius:': 'f',
    'bodyWithRectangleOfSize:center:': 'PP', 'setCategoryBitMask:': 'i', 'setContactTestBitMask:': 'i',
    'setCollisionBitMask:': 'i', 'setDynamic:': 'i', 'setAffectedByGravity:': 'i',
    'performSelector:withObject:afterDelay:': '@@d', 'scheduledTimerWithTimeInterval:target:selector:userInfo:repeats:': 'd@@@i',
    'stringWithFormat:': '@iiii', 'localizedStringForKey:value:table:': '@@@', 'objectForKey:': '@', 'setObject:forKey:': '@@',
    'objectAtIndex:': 'i', 'objectAtIndexedSubscript:': 'i', 'arrayWithObjects:count:': 'Ai',
    'speakSentence:withRate:': '@f', 'executeOnceSoundNamed:inPosition:': '@P', 'executeForeverSoundNamed:inPosition:': '@P',
    'setText:': '@', 'setName:': '@', 'addChild:': '@', 'removeActionForKey:': '@', 'actionForKey:': '@',
    'pathForResource:ofType:': '@@', 'initWithImageNamed:': '@', 'spriteNodeWithImageNamed:': '@',
    'setNumParticlesToEmit:': 'i', 'setParticleBirthRate:': 'f', 'setTimingMode:': 'i', 'setSpeed:': 'f',
    'integerForKey:': '@', 'boolForKey:': '@', 'setInteger:forKey:': 'i@', 'setBool:forKey:': 'i@',
    'colorWithRed:green:blue:alpha:': 'ffff', 'getTextureWithName:': '@', 'getTexturesWithPrefix:': '@',
    'textureWithImageNamed:': '@', 'followPath:asOffset:orientToPath:duration:': '@iid',
    'getRandomNumberBetween:maxNumber:': 'ii', 'removeFromParent': '', 'setHidden:': 'i', 'setPaused:': 'i',
    'setPan:': 'f', 'setVolume:': 'f', 'moveToPoint:': 'P', 'addLineToPoint:': 'P', 'setRestitution:': 'f',
    'setLastKnownPosition:': 'P', 'setNumberOfLoops:': 'i', 'setMaxAudio:': 'f', 'setBlendMode:': 'i',
    'setParticleLifetime:': 'f', 'setParticleSpeed:': 'f', 'setEmissionAngleRange:': 'f',
    'stringWithFormat:': '@iiii', 'bodyWithPolygonFromPath:': '@', 'bodyWithEdgeLoopFromRect:': 'PP',
    'setUsesPreciseCollisionDetection:': 'i', 'setAllowsRotation:': 'i', 'setFriction:': 'f', 'setMass:': 'f',
    'setLinearDamping:': 'f', 'setVelocity:': 'P', 'applyImpulse:': 'P', 'followPath:duration:': '@d',
    'speakSentence:withRate:preUtteranceDelay:postUtteranceDelay:completition:': '@fddB',
    'colorizeWithColor:colorBlendFactor:duration:': '@fd', 'playAudioFileNamed:completion:': '@B',
    'showText:for:speaker:': '@d@', 'presentText:withSpeaker:': '@@',
}
STRET_SELS = {'frame', 'size', 'position', 'anchorPoint', 'locationInNode:', 'calculateAccumulatedFrame', 'bounds', 'acceleration'}

class Tracer:
    def __init__(self, path, out=sys.stdout, max_depth=40):
        self.out = out
        b = self.b = lief.MachO.parse(path).at(0)
        self.data = open(path, 'rb').read()
        mu = self.mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        mu.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A15)
        mu.reg_write(UC_ARM_REG_C1_C0_2, mu.reg_read(UC_ARM_REG_C1_C0_2) | (0xf << 20))
        mu.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
        for s in b.segments:
            if s.virtual_size == 0 or s.name == '__PAGEZERO': continue
            base = s.virtual_address & ~0xfff
            size = ((s.virtual_address + s.virtual_size + 0xfff) & ~0xfff) - base
            mu.mem_map(base, size)
            mu.mem_write(s.virtual_address, self.data[s.file_offset:s.file_offset + s.file_size])
        self.sec = {x.name: x for x in b.sections}
        self.HEAP, self.HANDLE, self.STACK, self.SENT, self.IMPORT = 0x10000000, 0x50000000, 0x20000000, 0x40000000, 0x30000000
        mu.mem_map(self.HEAP, 0x4000000); mu.mem_map(self.STACK, 0x200000); mu.mem_map(self.SENT, 0x1000)
        mu.mem_map(self.IMPORT, 0x100000); mu.mem_map(self.HANDLE, 0x1000000)
        self.heap_top = self.HEAP + 0x100
        self.handles = {}      # addr -> description
        self.next_handle = self.HANDLE + 0x100
        self.objclass = {}     # heap object addr -> internal class addr
        self.pos = {}          # object -> (x, y) tracked positions
        self.sizes = {}        # object -> (w, h)
        self.blocks = []       # copied blocks (addr, invoke, label)
        self.depth = 0
        # bindings: imported data pointers and external class refs
        self.bind_name = {}
        for bi in b.bindings:
            if bi.has_symbol: self.bind_name[bi.address] = bi.symbol.name
        imp_slot = self.IMPORT
        self.import_addr = {}
        for addr, name in self.bind_name.items():
            if name.startswith('_OBJC_CLASS_$_') or name.startswith('_OBJC_METACLASS_$_'):
                h = self.new_handle('class ' + name.split('$_')[1]); self.w32(addr, h)
            else:
                if name not in self.import_addr:
                    self.import_addr[name] = imp_slot; imp_slot += 0x40
                self.w32(addr, self.import_addr[name])
        ind = b.dynamic_symbol_command.indirect_symbols
        for n in ('__nl_symbol_ptr',):
            s = self.sec[n]
            for i in range(s.size // 4):
                a = s.virtual_address + 4 * i
                if self.r32(a) == 0:
                    try: nm = ind[s.reserved1 + i].name
                    except Exception: nm = ''
                    if nm not in self.import_addr: self.import_addr[nm] = imp_slot; imp_slot += 0x40
                    self.w32(a, self.import_addr[nm])
        self.import_name = {v: k for k, v in self.import_addr.items()}
        stub = self.sec['__picsymbolstub4']
        self.stubs = {stub.virtual_address + 16 * i: ind[stub.reserved1 + i].name for i in range(stub.size // 16)}
        self.load_classes()
        self.load_textures(os.path.dirname(path))
        mu.hook_add(UC_HOOK_CODE, self.on_stub, begin=stub.virtual_address, end=stub.virtual_address + stub.size)
        mu.hook_add(UC_HOOK_CODE, self.on_sent, begin=self.SENT, end=self.SENT + 0x10)
        mu.hook_add(UC_HOOK_MEM_UNMAPPED, self.on_bad)
        self.globals = {}
        # the Global singleton is cached in a __DATA variable reached through this pointer
        g = self.send(self.classbyname['Global'], 'sharedManager', label='setup Global')
        self.global_obj = g
        self.w32(self.r32(0xb4018), g)

    # memory helpers
    def r32(self, a): return struct.unpack('<I', bytes(self.mu.mem_read(a, 4)))[0]
    def w32(self, a, v): self.mu.mem_write(a, struct.pack('<I', v & 0xffffffff))
    def cstr(self, a):
        out = bytearray()
        while True:
            c = self.mu.mem_read(a, 1)[0]
            if c == 0: return out.decode('utf-8', 'replace')
            out.append(c); a += 1
    def alloc(self, n):
        a = self.heap_top; self.heap_top += (n + 15) & ~15; self.mu.mem_write(a, b'\0' * n); return a
    def new_handle(self, desc):
        h = self.next_handle; self.next_handle += 0x10; self.handles[h] = desc; return h

    def load_classes(self):
        sec = self.sec
        self.classes = {}  # addr -> dict(name, super, imeth, cmeth, size)
        self.classbyname = {}
        cl = sec['__objc_classlist']
        for i in range(cl.size // 4):
            c = self.r32(cl.virtual_address + 4 * i)
            self.parse_class(c)
        for c, info in self.classes.items():
            self.classbyname[info['name']] = c
            # class objects are the class_t addresses themselves
        self.meta = {self.r32(c): c for c in self.classes}
    def methods(self, ml):
        out = {}
        if not ml: return out
        ent, cnt = self.r32(ml) & 0xffff, self.r32(ml + 4)
        for i in range(cnt):
            p = ml + 8 + i * ent
            out[self.cstr(self.r32(p))] = (self.r32(p + 8), self.cstr(self.r32(p + 4)))
        return out
    def parse_class(self, c):
        ro = self.r32(c + 16) & ~3
        meta = self.r32(c); mro = self.r32(meta + 16) & ~3
        sup = self.r32(c + 4)
        supname = None
        if sup in self.handles: supname = self.handles[sup].split(' ', 1)[1]
        self.classes[c] = dict(name=self.cstr(self.r32(ro + 16)), super=sup, supname=supname,
                               imeth=self.methods(self.r32(ro + 20)), cmeth=self.methods(self.r32(mro + 20)),
                               size=self.r32(ro + 8))
    def find_method(self, cls, sel, meta=False):
        while cls in self.classes:
            m = self.classes[cls]['cmeth' if meta else 'imeth']
            if sel in m: return m[sel]
            cls = self.classes[cls]['super']
        return None
    def ext_base(self, cls):
        while cls in self.classes: cls = self.classes[cls]['super']
        return self.handles.get(cls, '?').replace('class ', '')

    def load_textures(self, app):
        self.tex = {}
        for atlas in ('gameTextures',):
            p = os.path.join(app, atlas + '.atlasc', atlas + '.plist')
            if os.path.exists(p):
                for im in plistlib.load(open(p, 'rb'))['images']:
                    for s in im['subimages']:
                        w, h = re.findall(r'[\d.]+', s['spriteSourceSize'])
                        self.tex[s['name'].rsplit('.', 1)[0]] = (float(w), float(h))

    # describing values
    def desc(self, v):
        if v == 0: return 'nil'
        if v in self.handles: return self.handles[v]
        if v in self.objclass: return '<%s %#x>' % (self.classes[self.objclass[v]]['name'], v)
        if v in self.classes: return 'class ' + self.classes[v]['name']
        s = self.sec['__cfstring']
        if s.virtual_address <= v < s.virtual_address + s.size:
            _, fl, p, n = struct.unpack('<IIII', bytes(self.mu.mem_read(v, 16)))
            raw = bytes(self.mu.mem_read(p, n * 2 if fl == 0x7d0 else n))
            return repr(raw.decode('utf-16-le' if fl == 0x7d0 else 'utf-8', 'replace'))
        if v in self.import_name: return '&' + self.import_name[v]
        if self.STACK <= v < self.STACK + 0x200000 or self.HEAP <= v < self.HEAP + 0x4000000:
            # maybe a block
            isa = self.r32(v) if self.HEAP <= v or True else 0
            nm = self.import_name.get(isa, '')
            if 'Block' in nm: return 'block<invoke %#x>' % self.r32(v + 12)
        return '%#x' % v

    def fmt_args(self, sel, sig, regs, sp):
        words = regs[2:4] + [self.r32(sp + 4 * i) for i in range(8)]
        out, wi = [], 0
        def take(n, align=False):
            nonlocal wi
            if align and wi % 2 == 1 and wi >= 2 or align and wi == 1: wi += 1
            v = words[wi:wi + n]; wi += n; return v
        for t in sig:
            if t == 'd':
                lo, hi = take(2); out.append('%g' % f64(lo, hi))
            elif t == 'f': out.append('%g' % f32(take(1)[0]))
            elif t == 'P':
                a, c = take(2); out.append('(%g, %g)' % (f32(a), f32(c)))
            elif t == 'i': v = take(1)[0]; out.append(str(struct.unpack('<i', struct.pack('<I', v))[0]))
            elif t == 'A':
                arr, = take(1); cnt = words[wi] if wi < len(words) else 0
                out.append('[' + ', '.join(self.desc(self.r32(arr + 4 * k)) for k in range(min(cnt, 16))) + ']')
            elif t == 'B':
                v = take(1)[0]; out.append(self.copy_block(v, sel))
            else: out.append(self.desc(take(1)[0]))
        return out

    def copy_block(self, v, label):
        if v == 0: return 'nil'
        if v in self.handles: return self.handles[v]
        isa = self.r32(v); nm = self.import_name.get(isa, '')
        if 'Block' not in nm: return self.desc(v)
        desc = self.r32(v + 16); size = self.r32(desc + 4)
        size = max(size, 20) if size < 0x400 else 0x40
        h = self.alloc(size); self.mu.mem_write(h, bytes(self.mu.mem_read(v, size)))
        inv = self.r32(v + 12) & ~1
        idx = len(self.blocks); self.blocks.append((h, inv, label))
        return 'BLOCK#%d(invoke %#x)' % (idx, inv)

    def sig_for(self, cls, sel, meta):
        # own methods: parse the type encoding into our signature letters
        if cls is not None:
            m = self.find_method(cls, sel, meta)
            if m: return self.enc_to_sig(m[1])
        return FW_SIG.get(sel)
    def enc_to_sig(self, enc):
        enc = re.sub(r'\d+', '', enc)
        # skip return type
        toks = re.findall(r'\{[^}]*\}|\^?[@:#vcifdBlILsSqQ*]|@\?', enc)
        sig = ''
        for t in toks[3:]:
            if t.startswith('{CGPoint') or t.startswith('{CGSize'): sig += 'P'
            elif t.startswith('{CGRect'): sig += 'PP'
            elif t == 'f': sig += 'f'
            elif t == 'd': sig += 'd'
            elif t in ('@?',): sig += 'B'
            elif t in ('@', '#', ':'): sig += '@'
            else: sig += 'i'
        return sig

    def log(self, s): self.out.write('  ' * self.depth + s + '\n')

    # hooks
    def on_bad(self, uc, access, addr, size, value, _):
        self.log('!! unmapped access %#x at pc %#x' % (addr, uc.reg_read(UC_ARM_REG_PC))); return False
    def on_sent(self, uc, addr, size, _): uc.emu_stop()
    def ret(self, v=0, hi=None):
        mu = self.mu; mu.reg_write(UC_ARM_REG_R0, v & 0xffffffff)
        if hi is not None: mu.reg_write(UC_ARM_REG_R1, hi & 0xffffffff)
        mu.reg_write(UC_ARM_REG_PC, mu.reg_read(UC_ARM_REG_LR))
    def regs(self):
        return [self.mu.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]

    def on_stub(self, uc, addr, size, _):
        name = self.stubs.get(addr)
        if name is None: return
        r = self.regs(); sp = uc.reg_read(UC_ARM_REG_SP)
        if name in ('_objc_msgSend', '_objc_msgSend_stret', '_objc_msgSendSuper2', '_objc_msgSendSuper2_stret'):
            return self.msgsend(name, r, sp)
        if name.startswith(('_objc_retain', '_objc_autorelease')) or name in ('_objc_storeStrong',):
            if name == '_objc_storeStrong': self.w32(r[0], r[1])
            return self.ret(r[0])
        if name == '_objc_storeWeak': self.w32(r[0], r[1]); return self.ret(r[1])
        if name in ('_objc_loadWeakRetained', '_objc_loadWeak'): return self.ret(self.r32(r[0]))
        if name in ('_objc_initWeak',): self.w32(r[0], r[1]); return self.ret(r[1])
        if name in ('_objc_destroyWeak', '_objc_release', '_objc_copyWeak', '_objc_moveWeak'):
            if name in ('_objc_copyWeak', '_objc_moveWeak'): self.w32(r[0], self.r32(r[1]))
            return self.ret(0)
        if name == '_dispatch_once':
            if self.r32(r[0]) == 0:
                self.w32(r[0], 0xffffffff)
                uc.reg_write(UC_ARM_REG_R0, r[1]); uc.reg_write(UC_ARM_REG_PC, self.r32(r[1] + 12)); return
            return self.ret(0)
        if name == '_arc4random': self.log('arc4random -> %d' % self.rand_value); return self.ret(self.rand_value)
        if name == '_arc4random_uniform': self.log('arc4random_uniform(%d) -> 0' % r[0]); return self.ret(0)
        if name in ('_NSLog', '_UIAccessibilityIsVoiceOverRunning'):
            if name == '_NSLog': self.log('NSLog %s' % self.desc(r[0]))
            return self.ret(1 if 'VoiceOver' in name else 0)
        if name in ('_objc_enumerationMutation', '___stack_chk_fail', '_objc_terminate', '_objc_exception_throw'):
            self.log('!! %s' % name); uc.emu_stop(); return
        if name == '_objc_getProperty': return self.ret(self.r32(r[0] + r[2]))
        if name == '_objc_setProperty_nonatomic' or name.startswith('_objc_setProperty'):
            self.w32(r[0] + r[3], self.r32(sp)); return self.ret(0)
        if name in ('_objc_retainBlock', '__Block_copy'):
            self.copy_block(r[0], 'retainBlock'); return self.ret(r[0])
        if name.startswith('_objc_'): return self.ret(r[0])
        # math functions use softfp doubles in r0:r1 (and r2:r3)
        import math
        x = f64(r[0], r[1]); y = f64(r[2], r[3])
        fn = {'_cos': math.cos, '_sin': math.sin, '_sqrt': math.sqrt, '_cbrt': lambda v: math.copysign(abs(v) ** (1 / 3), v),
              '_fabs': abs, '_floor': math.floor, '_ceil': math.ceil, '_round': round, '_exp': math.exp, '_log': math.log}
        if name in fn: v = fn[name](x); lo, hi = struct.unpack('<II', struct.pack('<d', v)); return self.ret(lo, hi)
        if name in ('_atan2', '_hypot', '_pow', '_fmod'):
            v = {'_atan2': math.atan2, '_hypot': math.hypot, '_pow': math.pow, '_fmod': math.fmod}[name](x, y)
            lo, hi = struct.unpack('<II', struct.pack('<d', v)); return self.ret(lo, hi)
        self.log('call %s(%s)' % (name, ', '.join(self.desc(v) for v in r)))
        return self.ret(self.new_handle('ret of ' + name))

    def msgsend(self, name, r, sp):
        stret = name.endswith('_stret'); sup = 'Super' in name
        o = 1 if stret else 0
        recv, selp = r[o], r[o + 1]
        if sup:
            st = recv; recv = self.r32(st); start = self.r32(st + 4)
            meta = start in self.meta
            start_cls = self.meta.get(start, start)
            start_cls = self.classes[start_cls]['super'] if start_cls in self.classes else None
        sel = self.cstr(selp)
        mu = self.mu
        if recv == 0:
            if stret: mu.mem_write(r[0], b'\0' * 16)
            return self.ret(0)
        meta = recv in self.classes
        cls = recv if meta else self.objclass.get(recv)
        if sup: cls = start_cls
        imp = self.find_method(cls, sel, meta) if cls is not None else None
        if imp and not (sel in self.skip_impl):
            if not stret and self.trace_internal:
                self.log('-> %s %s' % (self.desc(recv) if not meta else self.classes[recv]['name'], sel))
            if sup:  # replace the super struct pointer by the receiver
                mu.reg_write(UC_ARM_REG_R1 if stret else UC_ARM_REG_R0, recv)
            mu.reg_write(UC_ARM_REG_PC, imp[0] | 1 if imp[0] & 1 == 0 else imp[0]); return
        # framework / mocked call
        sig = self.sig_for(cls, sel, meta) if cls else FW_SIG.get(sel)
        if sig is None: sig = 'x' * min(sel.count(':'), 6)
        regs = [0, 0] + ([r[3], self.r32(sp)] if stret else r[2:4])
        args = self.fmt_args(sel, sig, regs, sp + (4 if stret else 0)) if sig else []
        who = self.desc(recv)
        if sel == 'alloc' and meta:
            obj = self.alloc(0x800); self.w32(obj, recv); self.objclass[obj] = recv
            return self.ret(obj)
        if sup and sel.startswith('init'):
            if sel != 'init': self.log('%s super %s' % (self.desc(recv), sel))
            return self.ret(recv)
        if sel in ('init', 'initWithTexture:', 'initWithImageNamed:', 'initWithColor:size:', 'initWithTexture:color:size:') and recv in self.objclass:
            if sel != 'init': self.log('%s %s %s' % (who, sel, ' '.join(args)))
            m = re.search(r"'([^']+)'", args[0]) if args else None
            if m and m.group(1).rsplit('.', 1)[0] in self.tex: self.sizes[recv] = self.tex[m.group(1).rsplit('.', 1)[0]]
            if sel == 'initWithColor:size:': self.sizes[recv] = tuple(float(x) for x in args[1].strip('()').split(','))
            return self.ret(recv)
        if stret:
            self.stret(r[0], recv, sel); return self.ret(r[0])
        val = self.mock_value(recv, sel, args, regs, sp)
        if sel in ('initWithTexture:', 'spriteNodeWithTexture:', 'initWithImageNamed:', 'spriteNodeWithImageNamed:') and val:
            m = re.search(r"'([^']+)'", args[0])
            if m and m.group(1).rsplit('.', 1)[0] in self.tex: self.sizes[val] = self.tex[m.group(1).rsplit('.', 1)[0]]
        if sel not in self.quiet: self.log('%s %s %s' % (who, sel, ' '.join(args)) + ('' if val is None else '  => ' + self.desc(val)))
        if sel == 'setPosition:': self.pos[recv] = tuple(float(x) for x in args[0].strip('()').split(','))
        if sel == 'setSize:': self.sizes[recv] = tuple(float(x) for x in args[0].strip('()').split(','))
        return self.ret(0 if val is None else val)

    quiet = {'count', 'class', 'isEqualToString:', 'mainBundle', 'standardUserDefaults', 'defaultCenter'}
    skip_impl = {'getTexturesWithPrefix:', 'getTextureWithName:', 'platform'}
    trace_internal = True
    rand_value = 0

    def mock_value(self, recv, sel, args, regs, sp):
        if sel in ('integerForKey:', 'boolForKey:', 'count', 'userInterfaceIdiom', 'isActive', 'gamePaused', 'zPosition', 'isEqualToString:', 'floatForKey:'):
            return self.int_answers.get(sel, 0)
        if sel.startswith('set') and sel.endswith(':') or sel in ('addChild:', 'removeFromParent', 'removeAllActions',
                                                                   'removeAllChildren', 'runAction:', 'runAction:completion:',
                                                                   'runAction:withKey:', 'removeActionForKey:', 'play', 'stop',
                                                                   'prepareToPlay', 'speakSentence:withRate:'):
            return None
        if sel == 'localizedStringForKey:value:table:': return self.new_handle('L(%s)' % args[0])
        if sel == 'getTextureWithName:' or sel == 'textureWithImageNamed:': return self.new_handle('tex(%s)' % args[0])
        if sel == 'getTexturesWithPrefix:': return self.new_handle('textures(%s*)' % args[0].strip("'"))
        if sel == 'stringWithFormat:': return self.new_handle('fmt(%s)' % ','.join(args[:2]))
        if sel == 'objectAtIndexedSubscript:' or sel == 'objectAtIndex:':
            d = self.handles.get(recv, '')
            m = re.match(r"textures[(](.*)[*][)]", d)
            if m:
                names = sorted(n for n in self.tex if n.startswith(m.group(1)))
                i = int(args[0])
                return self.new_handle("tex('%s')" % (names[i] if 0 <= i < len(names) else '%s?%d' % (m.group(1), i)))
        if sel in ('countByEnumeratingWithState:objects:count:', 'maxAudio', 'zPosition', 'volume', 'duration',
                   'currentTime', 'integerValue', 'intValue', 'floatValue', 'boolValue', 'length', 'isPlaying'):
            return 0
        h = self.new_handle('#%x %s' % ((self.next_handle - self.HANDLE) >> 4, sel))
        return h
    int_answers = {'isActive': 1, 'userInterfaceIdiom': 0}

    def stret(self, out, recv, sel):
        if sel in ('frame', 'bounds'):
            if recv in self.objclass and self.ext_base(self.objclass[recv]) in ('SKScene',):
                v = (0.0, 0.0, SCENE_W, SCENE_H)
            else:
                w, h = self.size_of(recv); x, y = self.pos.get(recv, (0.0, 0.0)); v = (x - w / 2, y - h / 2, w, h)
            self.mu.mem_write(out, struct.pack('<4f', *v))
        elif sel == 'size':
            if recv in self.objclass and self.ext_base(self.objclass[recv]) in ('SKScene',): v = (SCENE_W, SCENE_H)
            else: v = self.size_of(recv)
            self.mu.mem_write(out, struct.pack('<2f', *v))
        elif sel == 'position': self.mu.mem_write(out, struct.pack('<2f', *self.pos.get(recv, (0.0, 0.0))))
        else: self.mu.mem_write(out, b'\0' * 16)
    def size_of(self, h):
        if h in self.sizes: return self.sizes[h]
        d = self.handles.get(h, '')
        m = re.search(r"tex\('([^']+)'\)", d) or re.search(r"objectAtIndexedSubscript:\((\d+)\)", d)
        if m and m.group(1) in self.tex: return self.tex[m.group(1)]
        return (40.0, 40.0)

    # running
    def call(self, fn, *args, label=None):
        mu = self.mu
        mu.reg_write(UC_ARM_REG_SP, self.STACK + 0x1f0000)
        regs = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
        for i, a in enumerate(args[:4]): mu.reg_write(regs[i], a & 0xffffffff)
        sp = self.STACK + 0x1f0000
        for i, a in enumerate(args[4:]): self.w32(sp + 4 * i, a)
        mu.reg_write(UC_ARM_REG_LR, self.SENT | 1)
        if label: self.log('== ' + label)
        try:
            mu.emu_start(fn | 1, self.SENT, count=2000000)
        except UcError as e:
            self.log('!! emulation error %s at pc %#x' % (e, mu.reg_read(UC_ARM_REG_PC)))
        return mu.reg_read(UC_ARM_REG_R0)
    def new_object(self, clsname):
        c = self.classbyname[clsname]
        obj = self.alloc(0x800); self.w32(obj, c); self.objclass[obj] = c; return obj
    def send(self, obj, sel, *args, label=None):
        cls = self.objclass.get(obj, obj)
        meta = obj in self.classes
        imp = self.find_method(cls, sel, meta)
        if not imp: raise KeyError(sel)
        selp = self.selref(sel)
        return self.call(imp[0], obj, selp, *args, label=label or '%s %s' % (self.desc(obj), sel))
    def selref(self, sel):
        s = self.sec['__objc_selrefs']
        for i in range(s.size // 4):
            p = self.r32(s.virtual_address + 4 * i)
            if self.cstr(p) == sel: return p
        p = self.alloc(len(sel) + 1); self.mu.mem_write(p, sel.encode() + b'\0'); return p
    def run_block(self, idx):
        h, inv, label = self.blocks[idx]
        return self.call(inv, h, label='BLOCK#%d (from %s)' % (idx, label))
