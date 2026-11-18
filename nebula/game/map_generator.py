"""MapGenerator: the scrolling space backgrounds of free mode and every chapter stage.

Visual, apart from one thing: like the original, it draws from the game's arc4random (and arc4random_uniform)
whenever it places a planet, nebula, map detail, fuel tank, rock emitter or background ship emitter, so those
draws are part of the game's random sequence. In the original some of this ran on background threads, so
the exact interleaving with gameplay draws wasn't fixed there either.

Building blocks, traced from the original (tools/re/objc_trace.py):
- rotateBackground: two 568 by 568 point copies of a texture stacked vertically (z 2), and with use2Layers a
  second pair turned half a turn (z 3). A 0.025 second timer moves the first pair down by
  H / (rotationTime / 0.025) points and the second by twice that; a copy that reaches -H/2 jumps above the
  other.
- The star emitter (starField.sks) at the top edge, z 5.
- Map details: every interval / 2 seconds, and once at once, a MapDetails_ texture (one of 3), a square of
  H + arc4random_uniform(H / 3) points at x = arc4random_uniform(W), tinted with the stage's colour, drifts
  from just above the screen to just below it over `interval` seconds.
- Items (makeItem...crossTheScreen...): placed with their bottom at the top edge and moved until their top
  reaches the bottom edge over the duration, then removed. A colour tints them fully.
- makeAPlanet: planet0 to 5 (arc4random % 6), 2H square, x = arc4random_uniform(2H + W) - H, z 4, 70 seconds
  unless the timer carries another duration.
- makeANebula: two layers (nebulaL1_, nebulaL2_), each one of 2 textures (arc4random % 2), 2W by 2H, x =
  arc4random_uniform(W), tinted with three arc4random_uniform(255) / 255 components, z 7, 40 seconds unless
  the timer carries another duration.
- makeAFuelTank: 1 + arc4random % 5 stacked Chapter1_BackgroundFuel pieces, each 5 + (arc4random % 23) * 3.2
  points square, crossing in 20 + arc4random % 11 seconds at x = arc4random_uniform(W), turned
  (arc4random % 10) / pi radians, z 3.
- Saturn's distant rocks and the background ships: every second the previous emitter stops and a new one
  starts with a random picture.
"""
import math

from ..engine import actions as A
from ..engine.nodes import Node
from ..engine.particles import Emitter
from . import rand

ROTATION_TICK = 0.025
BLUE, GREEN, CLEAR = (0.0, 0.0, 1.0, 1.0), (0.0, 1.0, 0.0, 1.0), (0.0, 0.0, 0.0, 0.0)
YELLOW, WHITE, PURPLE = (1.0, 1.0, 0.0, 1.0), (1.0, 1.0, 1.0, 1.0), (0.5, 0.0, 0.5, 1.0)
ORANGE_DETAIL = (1.0, 180 / 255, 0.0, 1.0)
BLACK = (0.0, 0.0, 0.0, 1.0)


