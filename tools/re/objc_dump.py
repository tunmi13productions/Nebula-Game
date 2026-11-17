# 32-bit Objective-C class dumper for Mach-O armv7
import sys, struct, lief
b = lief.MachO.parse(sys.argv[1]).at(0)
data = open(sys.argv[1], 'rb').read()
segs = [(s.virtual_address, s.virtual_address + s.file_size, s.file_offset) for s in b.segments]
def off(va):
    for a, e, o in segs:
        if a <= va < e: return o + va - a
    return None
def u32(va):
    o = off(va); return struct.unpack_from('<I', data, o)[0] if o is not None else 0
def cstr(va):
    o = off(va)
    if o is None: return '?'
    e = data.index(b'\0', o); return data[o:e].decode('utf-8', 'replace')
binds = {}
for bi in b.bindings:
    try:
        binds[bi.address] = bi.symbol.name
    except Exception: pass
sec = {s.name: s for s in b.sections}
def classname(cls):
    ro = u32(cls + 16) & ~3
    return cstr(u32(ro + 16))
def methods(ml):
    out = []
    if not ml: return out
    ent, cnt = u32(ml) & 0xffff, u32(ml + 4)
    for i in range(cnt):
        p = ml + 8 + i * ent
        out.append((cstr(u32(p)), cstr(u32(p + 4)), u32(p + 8)))
    return out
def protos(pl):
    if not pl: return []
    n = u32(pl); return [cstr(u32(u32(pl + 4 + 4 * i) + 4)) for i in range(n)]
out = []
cl = sec['__objc_classlist']
for i in range(cl.size // 4):
    va = cl.virtual_address + 4 * i
    cls = u32(va)
    ro = u32(cls + 16) & ~3
    name = cstr(u32(ro + 16))
    sup = u32(cls + 4)
    supn = classname(sup) if sup else binds.get(cls + 4, '?').replace('_OBJC_CLASS_$_', '')
    out.append(f'@interface {name} : {supn}  // instanceSize {u32(ro+8)}')
    pr = protos(u32(ro + 24))
    if pr: out.append('  protocols: ' + ', '.join(pr))
    iv = u32(ro + 28)
    if iv:
        ent, cnt = u32(iv), u32(iv + 4)
        for j in range(cnt):
            p = iv + 8 + j * ent
            out.append(f'  ivar {cstr(u32(p+4))} {cstr(u32(p+8))} @offset {u32(u32(p))}')
    pl = u32(ro + 36)
    if pl:
        ent, cnt = u32(pl), u32(pl + 4)
        for j in range(cnt):
            p = pl + 8 + j * ent
            out.append(f'  property {cstr(u32(p))} {cstr(u32(p+4))}')
    meta = u32(cls)
    if meta:
        mro = u32(meta + 16) & ~3
        for n, t, imp in methods(u32(mro + 20)):
            out.append(f'  + {n}  {t}  imp {imp:#x}')
    for n, t, imp in methods(u32(ro + 20)):
        out.append(f'  - {n}  {t}  imp {imp:#x}')
    out.append('@end\n')
cat = sec['__objc_catlist']
for i in range(cat.size // 4):
    c = u32(cat.virtual_address + 4 * i)
    tgt = u32(c + 4)
    tn = classname(tgt) if tgt else binds.get(c + 4, '?').replace('_OBJC_CLASS_$_', '')
    out.append(f'@category {tn} ({cstr(u32(c))})')
    for n, t, imp in methods(u32(c + 8)): out.append(f'  - {n}  {t}  imp {imp:#x}')
    for n, t, imp in methods(u32(c + 12)): out.append(f'  + {n}  {t}  imp {imp:#x}')
    out.append('@end\n')
print('\n'.join(out))
