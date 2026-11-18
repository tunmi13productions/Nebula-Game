"""MainMenuViewController.

Button titles come from the storyboard (data/strings/storyboard_*.json). Buttons, in screen order (the
order VoiceOver read them): Campaign (tag 1), Free Mode (tag 2), Tutorial (tag 3), Hangar (tag 5), About
(tag 6). Multiplayer (tag 4) is left out with versus mode (DEVIATIONS.md).

- Every button plays the accept sound first.
- Campaign and Free Mode show the loading screen: it fades in over 2 seconds, then the game voice says
  "Loading" (tela_load) and the game screen opens.
- Tutorial, Hangar and About push their screens.
- The first time the menu loads, a white flash runs for 1 second and then the doors open with
  closing_doors.caf.
- Every time the menu appears, ControleCapitulo is reset to "no".
- The original declares a menu music player (Global.mainMenuMusic, menuSound.mp3), but nothing ever creates
  it, so the menu is silent apart from the doors. The first-launch alert (alertViewTutorial) is never called
  either.
"""
from .screen import Element, Screen

RATE = 0.55
LOADING_FADE = 2.0
DOORS_DELAY = 1.0


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
        if not self.loaded:
            self.loaded = True
            self.services.scheduler.after(DOORS_DELAY, lambda: self.services.effects.play('closing_doors.caf'))

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