class MapGenerator:
    def __init__(self, scene, services):
        self.scene, self.services = scene, services
        self.W, self.H = scene.size
        self.timers = []
        self.layers = []
        self.rotation_timer = None
        self.running_emitter = {}

    # lifetime

    def every(self, interval, fn, fire_now=False):
        """An NSTimer that repeats; fire_now is the original's [timer fire] right after scheduling."""
        timer = self.services.scheduler.every(interval, lambda t: fn())
        self.timers.append(timer)
        if fire_now:
            fn()
        return timer

    def stop(self):
        """stopTheMapGenerator."""
        for t in self.timers:
            t.invalidate()
        self.timers = []

    def add(self, node):
        self.scene.add_child(node)
        return node

    # building blocks

    def rotate_background(self, texture, rotation_time, two_layers):
        W, H = self.W, self.H
        pairs = [(2.0, 0.0)] + ([(3.0, math.pi)] if two_layers else [])
        self.layers = []
        for z, turn in pairs:
            pair = []
            for y in (H * 0.5, H * 1.5):
                n = Node(name='background', size=(H, H), position=(W * 0.5, y))
                n.texture, n.z, n.rotation = texture, z, turn
                pair.append(self.add(n))
            self.layers.append(pair)
        step = H / (rotation_time / ROTATION_TICK)
        self.rotation_timer = self.every(ROTATION_TICK, lambda: self._rotate(step))

    def _rotate(self, step):
        H = self.H
        for i, (a, b) in enumerate(self.layers):
            for part, other in ((a, b), (b, a)):
                if part.position[1] <= -H * 0.5:
                    part.position = (part.position[0], other.position[1] + other.size[1])
            d = step * (i + 1)
            for part in (a, b):
                part.position = (part.position[0], part.position[1] - d)

    def star_emitter(self):
        em = Emitter('starField')
        em.set(position_range=[self.W, 0.0], birth_rate=32.0, lifetime=5.0, speed=self.H, speed_range=852.0,
               acceleration=[0.0, 0.0], rotation=0.0, alpha=1.0, alpha_range=0.0, alpha_speed=0.0,
               scale=0.032, scale_range=0.0427, scale_speed=0.0)
        em.position, em.z = (self.W * 0.5, self.H), 5
        return self.add(em)

    def ftl_emitter(self):
        em = Emitter('ftlparticle')
        em.set(position_range=[self.W, 0.0], birth_rate=32.0, lifetime=5.0, speed=1000.0, speed_range=1500.0,
               acceleration=[0.0, 0.0], rotation=0.0, alpha=1.0, alpha_range=0.0, alpha_speed=0.0,
               scale=0.5, scale_range=0.75, scale_speed=0.0)
        em.position, em.z = (self.W * 0.5, self.H), 5
        return self.add(em)

    def random_details(self, interval, color, z=1):
        self.every(interval * 0.5, lambda: self.map_detail(interval, color, z), fire_now=True)

    def map_detail(self, duration, color, z):
        index = rand.arc4random_uniform(3)
        size = rand.arc4random_uniform(int(self.H / 3.0)) + self.H
        x = float(rand.arc4random_uniform(int(self.W)))
        self.item_texture('MapDetails_%d' % index, duration, z, x, (size, size), color)

    def item_texture(self, texture, duration, z, x, size, color=None):
        node = Node(name='mapItem', size=size)
        node.texture = texture
        return self.item_node(node, duration, z, x, 0.0, color)

    def item_node(self, node, duration, z, x, rotation, color=None):
        if color is not None:
            node.tint, node.color_blend = color, 1.0
        h = node.size[1]
        node.position = (x, self.H + h * 0.5)
        node.z, node.rotation = z, rotation
        self.add(node)
        node.run(A.sequence([A.move_to_y(-h * 0.5, duration), A.remove_from_parent()]))
        return node

    def make_a_planet(self, duration=70.0):
        r = rand.arc4random()
        x = rand.arc4random_uniform(int(self.H * 2 + self.W)) - self.H
        self.item_texture('planet%d' % (r % 6), duration, 4, float(x), (self.H * 2, self.H * 2))

    def make_a_nebula(self, duration=40.0):
        for layer in ('nebulaL1_', 'nebulaL2_'):
            r = rand.arc4random()
            x = float(rand.arc4random_uniform(int(self.W)))
            color = tuple(rand.arc4random_uniform(255) / 255.0 for _ in range(3)) + (1.0,)
            self.item_texture('%s%d' % (layer, r % 2), duration, 7, x, (self.W * 2, self.H * 2), color)

    def make_a_fuel_tank(self):
        count = rand.arc4random() % 5 + 1
        piece = 5.0 + (rand.arc4random() % 23) * 3.2
        tank = Node(name='fuelTank', size=(piece, piece * count))
        for i in range(count):
            p = Node(name='fuel', size=(piece, piece), position=(0.0, (i - (count - 1) / 2.0) * piece))
            p.texture = 'Chapter1_BackgroundFuel'
            tank.add_child(p)
        duration = 20 + rand.arc4random() % 11
        x = float(rand.arc4random_uniform(int(self.W)))
        rotation = (rand.arc4random() % 10) / math.pi
        self.item_node(tank, float(duration), 3, x, rotation)

    def _replace_emitter(self, key, emitter):
        old = self.running_emitter.get(key)
        if old is not None:
            old.set(birth_rate=0.0)
            old.run(A.sequence([A.wait(old.params['lifetime']), A.remove_from_parent()]))
        self.running_emitter[key] = emitter
        self.add(emitter)

    def saturn_debris(self):
        """createSaturnDistantDebreeEmitter: one of asteroid0 to 2 particles, every second."""
        r = rand.arc4random()
        em = Emitter('asteroid%dparticle' % (r % 3))
        em.set(position_range=[self.W, 0.0], birth_rate=16.0, lifetime=30.0, speed=self.H / 4.0,
               speed_range=self.H / 3.0, acceleration=[0.0, 0.0], rotation=math.pi, alpha=0.8, alpha_range=0.0,
               alpha_speed=0.0, scale=0.032, scale_range=0.0427, scale_speed=0.0, color=list(WHITE))
        em.position, em.z = (self.W * 0.5, self.H), 4
        self._replace_emitter('rocks', em)

    def background_ships(self, down):
        """createSpaceshipsGoingUp/DownOnBackground: a ship (37 to 39) trail rising from below, and a less
        blurred one either rising too or (going down) falling from above."""
        ship = 37 + rand.arc4random() % 3
        a = Emitter('Ship%dFlyParticle' % ship)
        a.set(position_range=[self.W, 0.0], birth_rate=2.0, lifetime=30.0, speed=20.0, speed_range=20.0,
              acceleration=[0.0, 10.0], rotation=math.pi / 2, alpha=1.0, alpha_range=0.0, alpha_speed=0.0)
        if not down:
            a.set(emission_angle=math.pi / 2, emission_angle_range=0.0)
        a.position, a.z, a.xscale, a.yscale = (self.W * 0.5, -self.H * 0.2), 4, 1.0, 2.0
        self._replace_emitter('ships_a', a)
        ship = 37 + rand.arc4random() % 3
        b = Emitter('Ship%dFlyParticleLessBlur' % ship)
        if down:
            b.set(position_range=[self.W, 0.0], birth_rate=2.0, lifetime=30.0, speed=50.0, speed_range=20.0,
                  acceleration=[0.0, 0.0], rotation=math.pi / 2, alpha=1.0, alpha_range=0.0, alpha_speed=0.0,
                  emission_angle=3 * math.pi / 2, emission_angle_range=0.0)
            b.position, b.z = (self.W * 0.5, self.H * 1.2), 4.1
        else:
            b.set(position_range=[self.W, 0.0], birth_rate=1.0, lifetime=30.0, speed=30.0, speed_range=20.0,
                  acceleration=[0.0, 10.0], rotation=math.pi / 2, alpha=1.0, alpha_range=0.0, alpha_speed=0.0,
                  emission_angle=math.pi / 2, emission_angle_range=0.0)
            b.position, b.z = (self.W * 0.5, -self.H * 0.2), 4
        b.xscale, b.yscale = 0.8, 2.3
        self._replace_emitter('ships_b', b)

    def big_item(self, texture, size, position, z=4):
        n = Node(name='mapItem', size=size, position=position)
        n.texture, n.z = texture, z
        return self.add(n)

    # maps

    def free_mode(self):
        """initFreemodeMapInScene: (also the campaign selector's background)."""
        self.scene.background = (0.0, 0.0, 0.0)
        self.rotate_background('starfieldBG', 20, True)
        self.random_details(60, BLUE)
        self.every(100, self.make_a_planet, fire_now=True)
        self.star_emitter()
        self.every(60, self.make_a_nebula)

    def chapter(self, chapter, stage):
        """initChapterNStage:onScene:"""
        W, H = self.W, self.H
        self.scene.background = (0.0, 0.0, 0.0)
        key = (chapter, stage)
        if key == (3, 2):
            self.rotate_background('ftlBG', 2, False)
            self.ftl_emitter()
            return
        if key == (5, 4):
            self.rotate_background('lavaBG', 10, False)
            self.random_details(10, YELLOW, 7)
            return
        if chapter == 9:
            texture, time = {1: ('iceGrounds', 5), 2: ('iceNMetalGrounds', 5), 3: ('metalGrounds', 5),
                             4: ('canyon', 1)}[stage]
            self.rotate_background(texture, time, False)
            if stage == 4:
                self.random_details(30, PURPLE)
                veil = Node(name='veil', size=(W, H), position=(W * 0.5, H * 0.5))
                veil.color, veil.z, veil.alpha = BLACK, 7, 0.0
                self.add(veil).run(A.fade_alpha_to(0.95, 100))
            else:
                self.random_details({1: 15, 2: 10, 3: 5}[stage], WHITE, 7)
            return
        self.rotate_background('starfieldBG', 20, True)
        self._stage_layer(chapter, stage)
        stars = not (chapter == 6 or key == (4, 2) or key in ((8, 2), (8, 3), (8, 4)))
        if stars and chapter not in (7, 8):
            self.star_emitter()
        color = {1: BLUE, 2: GREEN, 3: BLUE if stage == 1 else CLEAR, 4: BLUE, 5: CLEAR, 6: CLEAR,
                 7: ORANGE_DETAIL, 8: ORANGE_DETAIL}[chapter]
        if key != (4, 2):
            self.random_details(60, color)
        if stars and chapter in (7, 8):
            self.star_emitter()

    def _stage_layer(self, chapter, stage):
        """createChapterN_SceneMBG2."""
        W, H = self.W, self.H
        key = (chapter, stage)
        if chapter == 1 and stage >= 2:
            self.every(15 if stage == 2 else 10, self.make_a_fuel_tank)
        elif key == (2, 2):
            self.every(30, lambda: self.make_a_nebula(10.0))
        elif key == (2, 3):
            self.every(40, lambda: self.make_a_nebula(25.0), fire_now=True)
        elif key == (2, 4):
            self.big_item('planet1', (H * 1.5, H * 1.5), (W / 3, H * 1.5)).run(A.move_to_y(-H * 0.75, 120))
        elif key == (3, 1):
            planet = self.big_item('planet1', (H * 1.2, H * 1.2), (W / 3, H * 0.5))
            planet.run(A.sequence([A.wait(20), A.move_to_y(-H * 0.6, 50)]))
        elif key == (3, 3):
            self.every(30, lambda: self.make_a_nebula(25.0), fire_now=True)
        elif key == (3, 4):
            self.big_item('plutao', (H * 1.5, H * 1.5), (W * 2 / 3, H * 1.75)).run(A.move_to_y(-H * 0.75, 120))
        elif key == (4, 1):
            self.big_item('netuno', (H * 1.2, H * 1.2), (W, H * 0.8)).run(A.move_to_y(-H * 0.6, 120))
        elif key == (4, 2):
            self.every(1, self.saturn_debris)
            self.big_item('saturno', (H * 1.5, H * 1.5), (W * 0.5, H)).run(A.move_to_y(-H * 0.75, 120))
        elif key == (4, 3):
            self.big_item('jupiter', (H, H), (36.0, H * 1.5)).run(A.move_to_y(-H * 0.5, 120))
        elif key == (4, 4):
            self.big_item('marte2', (H * 1.5, H * 1.5), (W * 2 / 3, H * 1.75)).run(A.move_to_y(-H * 0.75, 60))
        elif key == (5, 1):
            self.big_item('venus', (H * 1.2, H * 1.2), (W, H)).run(A.move_to_y(-H * 0.6, 120))
            self.big_item('sun', (128.0, 64.0), (W * 0.5, H * 0.5), z=1)
        elif key == (5, 2):
            self.big_item('mercurio', (H * 2, H * 1.5), (W * 0.5, H)).run(A.move_to_y(-H * 0.75, 120))
            self.big_item('sun', (W * 2 / 3, W / 3), (W * 0.5, H * 0.5), z=1)
        elif key == (5, 3):
            self.big_item('sun', (W, W * 0.5), (W * 0.5, H * 0.5), z=1).run(A.resize_to(W * 2, W, 60))
        elif chapter == 6:
            self.every(1, lambda: self.background_ships(down=stage in (2, 3)))
            if stage == 3:
                self.every(60, self.make_a_nebula)
        elif chapter == 7 or key == (8, 1):
            self.every(60, self.make_a_planet)
            self.every(40, self.make_a_nebula)
