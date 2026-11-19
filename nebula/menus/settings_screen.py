"""The Systems screen (the settings), a port addition (DEVIATIONS.md, "Settings screen").

Opened from the main menu, as the Systems item in Multiplayer's old slot or with F1. Up and down move
through the settings, left and right change the focused one (the new value is spoken), and Back or Escape saves them and returns. Every
change is written to settings.json at once and put into effect where it can be: steering, the danger zone,
the volumes, the speech rate and the window size. The language takes effect on the next start.

The original had no such screen and no strings for it, so the labels are kept here in English and
Portuguese. It draws only its own text on black.
"""
from . import view as V
from .screen import Element, Screen
from ..settings import DEFAULTS, apply_settings, save_settings, setting

LABELS = {
    'en': {'title': 'Systems', 'back': 'Back', 'tilt': 'Steering speed', 'fast_tilt': 'Fast steering speed, with Shift',
           'danger_zone': 'Danger zone width', 'sound_volume': 'Sound volume', 'music_volume': 'Music volume',
           'speech_volume': 'Speech volume', 'speech_rate': 'Speech rate', 'language': 'Language',
           'scale': 'Window size', 'auto': 'Follow Windows', 'en': 'English', 'pt': 'Portuguese',
           'restart': 'takes effect after a restart', 'hint': 'Left and right arrows change it',
           'controller_tilt': 'Controller tilt steering', 'controller_tilt_scale': 'Controller tilt sensitivity',
           'vibration': 'Controller vibration', 'on': 'On', 'off': 'Off',
           'game_voice': 'Game voice', 'voice': 'Built-in voice', 'screen_reader': 'Screen reader, experimental'},
    'pt': {'title': 'Sistemas', 'back': 'Voltar', 'tilt': 'Velocidade de direção',
           'fast_tilt': 'Velocidade rápida, com Shift', 'danger_zone': 'Largura da zona de perigo',
           'sound_volume': 'Volume dos sons', 'music_volume': 'Volume da música',
           'speech_volume': 'Volume da fala', 'speech_rate': 'Velocidade da fala', 'language': 'Idioma',
           'scale': 'Tamanho da janela', 'auto': 'Seguir o Windows', 'en': 'Inglês', 'pt': 'Português',
           'restart': 'vale depois de reiniciar', 'hint': 'Setas esquerda e direita mudam',
           'controller_tilt': 'Direção inclinando o controle',
           'controller_tilt_scale': 'Sensibilidade da inclinação do controle',
           'vibration': 'Vibração do controle', 'on': 'Ligado', 'off': 'Desligado',
           'game_voice': 'Voz do jogo', 'voice': 'Voz própria', 'screen_reader': 'Leitor de tela, experimental'},
}

