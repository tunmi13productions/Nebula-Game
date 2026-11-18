"""Contact detection in the style of SKPhysicsWorld.

Nothing is simulated physically: every node in the original is moved by actions or by code, and gravity is
zero. Only contacts matter. Two bodies are in contact when their shapes overlap and either body's category
bit mask intersects the other's contact test bit mask. The scene gets did_begin_contact(a, b) when a
contact starts and did_end_contact(a, b) when it ends, a and b being Body objects.

Shapes are in the node's local coordinates (points, centred on the node's position) and follow the node's
position, scale and rotation, including its ancestors' transforms.
"""
import math


class Circle:
    def __init__(self, radius, center=(0.0, 0.0)):
        self.radius, self.center = radius, center


class Polygon:
    """A convex polygon. Edge loops (bodyWithEdgeLoopFromPath) set edge_only, which means only the outline counts."""

    def __init__(self, points, edge_only=False):
        self.points, self.edge_only = list(points), edge_only


def rectangle(width, height, center=(0.0, 0.0)):
    cx, cy = center
    w, h = width / 2.0, height / 2.0
    return Polygon([(cx - w, cy - h), (cx + w, cy - h), (cx + w, cy + h), (cx - w, cy + h)])


class Body:
    def __init__(self, shape, category=0, contact=0, collision=0xFFFFFFFF):
        self.shape = shape
        self.category, self.contact, self.collision = category, contact, collision
        self.node = None


def attach(node, body):
    """node.physicsBody = body (None removes it)."""
    if node.physics is not None:
        node.physics.node = None
    node.physics = body
    if body is not None:
        body.node = node


def _world_transform(node):
    """Returns (x, y, scale, rotation) of node in scene space."""
    x, y = node.position
    s, r = node.scale, node.rotation
    p = node.parent
    while p is not None and p.parent is not None:
        c, si = math.cos(p.rotation), math.sin(p.rotation)
        x, y = p.position[0] + p.scale * (x * c - y * si), p.position[1] + p.scale * (x * si + y * c)
        s *= p.scale
        r += p.rotation
        p = p.parent
    return x, y, s, r


def _world_shape(body):
    x, y, s, r = _world_transform(body.node)
    c, si = math.cos(r), math.sin(r)

    def tf(px, py):
        return x + s * (px * c - py * si), y + s * (px * si + py * c)
    sh = body.shape
    if isinstance(sh, Circle):
        return ('circle', tf(*sh.center), sh.radius * s)
    return ('poly', [tf(px, py) for px, py in sh.points], sh.edge_only)


def _project(points, axis):
    ds = [p[0] * axis[0] + p[1] * axis[1] for p in points]
    return min(ds), max(ds)


def _axes(points):
    out = []
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        length = math.hypot(ex, ey)
        if length > 0:
            out.append((-ey / length, ex / length))
    return out


def _poly_poly(a, b):
    for axis in _axes(a) + _axes(b):
        amin, amax = _project(a, axis)
        bmin, bmax = _project(b, axis)
        if amax < bmin or bmax < amin:
            return False
    return True


def _point_in_poly(p, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > p[1]) != (y2 > p[1]) and p[0] < (x2 - x1) * (p[1] - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _segment_distance(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / l2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def _circle_poly(center, radius, poly, edge_only):
    n = len(poly)
    near_edge = any(_segment_distance(center, poly[i], poly[(i + 1) % n]) <= radius for i in range(n))
    if edge_only:
        return near_edge
    return near_edge or _point_in_poly(center, poly)


def _segments_cross(p1, p2, q1, q2):
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2 = orient(q1, q2, p1), orient(q1, q2, p2)
    d3, d4 = orient(p1, p2, q1), orient(p1, p2, q2)
    return (d1 * d2 <= 0) and (d3 * d4 <= 0)


def _edges_touch(a, b):
    na, nb = len(a), len(b)
    return any(_segments_cross(a[i], a[(i + 1) % na], b[j], b[(j + 1) % nb]) for i in range(na) for j in range(nb))


def overlap(body_a, body_b):
    a, b = _world_shape(body_a), _world_shape(body_b)
    if a[0] == 'circle' and b[0] == 'circle':
        return math.hypot(a[1][0] - b[1][0], a[1][1] - b[1][1]) <= a[2] + b[2]
    if a[0] == 'circle':
        return _circle_poly(a[1], a[2], b[1], b[2])
    if b[0] == 'circle':
        return _circle_poly(b[1], b[2], a[1], a[2])
    if a[2] or b[2]:
        return _edges_touch(a[1], b[1])
    return _poly_poly(a[1], b[1])


def wants_contact(a, b):
    return bool((a.category & b.contact) or (b.category & a.contact))


class PhysicsWorld:
    """Tracks which body pairs touch. New contacts found in a frame are all reported after detection,
    as SpriteKit does, so a handler that removes a node doesn't hide other contacts from that frame."""

    def __init__(self):
        self._pairs = {}   # (id, id) -> (body, body) currently touching

    def simulate(self, scene):
        bodies = [n.physics for n in scene.walk() if n is not scene and n.physics is not None and n.physics.node is n]
        now = {}
        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                a, b = bodies[i], bodies[j]
                if wants_contact(a, b) and overlap(a, b):
                    now[(id(a), id(b)) if id(a) < id(b) else (id(b), id(a))] = (a, b)
        ended = [pair for key, pair in self._pairs.items() if key not in now]
        begun = [pair for key, pair in now.items() if key not in self._pairs]
        self._pairs = now
        for a, b in begun:
            scene.did_begin_contact(a, b)
        for a, b in ended:
            scene.did_end_contact(a, b)
