"""Reads a CoreUI asset catalog (Assets.car): the BOM store, its trees, and the bitmap renditions.

Renditions here are BGRA with premultiplied alpha, compressed with LZVN (CELM compression 3), either in one
block or as KCBC row chunks.
"""
import struct

from lzvn import decode as lzvn_decode


class Car:
    def __init__(self, path):
        d = self.d = open(path, 'rb').read()
        _, _, _, idx_off, _, vars_off, _ = struct.unpack('>8sIIIIII', d[:32])
        count = struct.unpack('>I', d[idx_off:idx_off + 4])[0]
        self.blocks = [struct.unpack('>II', d[idx_off + 4 + 8 * i: idx_off + 12 + 8 * i]) for i in range(count)]
        nv = struct.unpack('>I', d[vars_off:vars_off + 4])[0]
        p = vars_off + 4
        self.vars = {}
        for _ in range(nv):
            bi, ln = struct.unpack('>IB', d[p:p + 5])
            self.vars[d[p + 5:p + 5 + ln].decode()] = bi
            p += 5 + ln

    def block(self, i):
        a, n = self.blocks[i]
        return self.d[a:a + n]

    def tree(self, name):
        t = self.block(self.vars[name])
        child = struct.unpack('>I', t[8:12])[0]
        out = []
        b = self.block(child)
        while True:
            isleaf, cnt, fwd, _ = struct.unpack('>HHII', b[:12])
            if not isleaf:
                b = self.block(struct.unpack('>I', b[12:16])[0])
                continue
            for i in range(cnt):
                v, k = struct.unpack('>II', b[12 + 8 * i:20 + 8 * i])
                out.append((self.block(k), self.block(v)))
            if not fwd:
                return out
            b = self.block(fwd)

    def bitmaps(self):
        """Yields (name, width, height, BGRA premultiplied bytes) for every bitmap rendition."""
        for _, v in self.tree('RENDITIONS'):
            if v[:4] != b'ISTC':
                continue
            w, h = struct.unpack('<II', v[12:20])
            name = v[40:168].rstrip(b'\0').decode()
            i = v.find(b'MLEC')
            if i < 0:
                continue
            flags, comp, ln = struct.unpack('<III', v[i + 4:i + 16])
            if comp != 3:
                raise ValueError('%s: compression %d not supported' % (name, comp))
            if flags == 0:
                raw = lzvn_decode(v[i + 16:i + 16 + ln])
            else:
                raw, p = b'', i + 16
                for _ in range(ln):
                    tag, _, _, _, clen = struct.unpack('<4sIIII', v[p:p + 20])
                    raw += lzvn_decode(v[p + 20:p + 20 + clen])
                    p += 20 + clen
            yield name, w, h, raw
