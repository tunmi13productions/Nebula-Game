"""UIKit-style screens (main menu, tutorial selection, Hangar, About), read by the screen reader.

In the original these were UIKit view controllers read by VoiceOver: each button or label was one
accessibility element, VoiceOver moved through them in screen order, read the label (adding "button" for
buttons), and a double tap activated the focused one. When a screen appeared VoiceOver focused and read its
first element. Here the down and up arrows move, Home and End jump to the first and last element (VoiceOver's
four-finger taps), Enter activates and Escape goes back (see DEVIATIONS.md), and labels go to the screen
reader through Prism. VoiceOver's own sounds have no counterpart.
"""

from .view import new_view

BACK_DOORS = 1.0   # the doors close over 1 second before a screen is popped

# The word VoiceOver added after a button's label, in the game's language. A Portuguese VoiceOver said
# "botão" itself; a screen reader here may be speaking with any voice, so the word is part of the text.
BUTTON_WORD = {'en': 'button', 'pt': 'botão'}


class Element:
    def __init__(self, label, action=None, button=True, visible=None):
        self._label = label
        self.action = action
        self.button = button
        self._visible = visible

    @property
    def label(self):
        return self._label() if callable(self._label) else self._label

    @property
    def visible(self):
        return self._visible is None or self._visible()

    def spoken(self, language='en'):
        if not self.button:
            return self.label
        return '%s, %s' % (self.label, BUTTON_WORD.get(language, BUTTON_WORD['en']))


class Screen:
    """A screen of accessibility elements. Subclasses fill self.elements in build()."""

    in_menu = True
    is_active = True

    def __init__(self, app):
        self.app = app
        self.services = app.services
        self.elements = []
        self.focus = 0
        self.busy = False   # while a transition runs, input does nothing
        self.view = new_view()   # what the screen draws (visual only)
        self.build()

    def build(self):
        pass

    # what the window calls

    def did_move_to_view(self):
        self.busy = False
        self.focus = 0
        for n in [c for c in self.view.children if c.name == 'loading']:
            n.remove_from_parent()      # a loading view left from the last game
        self.appeared()
        self.announce_first()

    def appeared(self):
        """viewDidAppear: hook for subclasses."""

    def step(self, dt):
        self.view.step(dt)

    def draw(self, surface, renderer):
        renderer.draw_scene(self.view, surface)

    def stop_audio(self):
        pass

    def handle_key(self, key):
        """Keys besides the menu ones. Returns True when handled. key is 'escape', 'left' or 'right'."""
        if key == 'escape':
            self.back()
            return True
        return key in ('left', 'right')

    # focus

    def _visible(self):
        return [e for e in self.elements if e.visible]

    def focused(self):
        items = self._visible()
        if not items:
            return None
        self.focus = min(self.focus, len(items) - 1)
        return items[self.focus]

    def spoken(self, element):
        """An element as VoiceOver read it, with "button" in the game's language."""
        return element.spoken(self.services.strings.language)

    def announce_first(self):
        self.focus = 0
        e = self.focused()
        if e is not None:
            self.say(self.spoken(e))

    def announce(self):
        e = self.focused()
        if e is not None:
            self.say(self.spoken(e))

    def say(self, text):
        self.services.screen_reader.say(text)

    def menu_next(self):
        if self.busy:
            return
        if self.focus + 1 < len(self._visible()):
            self.focus += 1
            self.announce()

    def menu_first(self):
        """Home: VoiceOver's four-finger tap near the top of the screen, which focused the first element
        (DEVIATIONS.md, "Home and End in menus")."""
        if self.busy or not self._visible():
            return
        self.focus = 0
        self.announce()

    def menu_last(self):
        """End: the four-finger tap near the bottom, the last element."""
        if self.busy or not self._visible():
            return
        self.focus = len(self._visible()) - 1
        self.announce()

    def menu_previous(self):
        if self.busy:
            return
        if self.focus > 0:
            self.focus -= 1
            self.announce()

    def menu_activate(self):
        if self.busy:
            return
        e = self.focused()
        if e is not None and e.action is not None:
            e.action()

    # the gameplay keys do nothing on these screens

    def player_shoot(self):
        pass

    def swipe_up(self):
        pass

    def speak_life(self):
        pass

    # navigation

    def back(self):
        """backPressed on the sub screens: the accept sound, the doors close, then the screen is popped."""

    def close_doors_then(self, fn):
        self.busy = True
        self.services.effects.play('acceptButton.mp3')
        self.services.scheduler.after(BACK_DOORS, fn)
