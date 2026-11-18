"""LZVN decoder (Apple's lzvn format, as used by CoreUI asset catalogs)."""


def decode(src, out_size=None):
    dst = bytearray()
    i, n = 0, len(src)
    d = 0  # previous match distance
    while i < n:
        op = src[i]
        if op == 0x06:                       # end of stream
            break
        hi = op >> 4
        if op in (0x0e, 0x16):               # nop
            i += 1
            continue
        if op & 0xf0 == 0xe0 or op == 0xe0:  # literal
            if op == 0xe0:
                L = src[i + 1] + 16
                i += 2
            else:
                L = op & 0x0f
                i += 1
            dst += src[i:i + L]
            i += L
            continue
        if op & 0xf0 == 0xf0:                # match with previous distance
            if op == 0xf0:
                M = src[i + 1] + 16
                i += 2
            else:
                M = op & 0x0f
                i += 1
            _copy(dst, d, M)
            continue
        if op & 0xf0 == 0x70 or op & 0xf0 == 0xd0:  # undefined
            raise ValueError('bad opcode %02x at %d' % (op, i))
        if op & 0xe0 == 0xa0:                # medium distance
            b1, b2 = src[i + 1], src[i + 2]
            L = (op >> 3) & 3
            M = ((op & 7) << 2 | (b1 & 3)) + 3
            dist = (b1 >> 2) | (b2 << 6)
            i += 3
        elif op & 7 == 7:                    # large distance
            L = op >> 6
            M = ((op >> 3) & 7) + 3
            dist = src[i + 1] | (src[i + 2] << 8)
            i += 3
        elif op & 7 == 6:                    # previous distance
            L = op >> 6
            M = ((op >> 3) & 7) + 3
            dist = d
            i += 1
        else:                                # small distance
            L = op >> 6
            M = ((op >> 3) & 7) + 3
            dist = ((op & 7) << 8) | src[i + 1]
            i += 2
        dst += src[i:i + L]
        i += L
        d = dist
        _copy(dst, d, M)
    return bytes(dst)


def _copy(dst, dist, m):
    start = len(dst) - dist
    if dist >= m:
        dst += dst[start:start + m]
    else:
        for k in range(m):
            dst.append(dst[start + k])
