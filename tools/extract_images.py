"""Copies the original game's images into images/.

- The iPhone images from the bundle root (png and jpg), unchanged. iPad-only files, app icons and the
  low-quality "tch_" copies are left out, since the port always uses the full-quality set.
- The gameTextures texture atlas (its sheets and plist), unchanged.
- The bitmaps of the compiled asset catalog (Assets.car), decoded to png in images/catalog/. They're BGRA
  with premultiplied alpha, which is undone here.
- HACKED_Title.ttf, the bundled font.

usage: python -I tools/extract_images.py   (from the repository root, with the ipa unpacked in decompiled/ipa)
"""
import os
import shutil
import sys

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


def unpremultiply_bgra(raw, w, h):
    a = numpy.frombuffer(raw, dtype=numpy.uint8).reshape(h, w, 4).astype(numpy.float32)
    alpha = a[:, :, 3:4]
    rgb = numpy.where(alpha > 0, numpy.clip(a[:, :, :3] * 255.0 / numpy.maximum(alpha, 1), 0, 255), 0)
    out = numpy.concatenate([rgb[:, :, 2:3], rgb[:, :, 1:2], rgb[:, :, 0:1], alpha], axis=2)
    return out.astype(numpy.uint8).tobytes()


def main():
    os.makedirs(os.path.join(OUT, 'catalog'), exist_ok=True)
    copied = 0
    for name in sorted(os.listdir(APP)):
        if wanted(name):
            shutil.copy2(os.path.join(APP, name), os.path.join(OUT, name))
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
    print('copied', copied, 'images, the atlas and the font; decoded', decoded, 'catalog images')


if __name__ == '__main__':
    main()
