"""The game's connection to the Nebula relay (server/relay.py), standing in for the original's GameKitHelper
and GKMatch (DEVIATIONS.md, "Multiplayer through a relay server").

A background thread reads the server; the game calls poll() once a frame and handlers run then, on the game's
own thread, the way GameKit called its delegates on the main thread. Every method is safe to call when the
server can't be reached: the failure arrives as on_error('unreachable').

Handlers (set the ones you need):
    on_welcome(name)          the server accepted the name
    on_waiting()              quick match: waiting for another player
    on_code(code)             invite: the code to read out to a friend
    on_matched(opponent)      a match: the opponent's name
    on_data(payload)          a game message (bytes) from the opponent
    on_opponent_left()        the opponent disconnected or left
    on_error(reason)          'unreachable', 'disconnected', 'bad_code', 'version', 'busy' or 'bad_request'
"""
import base64
import json
import queue
import socket
import threading

PROTOCOL_VERSION = 1
DEFAULT_SERVER = 'tunmi13.com:13013'
CONNECT_TIMEOUT = 8.0


def parse_address(address):
    host, _, port = address.rpartition(':')
    if not host:
        host, port = address, '13013'
    return host, int(port)


class RelayClient:
    def __init__(self, address=DEFAULT_SERVER, connect=socket.create_connection):
        self.address = address
        self._connect = connect
        self._sock = None
        self._inbox = queue.Queue()
        self._lock = threading.Lock()
        self.connected = False
        self.name = None
        self.opponent = None
        for handler in ('welcome', 'waiting', 'code', 'matched', 'data', 'opponent_left', 'error'):
            setattr(self, 'on_' + handler, None)

    # connecting

    def connect(self, name):
        """Connects in the background and introduces the player; on_welcome or on_error follows."""
        threading.Thread(target=self._run, args=(name,), daemon=True).start()

    def _run(self, name):
        try:
            host, port = parse_address(self.address)
            sock = self._connect((host, port), CONNECT_TIMEOUT)
            sock.settimeout(None)
        except (OSError, ValueError):
            self._inbox.put({'op': 'error', 'reason': 'unreachable'})
            return
        with self._lock:
            self._sock = sock
        self._send({'op': 'hello', 'name': name, 'version': PROTOCOL_VERSION})
        buffer = b''
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    try:
                        msg = json.loads(line.decode('utf-8'))
                    except (UnicodeDecodeError, ValueError):
                        continue
                    if isinstance(msg, dict):
                        self._inbox.put(msg)
        except OSError:
            pass
        with self._lock:
            was_ours = self._sock is sock
            if was_ours:
                self._sock = None
        if was_ours:
            self._inbox.put({'op': 'error', 'reason': 'disconnected'})

    def _send(self, message):
        line = (json.dumps(message, separators=(',', ':')) + '\n').encode('utf-8')
        with self._lock:
            sock = self._sock
        if sock is None:
            return False
        try:
            sock.sendall(line)
            return True
        except OSError:
            return False

    # what the game calls

    def quick(self):
        self._send({'op': 'quick'})

    def host(self):
        self._send({'op': 'host'})

    def join(self, code):
        self._send({'op': 'join', 'code': str(code)})

    def cancel(self):
        self._send({'op': 'cancel'})

    def send(self, payload):
        """GKMatch sendDataToAllPlayers: returns False when it couldn't be sent, as the original's did."""
        if self.opponent is None:
            return False
        return self._send({'op': 'data', 'data': base64.b64encode(bytes(payload)).decode('ascii')})

    def leave(self):
        self.opponent = None
        self._send({'op': 'leave'})

    def close(self):
        with self._lock:
            sock, self._sock = self._sock, None
        self.connected = False
        self.opponent = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def poll(self):
        """Runs the handlers for everything that arrived. Call once a frame."""
        while True:
            try:
                msg = self._inbox.get_nowait()
            except queue.Empty:
                return
            op = msg.get('op')
            if op == 'welcome':
                self.connected, self.name = True, msg.get('name')
                self._call('welcome', self.name)
            elif op == 'waiting':
                self._call('waiting')
            elif op == 'code':
                self._call('code', msg.get('code'))
            elif op == 'matched':
                self.opponent = msg.get('opponent')
                self._call('matched', self.opponent)
            elif op == 'data':
                try:
                    payload = base64.b64decode(msg.get('data', ''), validate=True)
                except (ValueError, TypeError):
                    continue
                self._call('data', payload)
            elif op == 'opponent_left':
                self.opponent = None
                self._call('opponent_left')
            elif op == 'error':
                if msg.get('reason') in ('unreachable', 'disconnected'):
                    self.connected, self.opponent = False, None
                self._call('error', msg.get('reason'))

    def _call(self, name, *args):
        handler = getattr(self, 'on_' + name)
        if handler is not None:
            handler(*args)