# What each option does, spoken after its name and value when it's focused.
EXPLAIN = {
    'en': {
        'tilt': 'How fast the ship slides while you hold an arrow key. Higher is faster. 1 is like tipping the '
                'phone fully on its side.',
        'fast_tilt': 'The same, while you also hold Shift.',
        'danger_zone': "How wide the area is where an enemy's shots and lasers sound straight ahead of you. "
                       'At 1, they sound centred about when they could hit you. Higher also centres near misses, '
                       'so you start dodging sooner. Lower centres only the shots right in front of you.',
        'sound_volume': 'Ships, shots, explosions and the other game sounds.',
        'music_volume': 'The music.',
        'speech_volume': "The game's own voice and the story narration. Your screen reader is not affected.",
        'speech_rate': "How fast the game's own voice talks. 1 is the original speed. Your screen reader is not "
                       'affected.',
        'language': "The game's language. Follow Windows uses your Windows display language.",
        'scale': 'The size of the game window on screen, for anyone watching.',
        'controller_tilt': 'With a controller that senses motion, like a DualSense, roll it left or right to '
                           'steer, the way the phone was tilted. The arrows, D-pad and stick still work.',
        'controller_tilt_scale': 'How far you need to roll the controller. Higher means a smaller roll steers '
                                 'harder. At 1, rolling it fully onto its side is the steepest tilt.',
        'vibration': 'The controller buzzes when you are hit, longer when you explode, a small pulse for a '
                     'power-up, and on the left or right side when you reach that edge of the screen.',
        'game_voice': "Experimental, and may not behave as intended. The original spoke the game's lines with "
                      "Apple's speech synthesizer, not VoiceOver. Screen reader sends them to your screen reader "
                      'instead. Where the game waits for a line to finish, you will be asked to press Enter or '
                      'Space to continue.',
    },
    'pt': {
        'tilt': 'A velocidade com que a nave desliza enquanto você segura uma seta. Maior é mais '
                'rápido. 1 é como deitar o celular totalmente de lado.',
        'fast_tilt': 'O mesmo, enquanto você também segura Shift.',
        'danger_zone': 'A largura da área em que os tiros e lasers inimigos soam bem à sua frente. '
                       'Em 1, eles soam no centro mais ou menos quando podem te acertar. Maior também '
                       'centraliza os tiros que passam perto, para você desviar antes. Menor centraliza '
                       'só os tiros bem à sua frente.',
        'sound_volume': 'Naves, tiros, explosões e os outros sons do jogo.',
        'music_volume': 'A música.',
        'speech_volume': 'A voz do próprio jogo e a narração da história. Seu leitor de '
                         'tela não muda.',
        'speech_rate': 'A velocidade da voz do próprio jogo. 1 é a velocidade original. Seu leitor '
                       'de tela não muda.',
        'language': 'O idioma do jogo. Seguir o Windows usa o idioma de exibição do Windows.',
        'scale': 'O tamanho da janela do jogo na tela, para quem estiver assistindo.',
        'controller_tilt': 'Com um controle que sente movimento, como o DualSense, incline-o para a esquerda '
                           'ou direita para guiar, como se inclinava o celular. As setas, o direcional e o '
                           'analógico continuam funcionando.',
        'controller_tilt_scale': 'O quanto você precisa inclinar o controle. Maior significa que uma '
                                 'inclinação menor guia mais forte. Em 1, deitar o controle de lado '
                                 'é a inclinação máxima.',
        'vibration': 'O controle vibra quando você é atingido, mais longo quando você explode, '
                     'um pulso curto ao pegar um power-up, e do lado esquerdo ou direito ao chegar nessa borda '
                     'da tela.',
        'game_voice': 'Experimental, e pode não funcionar como esperado. O original falava as falas do jogo '
                      'com o sintetizador de voz da Apple, não com o VoiceOver. Leitor de tela as envia ao seu '
                      'leitor de tela. Onde o jogo espera uma fala terminar, você será solicitado a pressionar '
                      'Enter ou Espaço para continuar.',
    },
}

# key: (kind, minimum, maximum, step) or ('choice', options)
RANGES = {
    'tilt': ('number', 0.1, 1.0, 0.05),
    'fast_tilt': ('number', 0.1, 1.0, 0.05),
    'danger_zone': ('number', 0.5, 3.0, 0.25),
    'sound_volume': ('percent', 0.0, 1.0, 0.1),
    'music_volume': ('percent', 0.0, 1.0, 0.1),
    'speech_volume': ('percent', 0.0, 1.0, 0.1),
    'speech_rate': ('number', 0.5, 1.8, 0.1),
    'language': ('choice', ('auto', 'en', 'pt')),
    'scale': ('number', 1.0, 3.0, 0.25),
    'controller_tilt': ('choice', ('on', 'off')),
    'controller_tilt_scale': ('number', 0.25, 3.0, 0.25),
    'vibration': ('choice', ('on', 'off')),
    'game_voice': ('choice', ('voice', 'screen_reader')),
}
ORDER = ('tilt', 'fast_tilt', 'controller_tilt', 'controller_tilt_scale', 'danger_zone', 'vibration',
         'sound_volume', 'music_volume', 'speech_volume', 'speech_rate', 'game_voice', 'language', 'scale')
