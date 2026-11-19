"""MainMenuViewController.

Button titles come from the storyboard (data/strings/storyboard_*.json). Buttons, in screen order (the
order VoiceOver read them): Campaign (tag 1), Free Mode (tag 2), Tutorial (tag 3), Multiplayer (tag 4),
Hangar (tag 5), About (tag 6). Multiplayer plays versus mode over the port's relay server instead of Game
Center (DEVIATIONS.md). Systems (the settings) and Exit follow About as spoken-only items, port additions with
no picture on the doors.

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
- Gameplay stops the music: free mode on entry, the campaign when a level starts, and a tutorial when it's
  opened from the tutorial selection (its stopMenuMusic notification).
"""
from ..engine import actions as A
from . import view as V
from .settings_screen import LABELS as _SETTINGS_LABELS
from .screen import Element, Screen

RATE = 0.55
EXIT_LABELS = {'en': 'Exit', 'pt': 'Sair'}
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
            Element(s.get('Hnv-oy-p4z.normalTitle'), lambda: self.open(self.app.open_multiplayer)),
            Element(s.get('WWl-xv-diA.normalTitle'), lambda: self.open(self.app.open_hangar)),
            Element(s.get('ZcV-1U-Bf2.normalTitle'), lambda: self.open(self.app.open_about)),
            # Systems, spoken only (DEVIATIONS.md, "Settings screen")
            Element(settings_label(s), lambda: self.open(self.app.open_settings)),
            # Exit, a port addition with no picture (DEVIATIONS.md, "Exit on the main menu")
            Element(EXIT_LABELS.get(s.language, EXIT_LABELS['en']), self.exit_game),
        ]

    def appeared(self):
        save = self.services.save
        save.set('ControleCapitulo', 'no')
        save.synchronize()
        self.app.play_menu_music()
        if not self.loaded:
            self.loaded = True
            self.build_pictures()
            self.services.scheduler.after(DOORS_DELAY, lambda: self.services.effects.play('closing_doors.caf'))
            self.services.scheduler.after(MUSIC_DELAY, self.toca_som)

    def build_pictures(self):
        """viewDidLoad's look (visual only): the nebula (nebulaMenu1) under a white flash that fades over 1
        second; the doors wait off screen, fade in over the next second, then slide shut over 0.4 seconds. The
        menu is drawn on the doors (leftDoor_en_4 and rightDoor_en_4 on this 4-inch screen); the buttons are
        invisible areas over them. Closed, the left door spans 0 to W / 2 * 1.124523 and the right door the
        right half."""
        W, H = V.W, V.H
        s = self.services.strings
        self.view.add_child(V.image('nebulaMenu1', 0, 0, W, H))
        flash = V.fill((1.0, 1.0, 1.0, 1.0), 0, 0, W, H, z=5)
        flash.run(A.sequence([A.fade_alpha_to(0.0, 1.0), A.remove_from_parent()]))
        self.view.add_child(flash)
        lw = W / 2 * 1.124523
        left = V.image(V.localized('leftDoor', s, '_4'), -lw, 0, lw, H, z=2)
        right = V.image(V.localized(V.RIGHT_DOOR, s, '_4'), W, 0, W / 2, H, z=1)
        for door, dx in ((left, lw), (right, -W / 2)):
            door.alpha = 0.0
            door.run(A.sequence([A.wait(1.0), A.fade_alpha_to(1.0, 1.0),
                                 A.move_by(dx, 0, 0.4)]))
            self.view.add_child(door)

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
        self.view.add_child(V.loading_view(self.services.strings))
        self.services.effects.play('acceptButton.mp3')

        def loaded():
            self.services.voice.speak(self.services.strings.get('tela_load'), RATE)
            fn()
        self.services.scheduler.after(LOADING_FADE, loaded)

    def exit_game(self):
        """Closes the game. iOS apps had no exit; the home button left them."""
        self.busy = True
        self.services.effects.play('acceptButton.mp3')
        self.app.quit()

    def handle_key(self, key):
        if key == 'f1' and not self.busy:
            self.open(self.app.open_settings)
            return True
        return key in ('escape', 'left', 'right')


class TutorialAlert(Screen):
    """alertViewTutorial: a UIAlertView over the menu. VoiceOver read the title and message and focused the
    first button. "Go to tutorial" (the cancel button, index 0) opens the tutorial selection, which then
    starts the movement tutorial because primeiraVez is still unset. "Cancel" (index 1) sets primeiraVez to
    1. Escape is the alert's escape action, which picks the cancel button, "Go to tutorial"."""

    def __init__(self, menu):
        self.menu = menu
        super().__init__(menu.app)
        self._build_box()

    def _build_box(self):
        """A stand-in for the system alert's look (visual only): a white box in the middle with the title,
        the message and the two buttons in the system blue, over the dimmed menu."""
        W, H = V.W, V.H
        s = self.services.strings
        self.view.background = None
        self.view.add_child(V.fill((0.0, 0.0, 0.0, 0.4), 0, 0, W, H))
        bw, bh = 270.0, 170.0
        x, y = (W - bw) / 2, (H - bh) / 2
        self.view.add_child(V.fill((0.97, 0.97, 0.97, 1.0), x, y, bw, bh, z=1))
        dark, blue = (0.0, 0.0, 0.0), (0.0, 0.48, 1.0)
        self.view.add_child(V.text(s.get('alert_titulo'), x, y + 12, bw, 24, 17, 'HelveticaNeue', dark, z=2))
        message = s.get('alert_mesagem')
        half = message.find(' ', len(message) // 2)
        for i, line in enumerate((message[:half], message[half + 1:]) if half > 0 else (message,)):
            self.view.add_child(V.text(line, x, y + 44 + i * 18, bw, 18, 13, 'HelveticaNeue', dark, z=2))
        self.view.add_child(V.fill((0.8, 0.8, 0.8, 1.0), x, y + bh - 88, bw, 1, z=2))
        self.view.add_child(V.text(s.get('alert_irTutorial'), x, y + bh - 87, bw, 43, 17, 'HelveticaNeue', blue, z=2))
        self.view.add_child(V.fill((0.8, 0.8, 0.8, 1.0), x, y + bh - 44, bw, 1, z=2))
        self.view.add_child(V.text(s.get('alert_cancelar'), x, y + bh - 43, bw, 43, 17, 'HelveticaNeue', blue, z=2))

    def step(self, dt):
        self.menu.view.step(dt)
        self.view.step(dt)

    def draw(self, surface, renderer):
        renderer.draw_scene(self.menu.view, surface)
        renderer.draw_scene(self.view, surface, clear=False)

    def build(self):
        s = self.services.strings
        self.elements = [Element(s.get('alert_titulo'), button=False), Element(s.get('alert_mesagem'), button=False),
                         Element(s.get('alert_irTutorial'), self.go), Element(s.get('alert_cancelar'), self.cancel)]

    def did_move_to_view(self):
        self.busy = False
        self.focus = 2
        s = self.services.strings
        self.say('%s, %s, %s' % (s.get('alert_titulo'), s.get('alert_mesagem'), self.spoken(self.elements[2])))

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


def settings_label(strings):
    return _SETTINGS_LABELS.get(strings.language, _SETTINGS_LABELS['en'])['title']
