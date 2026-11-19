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
from . import view as V
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
        self.build_pictures(rows)

    def build_pictures(self, rows):
        """The look (visual only). Partly traced, partly approximate: the emulator can't run this screen's
        viewDidLoad. portaLisa over the screen, the back picture at the top, the "ABOUT" picture (sobre_en,
        H / 5.8 tall) in the upper part, the "CREDITS" picture centred at H / 1.35, a divider at H / 1.2, the
        Gray Company logo (gray.png) below it and the copyright line along the bottom (y 0.94 H, H / 15 tall).
        OUR PAGE, SEND EMAIL (site_en, email_en) and the divider between them went with those buttons
        (DEVIATIONS.md). With the credits open, the list replaces the about picture, as text."""
        W, H = V.W, V.H
        s = self.services.strings
        self.view.add_child(V.image('portaLisa', 0, 0, W, H))
        self.view.add_child(V.image(V.localized('back', s), W / 4, H / 26.625 - 24.615, W / 2, 49.2308, z=3))
        sh = H / 5.8
        sw = sh * 698 / 252
        self.about_picture = V.image(V.localized('sobre', s), (W - sw) / 2, H * 0.17, sw, sh, z=1)
        self.view.add_child(self.about_picture)
        ch = H / 9
        cw = ch * 457 / 149
        self.view.add_child(V.image(V.localized('creditos', s), (W - cw) / 2, H / 1.35 - ch / 2, cw, ch, z=1))
        self.view.add_child(V.image('divisoria', 0, H / 1.2 - H * 0.01, W, H * 0.02, z=1))
        gh = H / 9
        gw = gh * 583 / 207
        self.view.add_child(V.image('gray', (W - gw) / 2, H / 1.2 + 4, gw, gh, z=1))
        self.view.add_child(V.text(s.get('info_gray').replace('�', '©'), 0, H * 0.94, W, H / 15, 12,
                                   'Futura', z=2))
        self.credit_lines = []
        for i, row in enumerate(rows):
            header = i in (0, 6, 10, 13)
            color = (1.0, 0.6, 0.1) if header else (1.0, 1.0, 1.0)
            line = V.text(row.label.strip(), 0, H * 0.12 + i * 16.5, W, 16.5, 14 if header else 13, 'Futura',
                          color, z=2)
            line.hidden = True
            self.view.add_child(line)
            self.credit_lines.append(line)
        self.doors = V.Doors(self.view, s)

    def did_move_to_view(self):
        super().did_move_to_view()
        self.doors.open()

    def creditos_pressed(self):
        """The credits list and the about part swap. The focus stays on CREDITS."""
        current = self.focused()
        self.showing_credits = not self.showing_credits
        self.focus = self._visible().index(current)
        self.about_picture.hidden = self.showing_credits
        for line in self.credit_lines:
            line.hidden = not self.showing_credits

    def back(self):
        self.doors.close()
        self.close_doors_then(self.app.pop)
