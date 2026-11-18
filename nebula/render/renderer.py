"""Draws a scene graph the way SpriteKit did: y up, nodes drawn by global z (parent z plus own z) and then in
tree order, with position, scale, rotation and alpha inherited from parents and the anchor point applied.

A node is drawn when it has a texture name (node.texture) or a fill colour (node.color, RGBA from 0 to 1). A
texture is tinted by node.tint (RGB from 0 to 1) when node.color_blend is above 0, like colorBlendFactor.
node.blend_mode 'add' draws additively, like SKBlendModeAdd. Emitters (nodes with particles) draw their
particles.
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
        if getattr(node, 'texture', None) or getattr(node, 'color', None) or getattr(node, 'particles', None):
            items.append((gz, counter[0], node, wpos, wscale, wrot, walpha))
        for child in list(node.children):
            self._collect(child, gz, wpos, wscale, wrot, walpha, items, counter)

    def _draw_node(self, surface, node, pos, scale, rot, alpha, height):
        if getattr(node, 'particles', None) is not None:
            self._draw_particles(surface, node, pos, scale, rot, alpha, height)
            return
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
        if getattr(node, 'blend_mode', None) == 'add':
            # SKBlendModeAdd: the colours, weighted by alpha, add onto what's below
            img = img.premul_alpha()
            if alpha < 1.0:
                img.fill([int(alpha * 255)] * 3 + [255], special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(img, rect, special_flags=pygame.BLEND_RGB_ADD)
            return
        if alpha < 1.0:
            img = img.copy()
            img.set_alpha(int(alpha * 255))
        surface.blit(img, rect)

    def _draw_particles(self, surface, emitter, pos, scale, rot, alpha, height):
        """An SKEmitterNode's particles: the texture at its own size times each particle's scale, tinted by the
        particle colour and blend factor, with additive blending for blend mode 1."""
        p = emitter.params
        tex = self.textures.get(p['texture']) if p.get('texture') else None
        if tex is None:
            return
        k = self.scale
        tw, th = tex.get_size()
        add = p.get('blend_mode') == 1
        c, s = math.cos(rot), math.sin(rot)
        for q in emitter.particles:
            xs, ys = getattr(emitter, 'xscale', 1.0), getattr(emitter, 'yscale', 1.0)
            if emitter.target is None:
                px, py = q.x * xs, q.y * ys
                x = pos[0] + scale * (px * c - py * s)
                y = pos[1] + scale * (px * s + py * c)
                size = q.scale * scale
            else:
                x, y, size = q.x, q.y, q.scale
            color = emitter.color_of(q)
            a = q.alpha * alpha * (color[3] if len(color) > 3 else 1.0)
            if a <= 0.01 or size <= 0:
                continue
            w, h = max(1, int(tw * size * k)), max(1, int(th * size * k))
            img = self._particle_image(p['texture'], tex, w, h, color, q.blend, q.rotation + rot, a, add,
                                       (xs, ys))
            rect = img.get_rect(center=(round(x * k), round((height - y) * k)))
            surface.blit(img, rect, special_flags=pygame.BLEND_RGB_ADD if add else 0)

    def _particle_image(self, name, tex, w, h, color, blend, rotation, alpha, add, stretch=(1.0, 1.0)):
        """A particle's picture, cached at coarse steps of colour, blend, rotation and alpha, with the alpha
        already applied (premultiplied for additive blending)."""
        cq = tuple(int(v * 15 + 0.5) for v in color[:3])
        bq = int(blend * 8 + 0.5)
        rq = int(math.degrees(rotation) / 10) % 36 if rotation else 0
        aq = int(alpha * 16 + 0.5)
        key = ('p', name, w, h, cq, bq, rq, aq, add, stretch)
        img = self._scaled.get(key)
        if img is None:
            img = self._sized(name, tex, w, h)
            if bq:
                img = self._tinted(img, [v / 15 for v in cq], bq / 8)
            if rq:
                img = pygame.transform.rotate(img, rq * 10)
            if stretch != (1.0, 1.0):
                # the emitter node's xScale and yScale apply after each particle's own rotation
                sw, sh = img.get_size()
                img = pygame.transform.smoothscale(img, (max(1, int(sw * stretch[0])), max(1, int(sh * stretch[1]))))
            if add:
                img = img.premul_alpha()
                img.fill([min(255, aq * 16)] * 3 + [255], special_flags=pygame.BLEND_RGBA_MULT)
            elif aq < 16:
                img = img.copy()
                img.set_alpha(aq * 16)
            if len(self._scaled) > 6000:
                self._scaled.clear()
            self._scaled[key] = img
        return img

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
