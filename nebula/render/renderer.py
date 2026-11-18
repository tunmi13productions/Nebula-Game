"""Draws a scene graph the way SpriteKit did: y up, nodes drawn by global z (parent z plus own z) and then in
tree order, with position, scale, rotation and alpha inherited from parents and the anchor point applied.

A node is drawn when it has a texture name (node.texture) or a fill colour (node.color, RGBA from 0 to 1). A
texture is tinted by node.tint (RGB from 0 to 1) when node.color_blend is above 0, like colorBlendFactor.
Points are converted to pixels with the window scale.
"""
import math

import pygame

SCENE_BACKGROUND = (0.15, 0.15, 0.15)   # SKScene's default backgroundColor


class Renderer:
    def __init__(self, textures, scale):
        self.textures = textures
        self.scale = scale
        self._scaled = {}

    def draw_scene(self, scene, surface):
        bg = getattr(scene, 'background', None) or SCENE_BACKGROUND
        surface.fill([int(c * 255) for c in bg[:3]])
        items = []
        self._collect(scene, 0.0, (0.0, 0.0), 1.0, 0.0, 1.0, items, [0])
        items.sort(key=lambda it: (it[0], it[1]))
        for _, _, node, pos, scale, rot, alpha in items:
            self._draw_node(surface, node, pos, scale, rot, alpha, scene.size[1])

    def _collect(self, node, z, pos, scale, rot, alpha, items, counter):
        if node.hidden or node.alpha <= 0.0:
            return
        if node.parent is None:
            gz, wpos, wscale, wrot, walpha = node.z, (0.0, 0.0), 1.0, 0.0, 1.0
        else:
            x, y = node.position
            c, s = math.cos(rot), math.sin(rot)
            gz = z + node.z
            wpos = (pos[0] + scale * (x * c - y * s), pos[1] + scale * (x * s + y * c))
            wscale, wrot, walpha = scale * node.scale, rot + node.rotation, alpha * node.alpha
        counter[0] += 1
        if getattr(node, 'texture', None) or getattr(node, 'color', None):
            items.append((gz, counter[0], node, wpos, wscale, wrot, walpha))
        for child in list(node.children):
            self._collect(child, gz, wpos, wscale, wrot, walpha, items, counter)

    def _draw_node(self, surface, node, pos, scale, rot, alpha, height):
        k = self.scale
        name = getattr(node, 'texture', None)
        tex = self.textures.get(name) if name else None
        w, h = node.size
        if (w <= 0 or h <= 0) and tex is not None:
            w, h = tex.get_size()
        w, h = w * scale * k, h * scale * k
        if w < 1 or h < 1:
            return
        iw, ih = int(round(w)), int(round(h))
        if tex is not None:
            img = self._sized(name, tex, iw, ih)
            blend = getattr(node, 'color_blend', 0.0)
            if blend > 0.0 and getattr(node, 'tint', None):
                img = self._tinted(img, node.tint, blend)
        elif getattr(node, 'color', None):
            img = pygame.Surface((iw, ih), pygame.SRCALPHA)
            r, g, b = (int(c * 255) for c in node.color[:3])
            a = node.color[3] if len(node.color) > 3 else 1.0
            img.fill((r, g, b, int(a * 255)))
        else:
            return
        ax, ay = node.anchor
        px, py = pos[0] * k, (height - pos[1]) * k
        if rot:
            # the image centre relative to the anchor, turned with the node (screen y points down)
            dx, dy = (0.5 - ax) * iw, (ay - 0.5) * ih
            c, s = math.cos(rot), math.sin(rot)
            cx, cy = px + dx * c + dy * s, py - dx * s + dy * c
            img = pygame.transform.rotate(img, math.degrees(rot))
            rect = img.get_rect(center=(round(cx), round(cy)))
        else:
            rect = pygame.Rect(round(px - ax * iw), round(py - (1 - ay) * ih), iw, ih)
        if alpha < 1.0:
            img = img.copy()
            img.set_alpha(int(alpha * 255))
        surface.blit(img, rect)

    @staticmethod
    def _tinted(img, tint, blend):
        """colorBlendFactor: the texture's colour multiplied by the tint, mixed in by the blend factor."""
        mult = [int(round(255 * (1.0 - blend + blend * c))) for c in tint[:3]]
        out = img.copy()
        out.fill(mult + [255], special_flags=pygame.BLEND_RGBA_MULT)
        return out

    def _sized(self, name, tex, w, h):
        key = (name, w, h)
        img = self._scaled.get(key)
        if img is None:
            img = tex if tex.get_size() == (w, h) else pygame.transform.smoothscale(tex, (w, h))
            if len(self._scaled) > 2000:
                self._scaled.clear()
            self._scaled[key] = img
        return img
