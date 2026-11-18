"""IntroViewController: the headphones notice, then the logo, then the main menu.

With VoiceOver running (always, here) the notice is spoken by the game voice after a 2 second pre-delay, and
the logo starts when that line ends. The logo screen plays thunder.mp3 at volume 0.8 (the file is silent on
the left, so it's heard on the right), fades the logo in over 2 seconds and out over 2, then opens the main
menu. Nothing on these screens is an accessibility element. IntroViewController also has a playSound method
for "Cilada Games.caf", but nothing calls it, so the studio sound never plays.
"""
from .screen import Screen

RATE = 0.55
NOTICE_PRE_DELAY = 2.0
THUNDER_VOLUME = 0.8
LOGO_FADE_IN = 2.0
LOGO_FADE_OUT = 2.0


class IntroScreen(Screen):
    def did_move_to_view(self):
        self.busy = True
        s = self.services.strings
        text = '%s %s, %s' % (s.get('sound_1'), s.get('sound_2'), s.get('sound_3'))
        self.services.voice.speak_then(text, RATE, NOTICE_PRE_DELAY, 0.0, self.show_logo)

    def show_logo(self):
        self.services.effects.play('thunder.mp3', THUNDER_VOLUME)
        self.services.scheduler.after(LOGO_FADE_IN + LOGO_FADE_OUT, self.app.open_main_menu)

    def handle_key(self, key):
        return True
