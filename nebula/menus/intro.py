"""IntroViewController: the headphones notice, then the logo, then the main menu.

With VoiceOver running (always, here) the notice is spoken by the game voice after a 2 second pre-delay, and
the logo starts when that line ends. The logo screen plays thunder.mp3 at volume 0.8 (the file is silent on
the left, so it's heard on the right), fades the logo in over 2 seconds and out over 2, then opens the main
menu. Nothing on these screens is an accessibility element. IntroViewController also has a playSound method
for "Cilada Games.caf", but nothing calls it, so the studio sound never plays.
"""
from ..engine import actions as A
from . import view as V
from .screen import Screen

RATE = 0.55
NOTICE_PRE_DELAY = 2.0
THUNDER_VOLUME = 0.8
LOGO_FADE_IN = 2.0
LOGO_FADE_OUT = 2.0


class IntroScreen(Screen):
    """The pictures (visual only): the notice is three white Futura lines, centred, in frames at 10%, 20% and
    80% of the height (sizes 4%, 2.5% and 2.5% of the height), and phones.png, W / 1.3 wide, in the middle.
    The logo screen is bg_logo stretched over the screen and logo.png, W / 1.3 wide, centred, fading in over
    2 seconds and out over 2."""

    def did_move_to_view(self):
        self.busy = True
        s = self.services.strings
        W, H = V.W, V.H
        for key, top, size in (('sound_1', 0.1, 0.04), ('sound_2', 0.2, 0.025), ('sound_3', 0.8, 0.025)):
            self.view.add_child(V.text(s.get(key), 0, H * top, W, H * 0.1, H * size))
        pw = W / 1.3
        ph = pw * 640 / 1024
        self.view.add_child(V.image('phones', (W - pw) / 2, (H - ph) / 2, pw, ph))
        text = '%s %s, %s' % (s.get('sound_1'), s.get('sound_2'), s.get('sound_3'))
        self.services.voice.speak_then(text, RATE, NOTICE_PRE_DELAY, 0.0, self.show_logo, prompt=True)

    def show_logo(self):
        W, H = V.W, V.H
        self.view.remove_all_children()
        self.view.add_child(V.image('bg_logo', 0, 0, W, H))
        lw = W / 1.3
        lh = lw * 273 / 824
        logo = V.image('logo', W / 9, (H - lh) / 2, lw, lh, z=1)
        logo.alpha = 0.0
        logo.run(A.sequence([A.fade_alpha_to(1.0, LOGO_FADE_IN), A.fade_alpha_to(0.0, LOGO_FADE_OUT)]))
        self.view.add_child(logo)
        self.services.effects.play('thunder.mp3', THUNDER_VOLUME)
        self.services.scheduler.after(LOGO_FADE_IN + LOGO_FADE_OUT, self.app.open_main_menu)

    def handle_key(self, key):
        return True
