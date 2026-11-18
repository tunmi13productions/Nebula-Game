"""Copies the original game's images into images/.

- The iPhone images from the bundle root (png and jpg), unchanged. iPad-only files, app icons and the
  low-quality "tch_" copies are left out, since the port always uses the full-quality set.
- The gameTextures texture atlas (its sheets and plist), unchanged.
- The bitmaps of the compiled asset catalog (Assets.car), decoded to png in images/catalog/. They're BGRA
  with premultiplied alpha, which is undone here.
- HACKED_Title.ttf, the bundled font.

Most bundle pngs are Apple "CgBI" pngs (made by Xcode for iPhones): BGRA, premultiplied alpha, and deflate data
without a zlib header. They're converted to standard pngs on the way.

usage: python -I tools/extract_images.py   (from the repository root, with the ipa unpacked in decompiled/ipa)
"""
import os
import shutil
import struct
import sys
import zlib

import numpy
import pygame

sys.path.insert(0, os.path.join('tools', 're'))
from car import Car  # noqa: E402

APP = os.path.join('decompiled', 'ipa', 'Payload', 'BEPiDGame.app')
OUT = 'images'
RENAMED = {'as.png': 'mais.png'}


def wanted(name):
    low = name.lower()
    if not low.endswith(('.png', '.jpg')):
        return False
    if low.startswith(('tch_', 'appicon')) or 'ipad' in low or low.startswith('launchimage-700-portrait'):
        return False
    return True


def is_cgbi(path):
    with open(path, 'rb') as f:
        return f.read(40).find(b'CgBI') >= 0


def decode_cgbi(path):
    """Returns (width, height, BGRA premultiplied bytes) of an Apple CgBI png."""
    with open(path, 'rb') as f:
        data = f.read()
    pos, idat, w = 8, b'', 0
    while pos < len(data):
        n, kind = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if kind == b'IHDR':
            w, h, depth, ctype = struct.unpack('>IIBB', body[:10])
            if depth != 8 or ctype != 6:
                raise ValueError('%s: unsupported png type %d/%d' % (path, depth, ctype))
        elif kind == b'IDAT':
            idat += body
        elif kind == b'IEND':
            break
        pos += 12 + n
    raw = zlib.decompress(idat, -15)
    stride = w * 4
    out = numpy.zeros((h, stride), dtype=numpy.int32)
    prev = numpy.zeros(stride, dtype=numpy.int32)
    for y in range(h):
        f = raw[y * (stride + 1)]
        line = numpy.frombuffer(raw, dtype=numpy.uint8, count=stride, offset=y * (stride + 1) + 1).astype(numpy.int32)
        cur = line.copy()
        if f == 1 or f == 3 or f == 4:
            for x in range(stride):
                a = cur[x - 4] if x >= 4 else 0
                if f == 1:
                    cur[x] = (line[x] + a) & 255
                elif f == 3:
                    cur[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
                else:
                    b, c = prev[x], (prev[x - 4] if x >= 4 else 0)
                    pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                    pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                    cur[x] = (line[x] + pred) & 255
        elif f == 2:
            cur = (line + prev) & 255
        out[y] = cur
        prev = cur
    return w, h, out.astype(numpy.uint8).tobytes()


def unpremultiply_bgra(raw, w, h):
    a = numpy.frombuffer(raw, dtype=numpy.uint8).reshape(h, w, 4).astype(numpy.float32)
    alpha = a[:, :, 3:4]
    rgb = numpy.where(alpha > 0, numpy.clip(a[:, :, :3] * 255.0 / numpy.maximum(alpha, 1), 0, 255), 0)
    out = numpy.concatenate([rgb[:, :, 2:3], rgb[:, :, 1:2], rgb[:, :, 0:1], alpha], axis=2)
    return out.astype(numpy.uint8).tobytes()


def main():
    os.makedirs(os.path.join(OUT, 'catalog'), exist_ok=True)
    copied = 0
    converted = 0
    for name in sorted(os.listdir(APP)):
        if wanted(name):
            src = os.path.join(APP, name)
            if name.lower().endswith('.png') and is_cgbi(src):
                w, h, raw = decode_cgbi(src)
                surface = pygame.image.frombuffer(unpremultiply_bgra(raw, w, h), (w, h), 'RGBA')
                pygame.image.save(surface, os.path.join(OUT, name))
                converted += 1
            else:
                shutil.copy2(src, os.path.join(OUT, name))
            copied += 1
    atlas = os.path.join(OUT, 'gameTextures.atlasc')
    if os.path.isdir(atlas):
        shutil.rmtree(atlas)
    shutil.copytree(os.path.join(APP, 'gameTextures.atlasc'), atlas)
    shutil.copy2(os.path.join(APP, 'HACKED_Title.ttf'), os.path.join(OUT, 'HACKED_Title.ttf'))
    decoded = 0
    for name, w, h, raw in Car(os.path.join(APP, 'Assets.car')).bitmaps():
        if 'ipad' in name.lower():
            continue
        # The catalog's "mais" image (the green plus button) is stored under the rendition name "as.png".
        name = RENAMED.get(name, name)
        surface = pygame.image.frombuffer(unpremultiply_bgra(raw, w, h), (w, h), 'RGBA')
        pygame.image.save(surface, os.path.join(OUT, 'catalog', name))
        decoded += 1
    print('copied', copied, 'images (%d converted from CgBI), the atlas and the font; decoded' % converted, decoded,
          'catalog images')


if __name__ == '__main__':
    main()
