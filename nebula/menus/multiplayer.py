"""The way into versus mode (a port addition in place of Game Center's sign-in and matchmaker, DEVIATIONS.md,
"Multiplayer through a relay server").

The first time, the player chooses a pilot name: typed, or generated from something in the game with digits
after it ("Nebula 482"). The name is kept in the settings and can be changed in Systems. Then the player picks
a quick match (whoever else is waiting) or an invite: hosting gets a four-digit code to read out to a friend,
and joining types a friend's code. Every screen here draws only its own text on black.
"""
import random

from . import view as V
from .screen import Element, Screen
from .text_entry import TextEntryScreen

NAME_WORDS = {
    'en': ('Pilot', 'Starship', 'Nebula', 'Planet', 'Thunder', 'Laser', 'Shield', 'Fireball', 'Star',
           'Fuel Tank'),
    'pt': ('Piloto', 'Nave', 'Nebulosa', 'Planeta', 'Trovão', 'Laser', 'Escudo', 'Bola de Fogo', 'Estrela',
           'Tanque'),
}

WORDS = {
    'en': {
        'title': 'Multiplayer', 'choose': 'Choose a pilot name for multiplayer.', 'enter': 'Enter a name',
        'generate': 'Generate a name', 'back': 'Back', 'type_name': 'Type your pilot name, then press Enter.',
        'name': 'Pilot name', 'your_name': 'Your pilot name is %s.', 'pilot': 'Pilot: %s',
        'quick': 'Quick match', 'host': 'Invite a friend', 'join': 'Join a friend',
        'type_code': "Type your friend's four-digit code, then press Enter.", 'code': 'Code',
        'connecting': 'Connecting.', 'waiting': 'Waiting for another pilot.',
        'your_code': 'Your code is %s. Give it to your friend; waiting for them to join.',
        'unreachable': "Can't reach the multiplayer server.", 'bad_code': 'No game with that code.',
        'version': 'This version of the game is too old for the multiplayer server.',
        'disconnected': 'The connection to the multiplayer server was lost.',
    },
    'pt': {
        'title': 'Multpleier', 'choose': 'Escolha um nome de piloto para o multijogador.',
        'enter': 'Digitar um nome', 'generate': 'Gerar um nome', 'back': 'Voltar',
        'type_name': 'Digite seu nome de piloto e pressione Enter.', 'name': 'Nome de piloto',
        'your_name': 'Seu nome de piloto é %s.', 'pilot': 'Piloto: %s',
        'quick': 'Partida rápida', 'host': 'Convidar um amigo', 'join': 'Entrar na partida de um amigo',
        'type_code': 'Digite o código de quatro dígitos do seu amigo e pressione Enter.',
        'code': 'Código', 'connecting': 'Conectando.', 'waiting': 'Esperando outro piloto.',
        'your_code': 'Seu código é %s. Passe para o seu amigo; esperando ele entrar.',
        'unreachable': 'Não foi possível alcançar o servidor multijogador.',
        'bad_code': 'Nenhuma partida com esse código.',
        'version': 'Esta versão do jogo é antiga demais para o servidor multijogador.',
        'disconnected': 'A conexão com o servidor multijogador caiu.',
    },
}


def words(services):
    return WORDS.get(services.strings.language, WORDS['en'])


def generate_name(language='en', rng=random):
    """Something from the game and a number, like "Nebula 482"."""
    return '%s %d' % (rng.choice(NAME_WORDS.get(language, NAME_WORDS['en'])), rng.randrange(1, 1000))


def spelled(code):
    """A code read digit by digit: "4 8 2 1"."""
    return ' '.join(str(code))


class _TextScreen(Screen):
    """A spoken menu drawn as plain white text on black."""

    def build_pictures(self, title):
        self.view.add_child(V.fill((0.0, 0.0, 0.0, 1.0), 0, 0, V.W, V.H))
        self.view.add_child(V.text(title, 0, 60, V.W, 40, 26, 'Futura', (1.0, 1.0, 1.0), z=2))
        self.lines = []
        for i in range(len(self.elements)):
            line = V.text('', 0, 160 + i * 50, V.W, 40, 18, 'Futura', (1.0, 1.0, 1.0), z=2)
            self.view.add_child(line)
            self.lines.append(line)

    def step(self, dt):
        for i, (e, line) in enumerate(zip(self.elements, self.lines)):
            line.text = e.label
            line.alpha = 1.0 if i == self.focus else 0.6
        super().step(dt)


class NameChoiceScreen(_TextScreen):
    """The first visit: type a name or generate one."""

    def __init__(self, app, then):
        self.then = then
        super().__init__(app)

    def build(self):
        w = words(self.services)
        self.elements = [Element(w['enter'], self.enter), Element(w['generate'], self.generate),
                         Element(w['back'], self.back)]
        self.build_pictures(w['title'])

    def announce_first(self):
        self.focus = 0
        self.say('%s %s' % (words(self.services)['choose'], self.spoken(self.focused())))

    def enter(self):
        w = words(self.services)
        self.services.effects.play('acceptButton.mp3')

        def done(name):
            self.app.set_player_name(name)
            del self.app.stack[-2:]      # the text box and this screen
            self.then()

        self.app.push(TextEntryScreen(self.app, w['type_name'], w['name'], done, self.app.pop, max_length=24))

    def generate(self):
        name = generate_name(self.services.strings.language)
        self.services.effects.play('acceptButton.mp3')
        self.app.set_player_name(name)
        self.app.stack.pop()
        self.then()                      # the multiplayer screen reads "Pilot:" and the name first

    def back(self):
        self.services.effects.play('acceptButton.mp3')
        self.app.pop()


class MultiplayerScreen(_TextScreen):
    """Quick match, invite a friend (host) or join a friend (type their code)."""

    def build(self):
        w = words(self.services)
        self.elements = [
            Element(lambda: w['pilot'] % self.app.player_name(), button=False),
            Element(w['quick'], lambda: self.start('quick')),
            Element(w['host'], lambda: self.start('host')),
            Element(w['join'], self.join),
            Element(w['back'], self.back),
        ]
        self.build_pictures(w['title'])

    def start(self, mode, code=None):
        self.services.effects.play('acceptButton.mp3')
        self.app.start_versus(mode, code)

    def join(self):
        w = words(self.services)
        self.services.effects.play('acceptButton.mp3')

        def done(code):
            self.app.pop()
            self.app.start_versus('join', code)

        self.app.push(TextEntryScreen(self.app, w['type_code'], w['code'], done, self.app.pop, max_length=4,
                                      allowed=set('0123456789')))

    def back(self):
        self.services.effects.play('acceptButton.mp3')
        self.app.pop()
