"""The multiplayer relay (server/relay.py) and the game's client (nebula/net/relay_client.py), with a real
server on this machine and two players talking through it. Nothing leaves the computer."""
import asyncio
import threading
import time

import pytest

from nebula.net.relay_client import RelayClient
from server import relay


@pytest.fixture
def server():
    """A relay on a free local port, for the length of a test."""
    port = []
    loop = asyncio.new_event_loop()

    def go():
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(relay.run('127.0.0.1', 0, ready=port.append))
        except (asyncio.CancelledError, RuntimeError):
            pass
    thread = threading.Thread(target=go, daemon=True)
    thread.start()
    for _ in range(200):
        if port:
            break
        time.sleep(0.01)
    yield '127.0.0.1:%d' % port[0]
    for task in asyncio.all_tasks(loop):
        loop.call_soon_threadsafe(task.cancel)
    thread.join(2.0)


class Player:
    def __init__(self, address, name):
        self.client = RelayClient(address)
        self.events = []
        for handler in ('welcome', 'waiting', 'code', 'matched', 'data', 'opponent_left', 'error'):
            setattr(self.client, 'on_' + handler, (lambda h: lambda *a: self.events.append((h,) + a))(handler))
        self.client.connect(name)

    def wait_for(self, kind, timeout=3.0):
        end = time.time() + timeout
        while time.time() < end:
            self.client.poll()
            for e in self.events:
                if e[0] == kind:
                    self.events.remove(e)
                    return e
            time.sleep(0.01)
        raise AssertionError('no %s, got %r' % (kind, self.events))


def test_quick_match_pairs_two_waiting_players_and_relays_messages(server):
    a, b = Player(server, 'Nebula 482'), Player(server, 'Starship 17')
    assert a.wait_for('welcome') == ('welcome', 'Nebula 482')
    b.wait_for('welcome')
    a.client.quick()
    a.wait_for('waiting')
    b.client.quick()
    assert a.wait_for('matched') == ('matched', 'Starship 17')
    assert b.wait_for('matched') == ('matched', 'Nebula 482')
    message = bytes([0, 0, 0, 0, 0, 0, 0x20, 0x43])
    assert a.client.send(message)
    assert b.wait_for('data') == ('data', message)


def test_an_invite_code_brings_a_friend_in(server):
    a, b = Player(server, 'Planet 905'), Player(server, 'Thunder 33')
    a.wait_for('welcome'), b.wait_for('welcome')
    a.client.host()
    code = a.wait_for('code')[1]
    assert len(code) == 4 and code.isdigit()
    b.client.join('0000' if code != '0000' else '0001')
    assert b.wait_for('error') == ('error', 'bad_code')
    b.client.join(code)
    assert a.wait_for('matched')[1] == 'Thunder 33'


def test_the_opponent_leaving_is_reported(server):
    a, b = Player(server, 'A'), Player(server, 'B')
    a.wait_for('welcome'), b.wait_for('welcome')
    a.client.quick()
    a.wait_for('waiting')
    b.client.quick()
    a.wait_for('matched'), b.wait_for('matched')
    b.client.close()
    a.wait_for('opponent_left')
    assert not a.client.send(b'\x01\x00\x00\x00')     # no opponent: the send fails, as GKMatch's did


def test_an_unreachable_server_is_an_error_not_a_crash():
    p = Player('127.0.0.1:1', 'Lonely')
    assert p.wait_for('error') == ('error', 'unreachable')
    p.client.quick()                                  # harmless
    assert not p.client.send(b'\x00')


def test_names_are_tidied_and_limited():
    r = relay.Relay()

    class Out:
        def __init__(self):
            self.lines = []

        def write(self, data):
            self.lines.append(data)
    p = relay.Player(Out())
    assert r.handle(p, {'op': 'hello', 'name': '  Pilot   ' + 'x' * 40, 'version': 1})
    assert p.name.startswith('Pilot x') and len(p.name) == relay.MAX_NAME
    q = relay.Player(Out())
    assert not r.handle(q, {'op': 'hello', 'name': 'Old', 'version': 0})
