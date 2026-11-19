"""The navigation between screens, following the original's view controllers.

The original pushed view controllers onto a navigation controller: the intro opened the main menu, and the
main menu pushed the tutorial selection, the Hangar, the About screen, or the game view controller (which
shows the campaign selector, free mode or a tutorial). backMenuController popped the game view controller,
returning to whichever screen opened it. Here self.stack holds the UIKit-style screens; a game scene is
shown on top of the last one and leaving it shows that screen again.
"""
import webbrowser

from .game.chapters import CHAPTERS
from .game.free_mode import FreeModeScene
from .audio.players import LoopingMusic
from .game.tutorial import TutorialScene
from .menus.about import AboutScreen
from .menus.campaign import CampaignSelectScene
from .menus.hangar import HangarScreen
from .menus.intro import IntroScreen
from .menus.main_menu import MainMenuScreen
from .menus.multiplayer import MultiplayerScreen, NameChoiceScreen
from .game.versus import VersusScene
from .net.relay_client import DEFAULT_SERVER, RelayClient
from .settings import save_settings
from .menus.settings_screen import SettingsScreen
from .menus.tutorial_selection import TutorialSelectionScreen


class App:
    def __init__(self, window, services, tilt, open_url=webbrowser.open, settings=None, settings_path=None):
        """open_url opens a web page or a mailto: link with the system's default program. settings: the
        settings file's contents, which the Settings screen changes and saves to settings_path."""
        self.window, self.services, self.tilt = window, services, tilt
        self.settings = settings if settings is not None else {}
        self.settings_path = settings_path
        self.open_url = open_url
        self.stack = []
        self.menu_music = None   # Global.mainMenuMusic, created by the main menu's opening animation

    def start(self):
        self.window.set_scene(IntroScreen(self))

    # the menu music

    def create_menu_music(self):
        if self.menu_music is None:
            path = self.services.sound_path('menuSound', 'mp3')
            if path is not None:
                self.menu_music = LoopingMusic(self.services.audio, path)

    def play_menu_music(self):
        if self.menu_music is not None:
            self.menu_music.play()

    def stop_menu_music(self):
        if self.menu_music is not None:
            self.menu_music.stop()

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

    def open_campaign(self, chapter=None):
        """The campaign selector, on the furthest chapter reached unless a chapter is given."""
        chapter = chapter or self.services.globals.last_chapter
        self.campaign = CampaignSelectScene(self, chapter)
        self.window.set_scene(self.campaign)

    def start_chapter(self, chapter, stage):
        self.stop_menu_music()
        self.window.set_scene(CHAPTERS[chapter](
            self.services, self.tilt, stage, on_select=self.back_to_campaign,
            on_next=lambda: self.next_mission(chapter, stage),
            on_restart=lambda: self.start_chapter(chapter, stage)))

    def next_mission(self, chapter, stage):
        """proximaMissao: the next level of the same chapter, remembered under "fase"."""
        save = self.services.save
        save.set_integer('fase', stage + 1)
        save.synchronize()
        self.start_chapter(chapter, stage + 1)

    def back_to_campaign(self):
        """backMenuCampaign: back to the selector on the chapter just played. When a chapter was newly
        completed (ControleCapitulo is "yes") it opens on the furthest chapter instead, awards 2 upgrade
        points (2 more when chapter 5 has just been reached) and opens the Hangar on top."""
        g, save = self.services.globals, self.services.save
        if save.get('ControleCapitulo') == 'yes':
            self.open_campaign(g.last_chapter)
            g.win_points += 2
            if g.last_chapter == 5:
                g.win_points += 2
            g.save_points(save)
            self.open_hangar(return_to=self.campaign)
        else:
            self.open_campaign(save.integer('capitulo') or g.last_chapter)

    def open_free_mode(self):
        self.stop_menu_music()
        self.window.set_scene(FreeModeScene(self.services, self.tilt, on_menu=self.back_to_screen,
                                            on_new_game=self.open_free_mode))

    def open_tutorial_selection(self):
        self.push(TutorialSelectionScreen(self))

    def start_tutorial(self, n):
        """TutorialSelectionViewController prepareForSegue:sender: posts stopMenuMusic before the tutorial
        opens. The next section keeps it stopped."""
        self.stop_menu_music()
        self.window.set_scene(TutorialScene(self.services, self.tilt, n, on_select=self.tutorial_selected_back,
                                            on_next=lambda: self.next_tutorial(n)))

    def tutorial_selected_back(self):
        """Select tutorial posts playMenuMusic, then backMenuController."""
        self.play_menu_music()
        self.back_to_screen()

    def next_tutorial(self, n):
        """proximoTutorial: the next section, remembered under the "tutorial" key."""
        save = self.services.save
        save.set('tutorial', '%d' % (n + 1))
        save.synchronize()
        self.start_tutorial(n + 1)

    def open_hangar(self, return_to=None):
        """The Hangar, from the main menu, or on top of the campaign selector (return_to) after a newly
        completed chapter."""
        self.push(HangarScreen(self, return_to))

    def open_about(self):
        self.push(AboutScreen(self))

    def quit(self):
        """Closes the window, which ends the game."""
        quit_window = getattr(self.window, 'quit', None)
        if quit_window is not None:
            quit_window()

    # multiplayer (a port addition in place of Game Center)

    def player_name(self):
        return self.settings.get('player_name') or ''

    def set_player_name(self, name):
        self.settings['player_name'] = name
        try:
            save_settings(self.settings, self.settings_path)
        except OSError:
            pass

    def open_multiplayer(self):
        """The Multiplayer button: the name is chosen the first time, then quick match or invites."""
        if self.player_name():
            self.push(MultiplayerScreen(self))
        else:
            self.push(NameChoiceScreen(self, lambda: self.push(MultiplayerScreen(self))))

    def start_versus(self, mode, code=None):
        """Connects to the relay and shows VersusScene's lobby while it pairs the players: mode 'quick',
        'host' (an invite code is read out) or 'join' (with the friend's code). The scene then plays the
        match; leaving it, or a failure, comes back to the multiplayer screen."""
        from .menus.multiplayer import spelled, words
        w = words(self.services)
        say = self.services.screen_reader.say
        net = self.make_relay_client(self.settings.get('server') or DEFAULT_SERVER)
        self.stop_menu_music()
        scene = VersusScene(self.services, self.tilt, net, self.back_to_screen)

        def welcome(name):
            if mode == 'quick':
                net.quick()
            elif mode == 'host':
                net.host()
            else:
                net.join(code)

        def failed(reason):
            scene.back_to_menu()
            say(w.get(reason, w['disconnected']))     # after the menu's own line, so it isn't cut off

        net.on_welcome = welcome
        net.on_waiting = lambda: say(w['waiting'])
        net.on_code = lambda c: say(w['your_code'] % spelled(c))
        net.on_error = failed
        self.window.set_scene(scene)
        say(w['connecting'])
        net.connect(self.player_name())

    def make_relay_client(self, address):
        return RelayClient(address)

    def open_settings(self):
        """The Settings screen, a port addition."""
        self.push(SettingsScreen(self, self.settings, self.settings_path))