RESTART = ('language',)


class SettingsScreen(Screen):
    def __init__(self, app, settings, path=None):
        self.settings, self.path = settings, path
        super().__init__(app)

    def build(self):
        lang = self.services.strings.language
        self.words = LABELS.get(lang, LABELS['en'])
        self.explain = EXPLAIN.get(lang, EXPLAIN['en'])
        self.elements = [Element(lambda k=key: '%s. %s' % (self.describe(k), self.explain[k]), button=False)
                         for key in ORDER]
        self.elements.append(Element(self.words['back'], self.back))
        self.keys = list(ORDER) + [None]
        self.build_pictures()

    def build_pictures(self):
        """Only text: the title and one line per setting, white on black."""
        self.view.add_child(V.fill((0.0, 0.0, 0.0, 1.0), 0, 0, V.W, V.H))
        self.view.add_child(V.text(self.words['title'], 0, 30, V.W, 40, 28, 'Futura', (1.0, 1.0, 1.0), z=2))
        self.lines = []
        for i in range(len(self.elements)):
            line = V.text('', 0, 80 + i * 34, V.W, 30, 14, 'Futura', (1.0, 1.0, 1.0), z=2)
            self.view.add_child(line)
            self.lines.append(line)
        self.refresh_pictures()

    def refresh_pictures(self):
        for i, (e, key, line) in enumerate(zip(self.elements, self.keys, self.lines)):
            line.text = '%s, %s' % (self.words[key], self.value_text(key)) if key else e.label
            line.alpha = 1.0 if i == self.focus else 0.6

    def step(self, dt):
        self.refresh_pictures()
        super().step(dt)

    # values

    def value(self, key):
        return setting(self.settings, key)

    def value_text(self, key):
        v = self.value(key)
        kind = RANGES[key][0]
        if kind == 'choice':
            return self.words.get(v, v)
        if kind == 'percent':
            return '%d%%' % round(float(v) * 100)
        if key == 'scale':
            return '%gx' % float(v)
        return '%g' % round(float(v), 2)

    def describe(self, key):
        text = '%s, %s' % (self.words[key], self.value_text(key))
        if key in RESTART:
            text += ', ' + self.words['restart']
        return text

    def announce_first(self):
        """The title, the first setting, and how to change it."""
        self.focus = 0
        self.say('%s. %s. %s' % (self.words['title'], self.focused().spoken(), self.words['hint']))

    def change(self, direction):
        e = self.focused()
        key = self.keys[self.elements.index(e)] if e is not None else None
        if key is None:
            return
        spec = RANGES[key]
        if spec[0] == 'choice':
            options = spec[1]
            current = self.value(key)
            i = options.index(current) if current in options else 0
            new = options[(i + direction) % len(options)]
        else:
            _, low, high, stepsize = spec
            new = round(min(high, max(low, float(self.value(key)) + direction * stepsize)), 2)
            if new == round(float(self.value(key)), 2):
                self.say(self.value_text(key))
                return
        self.settings[key] = new
        if key == 'danger_zone':
            self.settings.pop('laser_zone', None)
        self.save()
        apply_settings(self.settings, self.services, self.app.tilt, self.app.window)
        if key == 'music_volume' and self.app.menu_music is not None:
            self.app.menu_music.apply_volume()
        self.say(self.value_text(key))

    def save(self):
        try:
            save_settings(self.settings, self.path)
        except OSError:
            pass

    def handle_key(self, key):
        if key == 'escape':
            self.back()
            return True
        if key in ('left', 'right'):
            if not self.busy:
                self.change(-1 if key == 'left' else 1)
            return True
        return False

    def back(self):
        if self.busy:
            return
        self.busy = True
        self.services.effects.play('acceptButton.mp3')
        self.save()
        self.app.pop()


__all__ = ['SettingsScreen', 'DEFAULTS']
