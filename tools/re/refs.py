# Lists pc-relative references (selectors, cfstrings, classes, doubles) and calls in a Thumb range.
# usage: refs.py <binary> <start_hex> <end_hex>
import sys, struct, lief, capstone
path, start, end = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
b = lief.MachO.parse(path).at(0); d = open(path, 'rb').read()
segs = [(s.virtual_address, s.virtual_address + s.file_size, s.file_offset) for s in b.segments]
def off(va):
    for a, e, o in segs:
        if a <= va < e: return o + va - a
sec = {s.name: s for s in b.sections}
def insec(a, n): s = sec[n]; return s.virtual_address <= a < s.virtual_address + s.size
def cstr(va):
    o = off(va); e = d.index(b'\0', o); return d[o:e].decode('utf-8', 'replace')
def cfs(va):
    _, fl, p, n = struct.unpack_from('<IIII', d, off(va))
    return d[off(p):off(p) + (n * 2 if fl == 0x7d0 else n)].decode('utf-16-le' if fl == 0x7d0 else 'utf-8', 'replace')
binds = {bi.address: bi.symbol.name for bi in b.bindings if bi.has_symbol}
stub = sec['__picsymbolstub4']; ind = b.dynamic_symbol_command.indirect_symbols
def stubname(t):
    if stub.virtual_address <= t < stub.virtual_address + stub.size:
        return ind[stub.reserved1 + (t - stub.virtual_address) // 16].name
    # thunk: ldr.w ip,[pc,#4]; add ip,pc; bx ip
    o = off(t)
    if o and d[o:o+4] == b'\xdf\xf8\x04\xc0':
        lit = struct.unpack_from('<I', d, o + 8)[0]; return stubname(t + 4 + 4 + lit - 4 + 0) if False else stubname(t + 8 + lit)
    return hex(t)
def describe(a):
    if insec(a, '__objc_selrefs'): return 'sel ' + cstr(struct.unpack_from('<I', d, off(a))[0])
    if insec(a, '__cfstring'): return 'str ' + repr(cfs(a))
    if insec(a, '__objc_classrefs'):
        v = struct.unpack_from('<I', d, off(a))[0]
        return 'class ' + (binds.get(a, '').replace('_OBJC_CLASS_$_', '') or hex(v))
    if insec(a, '__objc_ivar'): return 'ivar@' + hex(a)
    if insec(a, '__nl_symbol_ptr'): return 'ptr'
    return None
cs = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
regs = {}
for i in cs.disasm(d[off(start):off(end)], start):
    m, o = i.mnemonic, i.op_str
    if m == 'movw': r, v = o.split(', #'); regs[r] = int(v, 16)
    elif m == 'movt': r, v = o.split(', #'); regs[r] = regs.get(r, 0) | (int(v, 16) << 16)
    elif m == 'add' and o.endswith(', pc') and o.split(',')[0] in regs:
        r = o.split(',')[0]; a = regs.pop(r) + i.address + 4; s = describe(a)
        if s: print(f'{i.address:#x}: {s}')
    elif m.startswith('bl') and o.startswith('#'):
        n = stubname(int(o[1:], 16))
        if 'objc_msgSend' not in n and 'retain' not in n and 'release' not in n: print(f'{i.address:#x}: call {n}')
    elif m.startswith('vmov') and '#' in o and 'e' in o.split('#')[-1]:
        print(f'{i.address:#x}: const {o}')
    elif m == 'vldr' and '[pc' in o:
        disp = int(o.split('#')[-1].rstrip(']'), 16) if '#' in o else 0
        a = ((i.address + 4) & ~3) + disp; print(f'{i.address:#x}: double {struct.unpack_from("<d", d, off(a))[0]}')
    elif m in ('movs', 'mov.w') and '#' in o:
        print(f'{i.address:#x}: int {o}')
