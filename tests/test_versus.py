"""Versus mode: two scenes talking through a stand-in relay, all silent and on one scheduler each."""
import pytest

from nebula.game.services import Services
from nebula.game.versus import VersusScene, enemy_stats
from nebula.input import KeyboardTilt

FRAME = 1 / 60


class FakeNet:
    """RelayClient's interface, wired to a partner."""

    def __init__(self, name):
        self.name, self.opponent, self.partner = name, None, None
        self.inbox, self.closed = [], False
        for h in ('welcome', 'waiting', 'code', 'matched', 'data', 'opponent_left', 'error'):
            setattr(self, 'on_' + h, None)

    def send(self, payload):
        if self.partner is None or self.partner.closed:
            return False
        self.partner.inbox.append(bytes(payload))
        return True

    def poll(self):
        while self.inbox:
            data = self.inbox.pop(0)
            if self.on_data:
                self.on_data(data)

    def leave(self):
        if self.partner is not None and self.partner.on_opponent_left:
            self.partner.partner = None
            self.partner.on_opponent_left()
        self.partner = None

    def close(self):
        self.closed = True


def pair(a_points=(0, 0), b_points=(0, 0)):
    sides = []
    nets = FakeNet('Nebula 482'), FakeNet('Starship 17')
    nets[0].partner, nets[1].partner = nets[1], nets[0]
    nets[0].opponent, nets[1].opponent = 'Starship 17', 'Nebula 482'
    for net, points in zip(nets, (a_points, b_points)):
        services = Services.silent('en')
        services.globals.life_points, services.globals.shield_points = points
        left = []
        scene = VersusScene(services, KeyboardTilt(0.3), net, lambda left=left: left.append(True))
        scene.did_move_to_view()
        sides.append((scene, services, left))
    sides[0][0].is_host = True
    for net in nets:
        net.on_matched('x')
    return sides


def run(sides, seconds):
    for _ in range(int(round(seconds / FRAME))):
        for scene, services, _ in sides:
            services.scheduler.update(FRAME)
            scene.step(FRAME)


def spoken(services):
    return [t for t, *_ in services.voice.spoken]


def test_opponent_ship_is_built_from_their_upgrades():
    assert enemy_stats(0, 0) == (5, 0) and enemy_stats(3, 2) == (20, 2) and enemy_stats(7, 9) == (30, 5)
    sides = pair(a_points=(3, 2))
    run(sides, 0.1)
    b = sides[1][0]
    assert (b.enemy.life, b.enemy.shield) == (20, 2)


def test_countdown_then_start_and_positions_follow():
    sides = pair()
    (a, sa, _), (b, sb, _) = sides
    assert a.lobby is None and not a.started
    run(sides, 4.5)
    assert spoken(sa)[-4:] == ['3', '2', '1', 'Start!'] and a.started and b.started
    a.player.position = (60.0, a.player.position[1])
    run(sides, 0.2)
    assert b.enemy.position[0] == pytest.approx(60.0)


def test_a_shot_reaches_the_other_side_and_damage_is_agreed():
    sides = pair()
    (a, sa, _), (b, sb, _) = sides
    run(sides, 4.5)
    a.can_shoot = True
    assert a.player_shoot() is not None
    run(sides, 0.05)
    assert any(n.name == 'shot' or getattr(n, 'ship', None) is b.enemy for n in b.children)
    a.enemy.inflict_damage(2)              # A's shot hit B's ship on A's screen
    run(sides, 0.2)
    assert b.player.life == 3


def end_round(sides):
    run(sides, 4.5)
    sides[0][0].enemy.inflict_damage(5)     # the host wins
    run(sides, 1.5)


def test_a_round_ends_and_waits_for_the_host():
    sides = pair()
    (a, sa, _), (b, sb, _) = sides
    end_round(sides)
    assert a.in_menu and b.in_menu
    assert spoken(sa)[-1] == 'Nebula 482 Winner., Back to menu button'
    assert spoken(sb)[-1] == 'Nebula 482 Winner. Waiting for the host to restart., Back to menu button'
    assert [label for label, _ in a.menu_items] == ['Back to menu button', 'Restart, button']
    assert [label for label, _ in b.menu_items] == ['Back to menu button']
    run(sides, 10.0)
    assert a.in_menu and b.in_menu           # no restart by itself


def test_the_host_restarts_both_sides():
    sides = pair()
    (a, sa, _), (b, sb, _) = sides
    end_round(sides)
    a.menu_next()
    a.menu_activate()                        # Restart
    run(sides, 0.1)
    assert not a.in_menu and not b.in_menu
    assert a.player.life == a.player.max_life and b.player.life == b.player.max_life
    run(sides, 4.5)
    assert a.started and b.started and spoken(sb)[-1] == 'Start!'


def test_the_guest_can_go_back_to_the_menu_from_the_end_screen():
    sides = pair()
    (a, sa, aleft), (b, sb, bleft) = sides
    end_round(sides)
    b.menu_activate()                        # Back to menu
    run(sides, 0.1)
    assert bleft == [True] and aleft == [True]


def test_a_draw_tells_the_guest_to_wait_in_portuguese():
    sides = pair()
    (a, sa, _), (b, sb, _) = sides
    for scene, services, _ in sides:
        services.strings.__init__('pt')
    run(sides, 4.5)
    a.player.inflict_damage(5)
    a.enemy.inflict_damage(5)
    run(sides, 1.5)
    assert spoken(sa)[-1] == 'Empate, Ir para menu, Botão'
    assert spoken(sb)[-1] == 'Empate. Esperando o anfitrião recomeçar., Ir para menu, Botão'


def test_the_loser_can_keep_shooting_after_a_restart():
    sides = pair()
    (a, sa, _), (b, sb, _) = sides
    run(sides, 4.5)
    a.enemy.inflict_damage(5)               # B loses: its ship is destroyed
    run(sides, 1.5)
    a.host_restart()
    run(sides, 4.5)
    assert b.started
    shots = 0
    for _ in range(3):
        if b.player_shoot() is not None:
            shots += 1
        run(sides, 1.0)
    assert shots == 3


def test_the_opponent_leaving_returns_to_the_menu():
    sides = pair()
    (a, sa, aleft), (b, sb, bleft) = sides
    run(sides, 1.0)
    b.back_to_menu()
    run(sides, 0.1)
    assert bleft == [True] and aleft == [True]


def test_no_answer_within_five_seconds_returns_to_the_menu():
    services = Services.silent('en')
    net = FakeNet('Alone')
    net.partner = FakeNet('Silent')         # accepts messages, never answers
    left = []
    scene = VersusScene(services, KeyboardTilt(0.3), net, lambda: left.append(True))
    net.on_matched('Silent')
    for _ in range(int(5.2 / FRAME)):
        services.scheduler.update(FRAME)
        scene.step(FRAME)
    assert left == [True]
