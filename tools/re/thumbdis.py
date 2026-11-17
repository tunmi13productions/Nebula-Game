# Thumb disassembler for BEPiDGame. usage: dis.py <binary> <start_hex> <end_hex>
import sys, struct, lief, capstone
path, start, end = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
b = lief.MachO.parse(path).at(0)
data = open(path, 'rb').read()
segs = [(s.virtual_address, s.virtual_address + s.file_size, s.file_offset) for s in b.segments]
def off(va):
    for a, e, o in segs:
        if a <= va < e: return o + va - a
stubsec = [s for s in b.sections if s.name == '__picsymbolstub4'][0]
ind = b.dynamic_symbol_command.indirect_symbols
stubs = {}
for i in range(stubsec.size // 16):
    try: stubs[stubsec.virtual_address + 16 * i] = ind[stubsec.reserved1 + i].name
    except Exception: pass
cs = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
cs.detail = True
code = data[off(start):off(end)]
for ins in cs.disasm(code, start):
    note = ''
    if ins.mnemonic.startswith('bl') and ins.op_str.startswith('#'):
        t = int(ins.op_str[1:], 16); note = stubs.get(t, '')
    if ('pc' in ins.op_str) and ins.mnemonic.startswith(('ldr', 'vldr')) and '[pc' in ins.op_str:
        try:
            disp = int(ins.op_str.split('#')[-1].rstrip(']'), 16) if '#' in ins.op_str else 0
            a = ((ins.address + 4) & ~3) + disp
            q = struct.unpack_from('<Q', data, off(a))[0]
            note = f'lit@{a:#x} u32={q & 0xffffffff:#x} f32={struct.unpack("<f", struct.pack("<I", q & 0xffffffff))[0]:g} f64={struct.unpack("<d", struct.pack("<Q", q))[0]:g}'
        except Exception as e: note = str(e)
    print(f'{ins.address:#x}: {ins.mnemonic:8} {ins.op_str:40} {note}')
