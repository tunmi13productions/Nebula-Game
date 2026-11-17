# Emulates SpaceShip::initEnemyOfType:inParentView: for each type and prints the createEnemy arguments.
import sys, struct, lief
from unicorn import *
from unicorn.arm_const import *
path = sys.argv[1]
b = lief.MachO.parse(path).at(0); data = open(path, 'rb').read()
mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
for s in b.segments:
    if s.virtual_size == 0 or s.name == '__PAGEZERO': continue
    base = s.virtual_address & ~0xfff; size = ((s.virtual_address + s.virtual_size + 0xfff) & ~0xfff) - base
    mu.mem_map(base, size)
    mu.mem_write(s.virtual_address, data[s.file_offset:s.file_offset + s.file_size])
SCRATCH, SELF, STACK, SENT = 0x30000000, 0x10000000, 0x20000000, 0x40000000
for a in (SCRATCH, SELF, STACK, SENT): mu.mem_map(a, 0x100000)
sec = {x.name: x for x in b.sections}
for n in ('__nl_symbol_ptr', '__la_symbol_ptr'):
    s = sec[n]
    for i in range(s.size // 4): mu.mem_write(s.virtual_address + 4 * i, struct.pack('<I', SCRATCH))
stub = sec['__picsymbolstub4']; ind = b.dynamic_symbol_command.indirect_symbols
names = {stub.virtual_address + 16 * i: ind[stub.reserved1 + i].name for i in range(stub.size // 16)}
def rd(a, n): return bytes(mu.mem_read(a, n))
def cstr(a):
    out = b''
    while True:
        c = rd(a, 1)
        if c == b'\0': return out.decode()
        out += c; a += 1
calls = []
def hook(uc, addr, size, _):
    if addr == SENT: uc.emu_stop(); return
    n = names.get(addr)
    if n is None: return
    r0 = uc.reg_read(UC_ARM_REG_R0)
    if n == '_objc_msgSend':
        sel = cstr(uc.reg_read(UC_ARM_REG_R1))
        if sel.startswith('createEnemyWithLife'):
            sp = uc.reg_read(UC_ARM_REG_SP)
            st, mv = struct.unpack('<ff', rd(sp, 8))
            calls.append((uc.reg_read(UC_ARM_REG_R2), struct.unpack('<i', struct.pack('<I', uc.reg_read(UC_ARM_REG_R3)))[0], round(st, 3), round(mv, 3)))
        uc.reg_write(UC_ARM_REG_R0, 0)
    elif n == '_objc_msgSendSuper2':
        uc.reg_write(UC_ARM_REG_R0, struct.unpack('<I', rd(r0, 4))[0])
    elif n.startswith('_objc_retain') or n.startswith('_objc_autorelease'):
        pass
    else:
        uc.reg_write(UC_ARM_REG_R0, 0)
    uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
mu.hook_add(UC_HOOK_CODE, hook, begin=stub.virtual_address, end=stub.virtual_address + stub.size)
mu.hook_add(UC_HOOK_CODE, hook, begin=SENT, end=SENT + 4)
FN = int(sys.argv[2], 16)
for t in list(range(0, 51)) + list(range(100, 106)):
    calls.clear(); mu.mem_write(SELF, b'\0' * 0x200)
    mu.reg_write(UC_ARM_REG_SP, STACK + 0x80000)
    mu.reg_write(UC_ARM_REG_R0, SELF); mu.reg_write(UC_ARM_REG_R1, 0); mu.reg_write(UC_ARM_REG_R2, t); mu.reg_write(UC_ARM_REG_R3, 0x50000000)
    mu.reg_write(UC_ARM_REG_LR, SENT | 1)
    mu.emu_start(FN | 1, 0, count=20000)
    code, dmg = struct.unpack('<i', rd(SELF + 68, 4))[0], struct.unpack('<i', rd(SELF + 108, 4))[0]
    for life, score, st, mv in calls:
        print(f'{t}: code {code} life {life} score {score} fire {st} move {mv} damage {dmg}')
    if not calls: print(f'{t}: no createEnemy call (code {code}, damage {dmg})')
