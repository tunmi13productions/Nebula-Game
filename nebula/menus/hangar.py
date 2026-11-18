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
