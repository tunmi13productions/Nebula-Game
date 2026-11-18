"""Boss: the ten bosses (see docs/NOTES.md, bosses, and data/bosses.json built from the original).

A boss starts off screen, flies its entrance, then loops its movement and fires on its attack interval.
Each boss has its own attack block. They're encoded here as cycles of firing points, relative to the boss,
traced from the original at the 320 by 568 scene size (tools/re/trace_boss_attacks.py). Boss 9's middle
step is a coin flip between a laser and a centre bullet: getRandomNumberBetween(0, 100), laser when even. Bosses have no engine sound: they're heard through
their bullets, lasers and explosion.
"""
from ..data import BOSSES
from ..engine import actions as A
from ..engine.nodes import Node
from ..engine.physics import Body, Circle, Polygon, attach, rectangle
from . import looks
from .rand import arc4random, between
from .ship import CAT_ENEMY, CAT_ENEMY_SHOT, CAT_LASER, CAT_OBSTACLE, CAT_PLAYER, CAT_PLAYER_SHOT, Shot

BOSS_CODE = 100            # what Boss getShipCode reports to destroyEnemy:
SHOT_FLIGHT = 1.5
LASER_CHARGE, LASER_WARM, LASER_RETREAT = 1.0, 1.5, 3.0
EXPLOSION_GAPS = (0.3, 0.2)
EXPLOSION_TIME = 1.0       # the explosion animation, visual only, before the boss leaves the scene

# Each step is a list of ('shot' | 'laser' | 'coin', dx, dy). 'coin': an even getRandomNumberBetween(0, 100)
# fires a laser, an odd one a bullet, at the same point.
ATTACKS = {
    1: [[('laser', 0.0, -139.0), ('shot', -72.15, 0.0)],
        [('laser', 141.47, -208.5), ('shot', 72.15, 0.0)],
        [('laser', -141.47, -208.5), ('shot', 72.15, 0.0)]],
    2: [[('shot', -102.6, 0.0)], [('shot', -64.125, 0.0)], [('shot', 0.0, 0.0)], [('shot', 64.125, 0.0)],
        [('shot', 102.6, 0.0)]],
    3: [[('shot', -53.09, -106.25)], [('shot', 0.0, -212.5)], [('shot', 58.4, -106.25)]],
    4: [[('shot', -102.89, -76.0)], [('shot', 0.0, -152.0)], [('shot', 102.89, -76.0)], [('shot', 0.0, -152.0)]],
    5: [[('shot', 292.0, -95.0)], [('shot', -292.0, -95.0)], [], [('laser', 0.0, -190.0)]],
    6: [[('shot', 0.0, -211.5)], [('laser', 0.0, -141.0)]],
    7: [[('shot', -151.74, -707.69)], [('shot', -175.84, -103.25)], [('laser', 8.26, -139.69)], [('shot', 194.07, 0.0)]],
    8: [[('shot', 182.22, -160.71)], [('laser', 0.0, -150.0)], [('shot', -182.22, -160.71)], [('shot', -182.22, -160.71)]],
    9: [[('shot', -132.29, -146.75), ('shot', -128.29, -146.75)], [('coin', 0.0, -195.67)],
        [('shot', 128.29, -146.75), ('shot', 132.29, -146.75)]],
    10: [[('shot', -71.23, -104.25)], [('shot', 0.0, -208.5)], [('shot', 71.23, -104.25)], [('shot', 0.0, -208.5)]],
}


