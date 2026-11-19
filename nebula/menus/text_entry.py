"""A screen holding one text box: the prompt and the box are read on arrival, Enter confirms and Escape cancels
(a port addition, DEVIATIONS.md, "Multiplayer through a relay server"). It draws only its own text on black.
"""
from . import view as V
from .screen import Screen
from .textbox import TextBox


class TextEntryScreen(Screen):
    def __init__(self, app, prompt, label, on_done, on_cancel, max_length=24, allowed=None, value=''):
        """on_done(text) gets the trimmed text; an empty box isn't accepted. on_cancel() runs on Escape."""
        self.prompt, self.label = prompt, label
        self.on_done, self.on_cancel = on_done, on_cancel
        self.max_length, self.allowed, self.value = max_length, allowed, value
        super().__init__(app)

    def build(self):
        s = self.services
        self.box = TextBox(self.label, s.screen_reader.say, lambda: s.effects.play('errorButton.mp3'),
                           s.strings.language, self.max_length, self.allowed, self.value)
        self.view.add_child(V.fill((0.0, 0.0, 0.0, 1.0), 0, 0, V.W, V.H))
        self.view.add_child(V.text(self.prompt, 0, 160, V.W, 40, 20, 'Futura', (1.0, 1.0, 1.0), z=2))
        self.line = V.text('', 0, 240, V.W, 40, 22, 'Futura', (1.0, 1.0, 1.0), z=2)
        self.view.add_child(self.line)

    def step(self, dt):
        self.line.text = self.box.text
        super().step(dt)

    def announce_first(self):
        joiner = ' ' if self.prompt.rstrip()[-1:] in '.!?:' else '. '
        self.say('%s%s%s' % (self.prompt.rstrip(), joiner, self.box.describe()))

    def announce(self):
        self.say(self.box.describe())

    def menu_next(self):
        self.announce()

    def menu_previous(self):
        self.announce()

    def menu_first(self):
        self.box.edge_jump(False)

    def menu_last(self):
        self.box.edge_jump(True)

    def handle_text_event(self, event):
        """Typing and editing keys go to the box first; the window passes every key and text event here."""
        if self.busy:
            return True
        return self.box.handle_event(event)

    def menu_activate(self):
        if self.busy:
            return
        text = ' '.join(self.box.text.split())
        if not text:
            self.services.effects.play('errorButton.mp3')
            self.say(self.box.words['blank'])
            return
        self.busy = True
        self.services.effects.play('acceptButton.mp3')
        self.on_done(text)

    def handle_key(self, key):
        if key == 'escape':
            if not self.busy:
                self.busy = True
                self.on_cancel()
            return True
        return key in ('left', 'right', 'control')

    def back(self):
        self.handle_key('escape')
