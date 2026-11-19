"""Builds the right door pictures with SYSTEMS (SISTEMAS in Portuguese) in place of MULTIPLAYER.

A port addition (DEVIATIONS.md, "Settings screen"): the Multiplayer slot on the main menu's doors opens
the Settings screen. The painted word is covered with the door metal from just above and below it, blended
across the strip, and the new word is spelled on top with the game's orange letter pictures (AlfabetoAct_).

Writes images/rightDoorSystems_en_4.png and images/rightDoorSystems_4.png.
usage: python tools/make_systems_door.py   (from the repository root)
"""
import os

import pygame

# source door, output, word, the painted word's strip (top, bottom, left, right) in door pixels
DOORS = (
    ('rightDoor_en_4.jpg', 'rightDoorSystems_en_4.png', 'SYSTEMS', (330, 352, 35, 181)),
    ('rightDoor_4.jpg', 'rightDoorSystems_4.png', 'SISTEMAS', (549, 586, 56, 303)),
)
PAD = 6          # the glow around the painted letters
LETTER = 1.85   # letter height as a multiple of the painted word's height
GAP = -0.14      # space between letters, as a share of the letter height


def cover(door, top, bottom, left, right):
    """Each column of the strip becomes a blend from the metal just above it to the metal just below it
    (each the average of three rows), so the strip's edges match the door; the door's own grain is mixed
    back in from the rows above, at low strength, so the fill isn't flat."""
    top, bottom = top - PAD, bottom + PAD
    left, right = max(0, left - PAD), min(door.get_width(), right + PAD)
    h = bottom - top
    def edge(x, ys):
        cs = [door.get_at((x, y)) for y in ys]
        return [sum(c[i] for c in cs) / len(cs) for i in range(3)]
    for x in range(left, right):
        a = edge(x, range(top - 3, top))
        b = edge(x, range(bottom, bottom + 3))
        grain = [door.get_at((x, top - h + y)) for y in range(h)]
        mean = [sum(g[i] for g in grain) / h for i in range(3)]
        for y in range(h):
            t = (y + 0.5) / h
            c = [a[i] * (1 - t) + b[i] * t + 0.5 * (grain[y][i] - mean[i]) for i in range(3)]
            door.set_at((x, top + y), tuple(max(0, min(255, round(v))) for v in c))


def spell(door, word, top, bottom, left, right):
    height = (bottom - top) * LETTER
    letters = []
    for ch in word:
        img = pygame.image.load(os.path.join('images', 'AlfabetoAct_%s.png' % ch)).convert_alpha()
        w = img.get_width() * height / img.get_height()
        letters.append(pygame.transform.smoothscale(img, (round(w), round(height))))
    gap = height * GAP
    total = sum(i.get_width() for i in letters) + gap * (len(letters) - 1)
    x = (left + right) / 2 - total / 2
    y = (top + bottom) / 2 - height / 2
    for img in letters:
        door.blit(img, (round(x), round(y)))
        x += img.get_width() + gap


def main():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    for source, out, word, (top, bottom, left, right) in DOORS:
        door = pygame.image.load(os.path.join('images', source)).convert()
        cover(door, top, bottom, left, right)
        spell(door, word, top, bottom, left, right)
        pygame.image.save(door, os.path.join('images', out))
        print('wrote', out)


if __name__ == '__main__':
    main()