class Boss(Node):
    def __init__(self, boss_code, scene):
        super().__init__(name='Boss')
        data = BOSSES[boss_code]
        self.boss_code = boss_code
        self.code = BOSS_CODE
        self.game = scene
        self.life = self.max_life = data['life']
        self.shield = 0
        self.shoot_damage = data['damage']
        self.score = data['score']
        self.size = tuple(data['size'])
        self.position = tuple(data['start'])
        self.z = 5
        self.receive_damage = True
        self.laser_active = False
        self.step = 0               # atualShootPoint
        self.data = data
        # its picture: Boss_NN as a child sprite at the texture's own size (visual only)
        self.sprite = Node(name='bossSprite', size=self.size)
        self.sprite.texture = 'Boss_%02d' % boss_code
        self.add_child(self.sprite)
        x, y, duration = data['entrance']
        self.run(A.move_to(x, y, duration), completion=self._arrived)

    @property
    def services(self):
        return self.game.services

    # after the entrance: body, movement loop, attack loop

    def _arrived(self):
        attach(self, Body(Polygon(self.data['outline'], edge_only=True), category=CAT_ENEMY,
                          contact=CAT_PLAYER | CAT_PLAYER_SHOT | CAT_OBSTACLE, collision=CAT_OBSTACLE))
        moves = []
        for kind, a, b, duration in self.data['moves']:
            moves.append(A.move_by(a, b, duration) if kind == 'by' else A.move_to(a, b, duration))
        moves.append(A.run_block(self._check_active))
        self.run(A.repeat_forever(A.sequence(moves)), key='BossMove')
        self.run(A.repeat_forever(A.sequence([A.wait(self.data['attack_interval']), A.run_block(self.attack_tick)])),
                 key='BossAttack')

    def _check_active(self):
        if not self.game.is_active:
            self.autodestruction()

    def attack_tick(self):
        if not self.game.is_active:
            self.autodestruction()
        pattern = ATTACKS[self.boss_code]
        self.step = (self.step + 1) % len(pattern)
        for kind, dx, dy in pattern[self.step - 1]:
            if kind == 'coin':
                kind = 'laser' if between(0, 100) & 1 == 0 else 'shot'
            if kind == 'laser':
                self.laser_shoot_on_position(dx, dy)
            else:
                self.shoot_on_position(self.position[0] + dx, self.position[1] + dy)

    # bullets (shootingOnPosition:)

    def shoot_on_position(self, x, y):
        w = self.game.size[0]
        bullet = Shot(self, (w / 12.0, w / 12.0))
        bullet.texture = looks.FIREBALL[2]   # a colour is set, but with no blend factor it doesn't show
        bullet.blend_mode, bullet.z = 'add', -1.0
        bullet.run(A.repeat_forever(A.animate_with_textures(looks.FIREBALL, looks.BOSS_BULLET_FRAME)))
        attach(bullet, Body(Circle(5.0), category=CAT_ENEMY_SHOT, contact=CAT_PLAYER | CAT_PLAYER_SHOT, collision=CAT_ENEMY_SHOT))
        bullet.position = (x, y)
        bullet.run(A.sequence([A.move_to_y(-20.0, SHOT_FLIGHT), A.remove_from_parent()]))
        self.game.add_child(bullet)
        self._play_linked('Enemy_Shot_1', 'caf', bullet)
        return bullet

    def _play_linked(self, name, ext, node):
        aureal = self.services.aureal
        key = aureal.next_key()
        aureal.add_sound(name, ext, key)
        aureal.sound_id += 1
        aureal.link(key, node)
        aureal.play_once(key, node.position)
        return key

    # lasers (laserShootOnPosition:)

    def laser_shoot_on_position(self, dx, dy):
        """Same cycle as a laser ship, but the beam is a child of the boss: it sits at (dx, dy - h/2) from
        the boss centre, W/50 wide and H tall, moves with the boss, and retreats to y = h over 3 seconds."""
        if self.laser_active:
            return
        hold = float(arc4random() % 5 + 3)
        self.laser_active = True
        beam = Shot(self, (0.0, 0.0))
        beam.anchor = (0.5, 1.0)
        self.add_child(beam)
        keys = {}
        w, h = self.game.size
        bh = self.size[1]

        def charge():
            keys['sound'] = self._play_linked('Laser_Charge', 'caf', self)

        def fire():
            keys['sound'] = self._play_linked('Laser_Firing', 'mp3', self)

        def beam_on():
            beam.position = (dx, dy - bh / 2.0)
            beam.size = (w / 50.0, h)
            attach(beam, Body(rectangle(*beam.size), category=CAT_LASER, contact=CAT_PLAYER, collision=CAT_LASER))

        def retreat():
            self.services.aureal.stop(keys.get('sound'), 1)

            def done():
                beam.remove_from_parent()
                self.laser_active = False
            beam.run(A.move_to_y(bh, LASER_RETREAT), completion=done)
        beam.run(A.sequence([A.run_block(charge), A.wait(LASER_CHARGE), A.run_block(fire), A.wait(LASER_WARM),
                             A.run_block(beam_on), A.wait(hold), A.run_block(retreat)]))

    # damage and death

    def inflict_damage(self, damage):
        """Boss inflictDamage: a shield point absorbs a hit (bosses have none), otherwise life drops. No speech."""
        if self.shield >= 1:
            self.shield -= 1
            return False
        self.life -= damage
        if self.life < 1:
            self.destroy()
            return True
        return False

    def destroy(self):
        """destroyBoss: three explosions 0.3 and 0.2 seconds apart, then the boss leaves after its animation."""
        fx = self.services.effects
        self.remove_all_actions()
        self.remove_all_children()
        attach(self, None)
        # its picture: three times its size, the Explosion02 frames at 0.032 seconds each
        boom = Node(name='explosion', size=(self.size[0] * 3, self.size[1] * 3))
        boom.texture = looks.EXPLOSION_1[0]
        boom.run(A.animate_with_textures(looks.EXPLOSION_1, looks.EXPLOSION_FRAME))
        self.add_child(boom)
        self.run(A.sequence([A.play_sound(lambda: fx.play('explosion_1.caf')), A.wait(EXPLOSION_GAPS[0]),
                             A.play_sound(lambda: fx.play('Explosion_.mp3')), A.wait(EXPLOSION_GAPS[1]),
                             A.play_sound(lambda: fx.play('explosion.mp3')),
                             A.wait(EXPLOSION_TIME), A.remove_from_parent()]))

    def autodestruction(self):
        self.remove_all_actions()
        self.remove_all_children()
        self.remove_from_parent()
