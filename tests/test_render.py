"""The renderer and texture store, drawn to an off-screen surface."""
import math

import pygame

from nebula.engine.nodes import Node, Scene
from nebula.render.renderer import Renderer
from nebula.render.textures import TextureStore

STORE = TextureStore()


def draw(*nodes, scale=1.0):
    scene = Scene(320, 568)
    for n in nodes:
        scene.add_child(n)
    surface = pygame.Surface((round(320 * scale), round(568 * scale)))
    Renderer(STORE, scale).draw_scene(scene, surface)
    return surface


def box(pos, size, color, **kw):
    n = Node(position=pos, size=size)
    n.color = color
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def test_y_points_up_and_the_anchor_is_the_centre():
    s = draw(box((50, 100), (20, 20), (1, 0, 0)))
    assert s.get_at((50, 568 - 100))[:3] == (255, 0, 0)
    assert s.get_at((50, 568 - 112))[:3] != (255, 0, 0)


def test_children_inherit_position_scale_and_alpha():
    parent = box((100, 100), (10, 10), (0, 0, 1), scale=2.0, alpha=0.5)
    child = box((20, 0), (4, 4), (0, 1, 0))
    parent.add_child(child)
    s = draw(parent)
    r, g, b, _ = s.get_at((140, 568 - 100))
    assert g > 100 and r < 60          # the child sits 20 x 2 points to the right, half transparent


def test_rotation_turns_anticlockwise():
    s = draw(box((160, 284), (100, 10), (1, 1, 1), rotation=math.pi / 2))
    assert s.get_at((160, 284 - 40))[:3] == (255, 255, 255)
    assert s.get_at((200, 284))[:3] != (255, 255, 255)


def test_higher_z_draws_on_top():
    s = draw(box((50, 50), (20, 20), (1, 0, 0), z=2), box((50, 50), (20, 20), (0, 0, 1), z=1))
    assert s.get_at((50, 568 - 50))[:3] == (255, 0, 0)


def test_window_scale():
    s = draw(box((100, 100), (10, 10), (1, 0, 0)), scale=1.5)
    assert s.get_at((150, round((568 - 100) * 1.5)))[:3] == (255, 0, 0)


def test_textures_come_from_the_atlas_the_bundle_and_the_catalog():
    ship = STORE.get('SpaceShips_37')      # a rotated atlas entry, restored to its source size
    assert ship.get_size() == (132, 269)
    assert STORE.get('leftDoor').get_size() == (531, 1229)
    assert STORE.get('nebulaMenu1').get_size() == (640, 1136)
    assert STORE.get('no such image') is None
