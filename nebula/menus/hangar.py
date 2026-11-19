"""SettingsViewController, the Hangar: spending upgrade points.

Accessibility elements in screen order:
- BACK (info_voltar), a button across the top.
- "%ld AVAILABLE POINTS" (pontosDisponiveis, showing winPoints).
- For each stat (Life, Shield, Ship speed, Attack speed, Power shot): its label, "Life, %ld points" and
  so on (lbl_*_points), then its plus button, "Life, %ld points. %d available points. Add points."
  (lbl_*_points_button). checkForButtonLock takes a plus button out of the accessibility order when its
  stat is at 5 or no points are left.

actionUpPower: with no points left it only refreshes the labels. Otherwise the accept sound plays, the stat
goes up by 1 (up to 5), a point is spent and the points are saved. Nothing is announced; VoiceOver stayed
on the button.

Back: the accept sound, ControleCapitulo goes back to "no", the doors close over 1 second and the screen is
popped.
"""
from . import view as V
from .screen import Element, Screen

MAX_POINTS = 5
STATS = (
    ('life_points', 'lbl_life_points', 'lbl_life_points_button'),
    ('shield_points', 'lbl_shield_points', 'lbl_shield_points_button'),
    ('speed_points', 'lbl_speed_points', 'lbl_speed_points_button'),
    ('time_shot_points', 'lbl_atkSpeed_points', 'lbl_atkSpeed_points_button'),
    ('shot_points', 'lbl_power_points', 'lbl_power_points_button'),
)


class HangarScreen(Screen):
    def __init__(self, app, return_to=None):
        self.return_to = return_to
        super().__init__(app)

    def build(self):
        s, g = self.services.strings, self.services.globals
        self.elements = [
            Element(s.get('info_voltar'), self.back),
            Element(lambda: s.format('pontosDisponiveis', g.win_points), button=False),
        ]
        for attr, label_key, button_key in STATS:
            self.elements.append(Element((lambda a, k: lambda: s.format(k, getattr(g, a)))(attr, label_key),
                                         button=False))
            self.elements.append(Element(
                (lambda a, k: lambda: s.format(k, getattr(g, a), g.win_points))(attr, button_key),
                (lambda a: lambda: self.action_up_power(a))(attr),
                visible=(lambda a: lambda: getattr(g, a) < MAX_POINTS and g.win_points >= 1)(attr)))
        self.build_pictures()

    def build_pictures(self):
        """viewDidLoad's look (visual only), from the traced frames: portaLisa over the screen; "N AVAILABLE
        POINTS" centred near the top; the five stat names (lbl_*, white 0.9 at half opacity, bold condensed
        21 points) at x 48 every 56.8 points from y 113.6; under each an empty glass bar (Vidro_Vazio, 256 by
        28.4) with the filled glass (Vidro_Preenchimento) at 256 / 5 per point; a plus button (42.6 square)
        at the left, PlusActive when it can be used, PlusInactive otherwise; the ship (95.85 by 153.36) on
        base_ship and base_ship2 at the bottom; the back picture at the top; and the doors."""
        W, H = V.W, V.H
        s, g = self.services.strings, self.services.globals
        self.view.add_child(V.image('portaLisa', 0, 0, W, H))
        grey = (0.9, 0.9, 0.9)
        self.points_label = V.text('', 0, 81.1429 - 14.2, W, 28.4, 21, 'Futura-CondensedExtraBold', grey, z=2)
        self.points_label.alpha = 0.5
        self.view.add_child(self.points_label)
        names = ('lbl_life', 'lbl_shield', 'lbl_speed', 'lbl_atkSpeed', 'lbl_power')
        self.fills, self.pluses = [], []
        for i, ((attr, _, _), name) in enumerate(zip(STATS, names)):
            y = 113.6 + 56.8 * i
            label = V.text(s.get(name), 48, y, 160, 28.4, 21, 'Futura-CondensedExtraBold', grey, z=2)
            label.alpha, label.align = 0.5, 'left'
            label.position = (48.0, label.position[1])
            self.view.add_child(label)
            self.view.add_child(V.image('Vidro_Vazio', 48, y + 28.4, 256, 28.4, z=1))
            fill = V.image('Vidro_Preenchimento', 48, y + 28.4, 0, 28.4, z=2)
            fill.anchor = (0.0, 0.5)
            fill.position = (48, fill.position[1])
            self.view.add_child(fill)
            self.fills.append((attr, fill))
            plus = V.image('PlusInactive', 2.7, y + 14.2, 42.6, 42.6, z=2)
            self.view.add_child(plus)
            self.pluses.append((attr, plus))
        self.view.add_child(V.image('base_ship2', 74.8, 397.6, 170.4, 170.4, z=1))
        self.view.add_child(V.image('base_ship', 74.8, 397.6, 170.4, 170.4, z=2))
        self.view.add_child(V.image('ship', 160 - 95.85 / 2, 482.8 - 153.36 / 2, 95.85, 153.36, z=3))
        self.view.add_child(V.image(V.localized('back', s), W / 4, 21.3333 - 24.615, W / 2, 49.2308, z=3))
        self.doors = V.Doors(self.view, s)
        self.refresh_pictures()

    def refresh_pictures(self):
        g = self.services.globals
        self.points_label.text = self.services.strings.format('pontosDisponiveis', g.win_points)
        for attr, fill in self.fills:
            width = 256.0 * min(getattr(g, attr), MAX_POINTS) / MAX_POINTS
            fill.size, fill.hidden = (width, 28.4), width <= 0
        for attr, plus in self.pluses:
            plus.texture = 'PlusActive' if getattr(g, attr) < MAX_POINTS and g.win_points >= 1 else 'PlusInactive'

    def step(self, dt):
        self.refresh_pictures()
        super().step(dt)

    def did_move_to_view(self):
        super().did_move_to_view()
        self.doors.open()

    def action_up_power(self, attr):
        g = self.services.globals
        if g.win_points < 1:
            return
        current = self.focused()
        self.services.effects.play('acceptButton.mp3')
        if getattr(g, attr) < MAX_POINTS:
            setattr(g, attr, getattr(g, attr) + 1)
        g.win_points -= 1
        g.save_points(self.services.save)
        # VoiceOver kept the focus where it was. If the button left the order, the focus goes to the element
        # before it, so the next one read is the one that followed the button.
        items = self._visible()
        if current in items:
            self.focus = items.index(current)
        else:
            self.focus = max(0, self.focus - 1)

    def back(self):
        self.doors.close()

        def leave():
            save = self.services.save
            if save.get('ControleCapitulo') == 'yes':
                save.set('ControleCapitulo', 'no')
                save.synchronize()
            if self.return_to is not None:
                self.app.stack.pop()
                self.app.window.set_scene(self.return_to)
            else:
                self.app.pop()
        self.close_doors_then(leave)
