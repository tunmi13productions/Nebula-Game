"""TutorialSelectionViewController.

- BACK (info_voltar), a button across the top of the screen, so VoiceOver read it first. Then six buttons
  labelled with the tutorial names (tut_movimento and so on), tags 1 to 6.
- tutorialSelected: no accept sound. The loading view fades in over 2 seconds, then the game voice says
  "Loading" and the tutorial of that tag starts.
- The first time the screen loads (primeiraVez not yet 1) it selects a tutorial by itself and sets
  primeiraVez to 1. With VoiceOver running that's the movement tutorial (without, the basic one).
- Back: the accept sound, the doors close over 1 second, then the screen is popped.
"""
from . import view as V
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
        self.build_pictures()

    def build_pictures(self):
        """viewDidLoad's look (visual only): portaLisaTutorial over the screen, the six word pictures
        (tut_*_en) as 160 by 189.3 point buttons in two columns and three rows, dividers between the rows,
        barraInferior at the bottom, the back picture at the top, and the doors."""
        W, H = V.W, V.H
        s = self.services.strings
        self.view.add_child(V.image('portaLisaTutorial', 0, 0, W, H))
        bh = H / 3
        cells = {'tut_movimento': (0, 0), 'tut_inimigo': (1, 0), 'tut_ataque': (0, 1), 'tut_batalha': (1, 1),
                 'tut_especial': (0, 2), 'tut_basico': (1, 2)}
        for name, (col, row) in cells.items():
            self.view.add_child(V.image(V.localized(name, s), col * W / 2, row * bh, W / 2, bh, z=1))
        for y in (bh, bh * 2):
            self.view.add_child(V.image('divisoria', 0, y - 3.2, W, 6.4, z=2))
        self.view.add_child(V.image('barraInferior', 0, H * 0.99 - H / 53.25, W, H / 26.625, z=2))
        self.view.add_child(V.image(V.localized('back', s), W / 4, H / 26.625 - 24.615, W / 2, 49.2308, z=3))
        self.doors = V.Doors(self.view, s)

    def did_move_to_view(self):
        super().did_move_to_view()
        self.doors.open()
        if self.first_load:
            self.first_load = False
            save = self.services.save
            if save.get('primeiraVez') != 1:
                self.select(1)
                save.set_integer('primeiraVez', 1)
                save.synchronize()

    def select(self, n):
        self.busy = True
        self.view.add_child(V.loading_view(self.services.strings))

        def loaded():
            self.services.voice.speak(self.services.strings.get('tela_load'), RATE)
            self.app.start_tutorial(n)
        self.services.scheduler.after(LOADING_FADE, loaded)

    def back(self):
        self.doors.close()
        self.close_doors_then(self.app.pop)
