"""MainMenuViewController.

Button titles come from the storyboard (data/strings/storyboard_*.json). Buttons, in screen order (the
order VoiceOver read them): Campaign (tag 1), Free Mode (tag 2), Tutorial (tag 3), Hangar (tag 5), About
(tag 6). Multiplayer (tag 4) is left out with versus mode (DEVIATIONS.md).

- Every button plays the accept sound first.
- Campaign and Free Mode show the loading screen: it fades in over 2 seconds, then the game voice says
  "Loading" (tela_load) and the game screen opens.
- Tutorial, Hangar and About push their screens.
- The first time the menu loads, an animation chain runs: a white flash fades over 1 second, the doors fade
  in over 1 second, then open over 0.4 seconds while closing_doors.caf plays (at 2 seconds), then two
  0.5 second steps. When the chain ends (3.4 seconds) the block "Toca Som" creates the menu music
  (menuSound.mp3, looping forever, full volume, kept in Global.mainMenuMusic), plays it if the menu is on
  screen, and shows the first-launch alert when primeiraVez isn't 1.
- Every time the menu appears, ControleCapitulo is reset to "no" and the menu music plays if it exists.
- Gameplay stops the music: free mode on entry and the campaign when a level starts. Tutorials don't.
"""
from .screen import Element, Screen

RATE = 0.55
LOADING_FADE = 2.0
DOORS_DELAY = 2.0      # the 1 second flash, then the 1 second door fade-in
MUSIC_DELAY = 3.4      # then the 0.4 second door opening and two 0.5 second steps


class MainMenuScreen(Screen):
    def build(self):
        s = self.services.strings
        self.loaded = False
        self.elements = [
            Element(s.get('hVd-Ez-Tht.normalTitle'), lambda: self.load_game(self.app.open_campaign)),
            Element(s.get('V1V-dx-jYs.normalTitle'), lambda: self.load_game(self.app.open_free_mode)),
            Element(s.get('mXA-bH-dA4.normalTitle'), lambda: self.open(self.app.open_tutorial_selection)),
            Element(s.get('WWl-xv-diA.normalTitle'), lambda: self.open(self.app.open_hangar)),
            Element(s.get('ZcV-1U-Bf2.normalTitle'), lambda: self.open(self.app.open_about)),
        ]

    def appeared(self):
        save = self.services.save
        save.set('ControleCapitulo', 'no')
        save.synchronize()
        self.app.play_menu_music()
        if not self.loaded:
            self.loaded = True
            self.services.scheduler.after(DOORS_DELAY, lambda: self.services.effects.play('closing_doors.caf'))
            self.services.scheduler.after(MUSIC_DELAY, self.toca_som)

    def toca_som(self):
        """The last completion of the opening animation."""
        self.app.create_menu_music()
        if self.app.window.scene is self:
            self.app.play_menu_music()
        if self.services.save.get('primeiraVez') != 1:
            self.app.window.set_scene(TutorialAlert(self))

    def open(self, fn):
        self.services.effects.play('acceptButton.mp3')
        fn()

    def load_game(self, fn):
        """buttonPressed: the loading view fades in, then "Loading" is spoken and the game screen opens."""
        self.busy = True
        self.services.effects.play('acceptButton.mp3')

        def loaded():
            self.services.voice.speak(self.services.strings.get('tela_load'), RATE)
            fn()
        self.services.scheduler.after(LOADING_FADE, loaded)

    def handle_key(self, key):
        return key in ('escape', 'left', 'right')


class TutorialAlert(Screen):
    """alertViewTutorial: a UIAlertView over the menu. VoiceOver read the title and message and focused the
    first button. "Go to tutorial" (the cancel button, index 0) opens the tutorial selection, which then
    starts the movement tutorial because primeiraVez is still unset. "Cancel" (index 1) sets primeiraVez to
    1. Escape is the alert's escape action, which picks the cancel button, "Go to tutorial"."""

    def __init__(self, menu):
        self.menu = menu
        super().__init__(menu.app)

    def build(self):
        s = self.services.strings
        self.elements = [Element(s.get('alert_titulo'), button=False), Element(s.get('alert_mesagem'), button=False),
                         Element(s.get('alert_irTutorial'), self.go), Element(s.get('alert_cancelar'), self.cancel)]

    def did_move_to_view(self):
        self.busy = False
        self.focus = 2
        s = self.services.strings
        self.say('%s, %s, %s' % (s.get('alert_titulo'), s.get('alert_mesagem'), self.elements[2].spoken()))

    def _dismiss(self):
        self.app.window.scene = self.menu   # the menu stays as it was under the alert

    def go(self):
        self._dismiss()
        self.menu.open(self.app.open_tutorial_selection)

    def cancel(self):
        save = self.services.save
        save.set_integer('primeiraVez', 1)
        save.synchronize()
        self._dismiss()
        self.menu.announce_first()

    def handle_key(self, key):
        if key == 'escape':
            self.go()
        return True
