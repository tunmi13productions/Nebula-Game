"""The Nebula relay: the port's stand-in for Game Center in versus mode (DEVIATIONS.md, "Multiplayer through a
relay server").

In the original, Game Center named the players, paired them (auto-match or an invite) and carried the
game's own messages between the two phones. This server does the same three things and nothing else: it
never reads the game's messages, so the game logic stays the original's, running on both players' machines.

Protocol: one JSON object per line, UTF-8, over TCP. Game messages travel as base64 in "data".

    client -> server
        {"op": "hello", "name": "Nebula 482", "version": 1}
        {"op": "quick"}                   wait for anyone else doing a quick match
        {"op": "host"}                    get an invite code to read out to a friend
        {"op": "join", "code": "4821"}    join a friend's code
        {"op": "cancel"}                  stop waiting
        {"op": "data", "data": "..."}     a game message for the opponent
        {"op": "leave"}                   leave the match
    server -> client
        {"op": "welcome", "name": "..."}
        {"op": "waiting"}
        {"op": "code", "code": "4821"}
        {"op": "matched", "opponent": "..."}
        {"op": "data", "data": "..."}
        {"op": "opponent_left"}
        {"op": "error", "reason": "bad_code" | "bad_request" | "version"}

usage: python server/relay.py [--host 0.0.0.0] [--port 13013]
Needs Python 3.8 or newer and nothing else.
"""
import argparse
import asyncio
import json
import logging
import random

PROTOCOL_VERSION = 1
DEFAULT_PORT = 13013
MAX_LINE = 4096          # bytes; the game's largest message is 20 bytes before base64
MAX_NAME = 24
IDLE_TIMEOUT = 600.0     # seconds without a line before a connection is dropped

log = logging.getLogger('relay')


class Player:
    def __init__(self, writer):
        self.writer = writer
        self.name = None
        self.opponent = None
        self.waiting = None       # 'quick' or an invite code

    def send(self, **message):
        try:
            self.writer.write((json.dumps(message, separators=(',', ':')) + '\n').encode('utf-8'))
        except Exception:
            pass


class Relay:
    def __init__(self):
        self.quick = None         # the player waiting for a quick match
        self.codes = {}           # invite code -> hosting player

    # pairing

    def _stop_waiting(self, p):
        if p.waiting == 'quick' and self.quick is p:
            self.quick = None
        elif p.waiting and self.codes.get(p.waiting) is p:
            del self.codes[p.waiting]
        p.waiting = None

    def _pair(self, a, b):
        self._stop_waiting(a)
        self._stop_waiting(b)
        a.opponent, b.opponent = b, a
        a.send(op='matched', opponent=b.name)
        b.send(op='matched', opponent=a.name)
        log.info('matched %s with %s', a.name, b.name)

    def _part(self, p):
        """p leaves its match; the other player is told."""
        other, p.opponent = p.opponent, None
        if other is not None:
            other.opponent = None
            other.send(op='opponent_left')

    def _new_code(self):
        for _ in range(1000):
            code = '%04d' % random.randrange(10000)
            if code not in self.codes:
                return code
        return None

    # messages

    def handle(self, p, msg):
        op = msg.get('op')
        if op == 'hello':
            if msg.get('version') != PROTOCOL_VERSION:
                p.send(op='error', reason='version')
                return False
            name = ' '.join(str(msg.get('name', '')).split())[:MAX_NAME]
            p.name = name or 'Pilot %d' % random.randrange(1000)
            p.send(op='welcome', name=p.name)
            return True
        if p.name is None:
            p.send(op='error', reason='bad_request')
            return False
        if op == 'quick':
            self._part(p)
            self._stop_waiting(p)
            if self.quick is not None and self.quick is not p:
                self._pair(self.quick, p)
            else:
                self.quick, p.waiting = p, 'quick'
                p.send(op='waiting')
        elif op == 'host':
            self._part(p)
            self._stop_waiting(p)
            code = self._new_code()
            if code is None:
                p.send(op='error', reason='busy')
            else:
                self.codes[code], p.waiting = p, code
                p.send(op='code', code=code)
        elif op == 'join':
            self._part(p)
            self._stop_waiting(p)
            host = self.codes.get(str(msg.get('code', '')).strip())
            if host is None or host is p:
                p.send(op='error', reason='bad_code')
            else:
                self._pair(host, p)
        elif op == 'cancel':
            self._stop_waiting(p)
        elif op == 'data':
            data = msg.get('data')
            if p.opponent is not None and isinstance(data, str):
                p.opponent.send(op='data', data=data)
        elif op == 'leave':
            self._part(p)
        else:
            p.send(op='error', reason='bad_request')
        return True

    def gone(self, p):
        self._stop_waiting(p)
        self._part(p)

    async def serve_client(self, reader, writer):
        p = Player(writer)
        try:
            while True:
                try:
                    line = await asyncio.wait_for(reader.readline(), IDLE_TIMEOUT)
                except (asyncio.TimeoutError, ValueError):
                    break             # idle, or a line longer than the reader's limit
                if not line or len(line) > MAX_LINE:
                    break
                try:
                    msg = json.loads(line.decode('utf-8'))
                except (UnicodeDecodeError, ValueError):
                    break
                if not isinstance(msg, dict) or not self.handle(p, msg):
                    break
                await writer.drain()
        except (ConnectionError, OSError):
            pass
        finally:
            self.gone(p)
            try:
                writer.close()
            except Exception:
                pass


async def run(host, port, ready=None):
    relay = Relay()
    server = await asyncio.start_server(relay.serve_client, host, port, limit=MAX_LINE)
    if ready is not None:
        ready(server.sockets[0].getsockname()[1])
    log.info('relay listening on %s:%d', host, port)
    async with server:
        await server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description='The Nebula multiplayer relay.')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    try:
        asyncio.run(run(args.host, args.port))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
