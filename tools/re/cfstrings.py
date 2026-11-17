import sys, struct, lief
b = lief.MachO.parse(sys.argv[1]).at(0)
data = open(sys.argv[1], 'rb').read()
segs = [(s.virtual_address, s.virtual_address + s.file_size, s.file_offset) for s in b.segments]
def off(va):
    for a, e, o in segs:
        if a <= va < e: return o + va - a
s = [x for x in b.sections if x.name == '__cfstring'][0]
for i in range(s.size // 16):
    va = s.virtual_address + 16 * i
    _, flags, ptr, ln = struct.unpack_from('<IIII', data, off(va))
    o = off(ptr)
    if flags == 0x7d0:
        txt = data[o:o + ln * 2].decode('utf-16-le', 'replace')
    else:
        txt = data[o:o + ln].decode('utf-8', 'replace')
    print(f'{va:#x}\t{txt!r}')
