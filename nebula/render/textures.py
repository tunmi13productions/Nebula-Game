"""Finds and loads the original images by name, the way SKTexture and UIImage imageNamed: did.

Lookup order: the gameTextures atlas, then the loose bundle images (png, then jpg), then the asset catalog.
Atlas entries are trimmed and may be stored rotated; they're restored to their full source size here.
"""
import os
import plistlib
import re

import pygame

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'images')
ATLAS = 'gameTextures.atlasc'


def _numbers(text):
    return [float(v) for v in re.findall(r'-?[\d.]+', text)]


class TextureStore:
    def __init__(self, root=ROOT):
        self.root = root
        self._cache = {}
        self._sheets = {}
        self.atlas = {}
        plist = os.path.join(root, ATLAS, 'gameTextures.plist')
        if os.path.exists(plist):
            with open(plist, 'rb') as f:
                data = plistlib.load(f)
            for sheet in data['images']:
                for sub in sheet['subimages']:
                    entry = (sheet['path'], sub)
                    self.atlas[sub['name']] = entry
                    self.atlas[os.path.splitext(sub['name'])[0]] = entry

    def exists(self, name):
        return self._atlas_entry(name) is not None or self._path(name) is not None

    def get(self, name):
        """A pygame Surface with alpha, or None if there's no such image."""
        if name in self._cache:
            return self._cache[name]
        surface = None
        entry = self._atlas_entry(name)
        if entry is not None:
            surface = self._from_atlas(*entry)
        else:
            path = self._path(name)
            if path is not None:
                surface = pygame.image.load(path)
        if surface is not None and pygame.display.get_surface() is not None:
            surface = surface.convert_alpha()
        self._cache[name] = surface
        return surface

    def get_particle(self, name):
        """A particle's texture. SKEmitterNode drew atlas textures as stored in the sheet, so a texture the
        atlas keeps turned a quarter clockwise shows turned; the original's emitters (the background ships)
        add a quarter turn of particle rotation that stands them up again."""
        key = ('particle', name)
        if key in self._cache:
            return self._cache[key]
        surface = self.get(name)
        entry = self._atlas_entry(name)
        if surface is not None and entry is not None and entry[1].get('textureRotated', False):
            surface = pygame.transform.rotate(surface, -90)
        self._cache[key] = surface
        return surface

    def _atlas_entry(self, name):
        return self.atlas.get(name) or self.atlas.get(os.path.splitext(name)[0])

    def _path(self, name):
        base, ext = os.path.splitext(name)
        candidates = [name] if ext in ('.png', '.jpg') else [name + '.png', name + '.jpg']
        for c in candidates:
            for folder in (self.root, os.path.join(self.root, 'catalog')):
                p = os.path.join(folder, c)
                if os.path.exists(p):
                    return p
        return None

    def _from_atlas(self, sheet_name, sub):
        sheet = self._sheets.get(sheet_name)
        if sheet is None:
            sheet = self._sheets[sheet_name] = pygame.image.load(os.path.join(self.root, ATLAS, sheet_name))
        x, y, w, h = _numbers(sub['textureRect'])
        piece = sheet.subsurface(pygame.Rect(int(x), int(y), int(w), int(h))).copy()
        if sub.get('textureRotated', False):
            # textureRect is the stored, turned rectangle; the image is turned back a quarter
            piece = pygame.transform.rotate(piece, 90)
            w, h = h, w
        src_w, src_h = _numbers(sub['spriteSourceSize'])
        ox, oy = _numbers(sub['spriteOffset'])
        full = pygame.Surface((int(src_w), int(src_h)), pygame.SRCALPHA)
        # spriteOffset: the trimmed piece's centre relative to the source centre, y up
        full.blit(piece, (round(src_w / 2 + ox - w / 2), round(src_h / 2 - oy - h / 2)))
        return full
