"""TutorialSelectionViewController.

- BACK (info_voltar), a button across the top of the screen, so VoiceOver read it first. Then six buttons
  labelled with the tutorial names (tut_movimento and so on), tags 1 to 6.
- tutorialSelected: no accept sound. The loading view fades in over 2 seconds, then the game voice says
  "Loading" and the tutorial of that tag starts.
- The first time the screen loads (primeiraVez not yet 1) it selects a tutorial by itself and sets
  primeiraVez to 1. With VoiceOver running that's the movement tutorial (without, the basic one).
- Back: the accept sound, the doors close over 1 second, then the screen is popped.
"""
from .screen import Element, Screen

RATE = 0.55
LOADING_FADE = 2.0
NAMES = ('tut_movimento', 'tut_inimigo', 'tut_ataque', 'tut_batalha', 'tut_basico', 'tut_especial')


class TutorialSelectionScreen(Screen):
    def build(self):
        s = self.services.strings
        self.elements = [Element(s.get('info_voltar'), self.back)]
        self.elements += [Element(s.get(key), (lambda n: lambda: self.select(n))(i + 1))
                          for i, key in enumerate(NAMES)]
        self.first_load = True

    def did_move_to_view(self):
        super().did_move_to_view()
        if self.first_load:
            self.first_load = False
            save = self.services.save
            if save.get('primeiraVez') != 1:
                self.select(1)
                save.set_integer('primeiraVez', 1)
                save.synchronize()

    def select(self, n):
        self.busy = True

        def loaded():
            self.services.voice.speak(self.services.strings.get('tela_load'), RATE)
            self.app.start_tutorial(n)
        self.services.scheduler.after(LOADING_FADE, loaded)

    def back(self):
        self.close_doors_then(self.app.pop)
