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


def test_ships_carry_their_pictures_and_the_player_banks():
    from nebula.game.free_mode import FreeModeScene
    from nebula.game.services import Services
    from nebula.game.ship import SpaceShip
    services = Services.silent('en')
    scene = FreeModeScene(services)
    player = scene.player
    assert player.sprite.texture == 'Player_10' and player.sprite.size == player.ship_size
    assert SpaceShip.enemy(12, scene, entrance=False).sprite.texture == 'SpaceShips_12'
    player.move_left()
    for _ in range(40):
        player.sprite.update_actions(1 / 60)
    assert player.sprite.texture == 'Player_20'
    player.stabilise_from_left()
    for _ in range(40):
        player.sprite.update_actions(1 / 60)
    assert player.sprite.texture == 'Player_10'


def test_shot_frames_follow_the_original_lists():
    from nebula.game import looks
    assert looks.ARRAY_POWER_1 == ['PlayerPower_%02d' % i for i in range(2, 8)]
    assert looks.ARRAY_POWER_3 == ['PlayerPower_%02d' % i for i in (3, 5, 7, 9, 11, 12, 13, 14, 15)]
    assert looks.ship_color(3) == looks.ORANGE
    assert looks.ship_color(13) == (1.0, 1.0, 1.0, 1.0)     # 56, 148, 240 clamp to white
    assert looks.ship_color(45) == looks.BLACK


def test_tint_multiplies_the_texture():
    n = Node(position=(160, 284), size=(40, 40))
    n.texture = 'Fireball_08'
    plain = draw(n)
    n.tint, n.color_blend = (1.0, 0.0, 0.0), 1.0
    red = draw(n)
    assert red.get_at((160, 284))[1] <= plain.get_at((160, 284))[1]
    assert red.get_at((160, 284))[1] == 0


def test_emitters_load_and_emit_without_touching_the_game_random_numbers():
    from nebula.engine.particles import Emitter, keyframe
    from nebula.game import rand
    rand.seed(9)
    before = rand.arc4random()
    rand.seed(9)
    Emitter.simulate = True
    em = Emitter('starField')
    for _ in range(60):
        em.update_actions(1 / 60)
    assert 20 <= len(em.particles) <= 40          # 30 a second
    Emitter.simulate = False
    assert rand.arc4random() == before
    assert keyframe({'times': [0.0, 1.0], 'values': [[0.0], [1.0]]}, 0.25) == [0.25]
    s = draw(em)
    assert s.get_size() == (320, 568)


def test_bars_follow_life_and_shield():
    from nebula.game.free_mode import FreeModeScene
    from nebula.game.services import Services
    from nebula.game.ship import SpaceShip
    services = Services.silent('en')
    scene = FreeModeScene(services)
    bars = scene.player_bars
    life = bars.nodes[1]
    full = life.size[0]
    scene.player.life -= 1
    for _ in range(30):
        services.scheduler.update(1 / 60)
        scene.step(1 / 60)
    assert abs(life.size[0] - full * scene.player.life / scene.player.max_life) < 1e-6
    enemy = SpaceShip.enemy(12, scene, entrance=False)
    assert enemy.life_bar is not None
    assert getattr(SpaceShip.enemy(37, scene, entrance=False), 'life_bar', None) is None


def test_menus_show_their_pictures_and_remove_them():
    from nebula.game.free_mode import FreeModeScene
    from nebula.game.services import Services
    services = Services.silent('en')
    scene = FreeModeScene(services)
    scene.swipe_up()
    pictures = [c.texture for n in scene.children for c in n.children if getattr(c, 'texture', None)]
    assert 'pause_en' in pictures
    scene.menu_activate()
    assert not any(n.name == 'Pause background' for n in scene.children)
    assert scene.display.score.text == '0'
    s = draw(*[])     # labels render without a display
    label_node = Node(position=(160, 300))
    label_node.text, label_node.font_size, label_node.font_color = '12', 20, (1.0, 1.0, 0.0)
    assert draw(label_node).get_size() == (320, 568)
