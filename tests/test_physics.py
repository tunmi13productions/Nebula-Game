import math

from nebula.engine.nodes import Node, Scene
from nebula.engine.physics import Body, Circle, PhysicsWorld, Polygon, attach, overlap, rectangle, wants_contact


class Recorder(Scene):
    def __init__(self):
        super().__init__()
        self.physics_world = PhysicsWorld()
        self.log = []

    def did_begin_contact(self, a, b):
        self.log.append(('begin', {a.node.name, b.node.name}))

    def did_end_contact(self, a, b):
        self.log.append(('end', {a.node.name, b.node.name}))


def body_node(name, shape, pos, category, contact):
    n = Node(name=name, position=pos)
    attach(n, Body(shape, category, contact))
    return n


def test_contact_needs_a_matching_mask_on_either_side():
    a, b = Body(Circle(1), category=1, contact=0), Body(Circle(1), category=0x200, contact=1)
    assert wants_contact(a, b) and wants_contact(b, a)
    assert not wants_contact(Body(Circle(1), 1, 0), Body(Circle(1), 2, 0))


def test_begin_and_end_fire_once_each():
    s = Recorder()
    player = body_node('player', rectangle(20, 20), (100, 100), 1, 24)
    wall = body_node('wall', rectangle(3, 71), (0, 100), 0x200, 1)
    s.add_child(player); s.add_child(wall)
    s.step(1 / 60)
    assert s.log == []
    player.position = (10, 100)
    s.step(1 / 60); s.step(1 / 60)
    assert s.log == [('begin', {'player', 'wall'})]
    player.position = (100, 100)
    s.step(1 / 60)
    assert s.log[-1] == ('end', {'player', 'wall'})


def test_shapes_follow_node_scale():
    small = body_node('a', rectangle(10, 10), (0, 0), 1, 1)
    other = body_node('b', Circle(1), (8, 0), 1, 1)
    s = Scene(); s.add_child(small); s.add_child(other)
    assert not overlap(small.physics, other.physics)
    small.scale = 1.5
    assert overlap(small.physics, other.physics)


def test_rotated_polygon():
    bar = body_node('bar', rectangle(40, 2), (0, 0), 1, 1)
    dot = body_node('dot', Circle(1), (0, 15), 1, 1)
    s = Scene(); s.add_child(bar); s.add_child(dot)
    assert not overlap(bar.physics, dot.physics)
    bar.rotation = math.pi / 2
    assert overlap(bar.physics, dot.physics)


def test_edge_loop_only_counts_its_outline():
    loop = body_node('boss', Polygon([(-50, -50), (50, -50), (50, 50), (-50, 50)], edge_only=True), (0, 0), 2, 4)
    shot = body_node('shot', Circle(5), (0, 0), 4, 2)
    s = Scene(); s.add_child(loop); s.add_child(shot)
    assert not overlap(loop.physics, shot.physics)
    shot.position = (0, -48)
    assert overlap(loop.physics, shot.physics)


def test_child_bodies_use_the_parent_transform():
    ship = Node(position=(100, 100))
    field = body_node('field', rectangle(10, 10), (-40, 0), 0x100, 8)
    ship.add_child(field)
    bullet = body_node('bullet', Circle(2), (60, 100), 8, 5)
    s = Scene(); s.add_child(ship); s.add_child(bullet)
    assert overlap(field.physics, bullet.physics)


def test_removing_a_node_ends_its_contacts_and_all_begins_are_reported():
    s = Recorder()
    player = body_node('player', Circle(10), (0, 0), 1, 0)
    a = body_node('shotA', Circle(2), (5, 0), 8, 1)
    b = body_node('shotB', Circle(2), (-5, 0), 8, 1)
    for n in (player, a, b):
        s.add_child(n)

    def begin(x, y):
        s.log.append(('begin', {x.node.name, y.node.name}))
        for n in (x.node, y.node):
            if n.name.startswith('shot'):
                n.remove_from_parent()
    s.did_begin_contact = begin
    s.step(1 / 60)
    assert {frozenset(e[1]) for e in s.log if e[0] == 'begin'} == {frozenset({'player', 'shotA'}), frozenset({'player', 'shotB'})}
    s.step(1 / 60)
    assert sum(1 for e in s.log if e[0] == 'end') == 2
