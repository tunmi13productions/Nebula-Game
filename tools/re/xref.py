"""Finds code that computes the given addresses with movw, movt and add pc, the way the binary loads
selector references, cfstrings and block functions. Ghidra misses some blocks; this finds them.

usage: python -I tools/re/xref.py <hex address> [...]   (from the repository root)
"""
import sys, lief, capstone
path = 'decompiled/ipa/Payload/BEPiDGame.app/BEPiDGame'
targets = {int(a, 16) for a in sys.argv[1:]}
b = lief.MachO.parse(path).at(0)
data = open(path, 'rb').read()
text = [s for s in b.sections if s.name == '__text'][0]
seg = [s for s in b.segments if s.virtual_address <= text.virtual_address < s.virtual_address + s.virtual_size][0]
o = seg.file_offset + text.virtual_address - seg.virtual_address
code = data[o:o + text.size]
cs = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
regs = {}
addr = text.virtual_address
end = addr + text.size
while addr < end:
    got = False
    for ins in cs.disasm(code[addr - text.virtual_address:addr - text.virtual_address + 64], addr):
        got = True
        m, ops = ins.mnemonic, ins.op_str.replace(' ', '').split(',')
        if m.startswith('movw') and len(ops) == 2 and ops[1].startswith('#'):
            regs[ops[0]] = int(ops[1][1:], 0)
        elif m.startswith('movt') and len(ops) == 2 and ops[0] in regs:
            regs[ops[0]] = (regs[ops[0]] & 0xffff) | (int(ops[1][1:], 0) << 16)
        elif m == 'add' and len(ops) == 2 and ops[1] == 'pc' and ops[0] in regs:
            t = (regs.pop(ops[0]) + ins.address + 4) & 0xffffffff
            if t in targets:
                print(hex(t), 'referenced at', hex(ins.address))
        addr = ins.address + ins.size
    if not got:
        addr += 2
