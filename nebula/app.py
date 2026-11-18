"""The navigation between screens, following the original's view controllers.

The original pushed view controllers onto a navigation controller: the intro opened the main menu, and the
main menu pushed the tutorial selection, the Hangar, the About screen, or the game view controller (which
shows the campaign selector, free mode or a tutorial). backMenuController popped the game view controller,
returning to whichever screen opened it. Here self.stack holds the UIKit-style screens; a game scene is
shown on top of the last one and leaving it shows that screen again.
"""
from .game.free_mode import FreeModeScene
from .game.tutorial import TutorialScene
from .menus.intro import IntroScreen
from .menus.main_menu import MainMenuScreen
from .menus.tutorial_selection import TutorialSelectionScreen


class App:
    def __init__(self, window, services, tilt):
        self.window, self.services, self.tilt = window, services, tilt
        self.stack = []

    def start(self):
        self.window.set_scene(IntroScreen(self))

    # UIKit screens

    def open_main_menu(self):
        self.stack = [MainMenuScreen(self)]
        self.window.set_scene(self.stack[-1])

    def push(self, screen):
        self.stack.append(screen)
        self.window.set_scene(screen)

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop()
        self.window.set_scene(self.stack[-1])

    def back_to_screen(self):
        """backMenuController: the game view controller is popped."""
        self.window.set_scene(self.stack[-1])

    # what the main menu opens (filled in as each screen is ported)

    def open_campaign(self):
        pass

    def open_free_mode(self):
        self.window.set_scene(FreeModeScene(self.services, self.tilt, on_menu=self.back_to_screen,
                                            on_new_game=self.open_free_mode))

    def open_tutorial_selection(self):
        self.push(TutorialSelectionScreen(self))

    def start_tutorial(self, n):
        self.window.set_scene(TutorialScene(self.services, self.tilt, n, on_select=self.back_to_screen,
                                            on_next=lambda: self.next_tutorial(n)))

    def next_tutorial(self, n):
        """proximoTutorial: the next section, remembered under the "tutorial" key."""
        save = self.services.save
        save.set('tutorial', '%d' % (n + 1))
        save.synchronize()
        self.start_tutorial(n + 1)

    def open_hangar(self):
        pass

    def open_about(self):
        pass
