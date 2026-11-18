"""Minimal NIBArchive dumper: prints each object's class and its string-ish values."""
import struct, sys
def varint(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1
        r |= (c & 0x7f) << s; s += 7
        if c & 0x80: return r, i
def load(path):
    b = open(path, 'rb').read()
    assert b[:10] == b'NIBArchive', path
    h = struct.unpack('<10I', b[10:50])
    _, _, no, oo, nk, ko, nv, vo, nc, co = h
    keys = []; i = ko
    for _ in range(nk):
        n, i = varint(b, i); keys.append(b[i:i+n].decode()); i += n
    vals = []; i = vo
    for _ in range(nv):
        k, i = varint(b, i); t = b[i]; i += 1
        if t == 0: v = b[i]; i += 1
        elif t == 1: v = struct.unpack('<h', b[i:i+2])[0]; i += 2
        elif t == 2: v = struct.unpack('<i', b[i:i+4])[0]; i += 4
        elif t == 3: v = struct.unpack('<q', b[i:i+8])[0]; i += 8
        elif t in (4, 5): v = bool(t == 5)
        elif t == 6: v = struct.unpack('<f', b[i:i+4])[0]; i += 4
        elif t == 7: v = struct.unpack('<d', b[i:i+8])[0]; i += 8
        elif t == 8:
            n, i = varint(b, i); v = b[i:i+n]; i += n
        elif t == 9: v = None
        elif t == 10: v = ('obj', struct.unpack('<I', b[i:i+4])[0]); i += 4
        else: raise ValueError(t)
        vals.append((keys[k], v))
    classes = []; i = co
    for _ in range(nc):
        n, i = varint(b, i); ex, i = varint(b, i); i += 4 * ex
        classes.append(b[i:i+n].rstrip(b'\0').decode()); i += n
    objs = []; i = oo
    for _ in range(no):
        c, i = varint(b, i); s, i = varint(b, i); n, i = varint(b, i)
        objs.append((classes[c], vals[s:s+n]))
    return objs
if __name__ == '__main__':
    objs = load(sys.argv[1])
    for idx, (c, vs) in enumerate(objs):
        out = []
        for k, v in vs:
            if isinstance(v, bytes):
                try:
                    t = v.decode('utf-8')
                    if t.isprintable() and t.strip(): out.append('%s=%r' % (k, t))
                except UnicodeDecodeError: pass
            elif isinstance(v, tuple): out.append('%s->%d' % (k, v[1]))
            elif v is not None and not isinstance(v, bytes) and k in ('UITag','UIEnabled','UIAccessibilityElementsHidden','UIIsAccessibilityElement'): out.append('%s=%s' % (k, v))
        print(idx, c, '; '.join(out))
