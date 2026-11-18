"""InfoViewController, the About screen.

Accessibility elements in screen order:
- BACK (info_voltar), across the top.
- An invisible label "About" (info_sobre) over the about image (the image itself is text drawn as a picture).
- CREDITS (info_credito).
- The copyright line (info_gray).

The original also had OUR PAGE (contato_pagina) and SEND EMAIL (contato_email). Gray Company no longer exists,
so those two are removed (DEVIATIONS.md).

CREDITS (creditosPressed) swaps the about part for the credits list and back. While the list shows, the
"About" label leaves the accessibility order. The list has 18 rows: section headers
(the cred_* strings, which start with a space) and names. FreeSFX, OpenGameArt, SoundJay, OpenGameArt and
MillionthVector (rows 7, 8, 9, 11 and 12) are buttons that open the source's web site (buttonListAction).
"""
from .screen import Element, Screen

LINKS = {
    'FreeSFX': 'http://www.freesfx.co.uk/',
    'OpenGameArt': 'http://opengameart.org',
    'SoundJay': 'http://www.soundjay.com/',
    'MillionthVector': 'http://millionthvector.blogspot.de',
}
# The credits array of viewDidLoad. The English build has U+FFFD in two names and in the copyright sign;
# they are restored from the Portuguese strings (see DEVIATIONS.md).
CREDITS = ('cred_devs', 'Bruno Moreira', 'Diego Pereira', 'Felipe Delazeri', 'Leonardo Gubert', 'Lucas Carletti',
           'cred_sounds', 'FreeSFX', 'OpenGameArt', 'SoundJay',
           'cred_design', 'OpenGameArt', 'MillionthVector',
           'cred_teste', 'Márcia Campos', 'Lucas Santurio', 'Raí Carvalho', 'Ricardo Rauber')
LINK_ROWS = (7, 8, 9, 11, 12)


class AboutScreen(Screen):
    def build(self):
        s = self.services.strings
        self.showing_credits = False
        about = lambda: not self.showing_credits
        credits = lambda: self.showing_credits
        rows = []
        for i, entry in enumerate(CREDITS):
            text = s.get(entry) if entry.startswith('cred_') else entry
            if i in LINK_ROWS:
                rows.append(Element(text, (lambda url: lambda: self.app.open_url(url))(LINKS[entry]),
                                    visible=credits))
            else:
                rows.append(Element(text, button=False, visible=credits))
        self.elements = [
            Element(s.get('info_voltar'), self.back),
            Element(s.get('info_sobre'), button=False, visible=about),
            Element(s.get('info_credito'), self.creditos_pressed),
        ] + rows + [
            Element(s.get('info_gray').replace('�', '©'), button=False),
        ]

    def creditos_pressed(self):
        """The credits list and the about part swap. The focus stays on CREDITS."""
        current = self.focused()
        self.showing_credits = not self.showing_credits
        self.focus = self._visible().index(current)

    def back(self):
        self.close_doors_then(self.app.pop)
