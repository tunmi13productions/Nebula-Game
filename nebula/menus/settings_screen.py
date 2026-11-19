"""The Settings screen, a port addition (DEVIATIONS.md, "Settings screen").

Opened from the main menu, as an item after About or with F1. Up and down move through the settings, left
and right change the focused one (the new value is spoken), and Back or Escape saves them and returns. Every
change is written to settings.json at once and put into effect where it can be: steering, the danger zone,
the volumes, the speech rate and the window size. The language takes effect on the next start.

The original had no such screen and no strings for it, so the labels are kept here in English and
Portuguese. It draws only its own text on black.
"""
from . import view as V
from .screen import Element, Screen
from ..settings import DEFAULTS, apply_settings, save_settings, setting

LABELS = {
    'en': {'title': 'Settings', 'back': 'Back', 'tilt': 'Steering speed', 'fast_tilt': 'Fast steering speed, with Shift',
           'danger_zone': 'Danger zone width', 'sound_volume': 'Sound volume', 'music_volume': 'Music volume',
           'speech_volume': 'Speech volume', 'speech_rate': 'Speech rate', 'language': 'Language',
           'scale': 'Window size', 'auto': 'Follow Windows', 'en': 'English', 'pt': 'Portuguese',
           'restart': 'takes effect after a restart', 'hint': 'Left and right arrows change it'},
    'pt': {'title': 'Configurações', 'back': 'Voltar', 'tilt': 'Velocidade de direção',
           'fast_tilt': 'Velocidade rápida, com Shift', 'danger_zone': 'Largura da zona de perigo',
           'sound_volume': 'Volume dos sons', 'music_volume': 'Volume da música',
           'speech_volume': 'Volume da fala', 'speech_rate': 'Velocidade da fala', 'language': 'Idioma',
           'scale': 'Tamanho da janela', 'auto': 'Seguir o Windows', 'en': 'Inglês', 'pt': 'Português',
           'restart': 'vale depois de reiniciar', 'hint': 'Setas esquerda e direita mudam'},
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
}
ORDER = ('tilt', 'fast_tilt', 'danger_zone', 'sound_volume', 'music_volume', 'speech_volume', 'speech_rate',
         'language', 'scale')
RESTART = ('language',)


class SettingsScreen(Screen):
    def __init__(self, app, settings, path=None):
        self.settings, self.path = settings, path
        super().__init__(app)

    def build(self):
        self.words = LABELS.get(self.services.strings.language, LABELS['en'])
        self.elements = [Element(lambda k=key: self.describe(k), button=False) for key in ORDER]
        self.elements.append(Element(self.words['back'], self.back))
        self.keys = list(ORDER) + [None]
        self.build_pictures()

    def build_pictures(self):
        """Only text: the title and one line per setting, white on black."""
        self.view.add_child(V.fill((0.0, 0.0, 0.0, 1.0), 0, 0, V.W, V.H))
        self.view.add_child(V.text(self.words['title'], 0, 30, V.W, 40, 28, 'Futura', (1.0, 1.0, 1.0), z=2))
        self.lines = []
        for i in range(len(self.elements)):
            line = V.text('', 0, 90 + i * 42, V.W, 36, 15, 'Futura', (1.0, 1.0, 1.0), z=2)
            self.view.add_child(line)
            self.lines.append(line)
        self.refresh_pictures()

    def refresh_pictures(self):
        for i, (e, line) in enumerate(zip(self.elements, self.lines)):
            line.text = e.label.replace(', ' + self.words['restart'], ' *')
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
