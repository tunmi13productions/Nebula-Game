"""CampaignScene: the chapter and level selector, a SpriteKit scene spoken by the game voice.

It shows one chapter at a time. With VoiceOver running (always, here) its items are, by menuSelection:
0 the chapter label "Chapter %ld: %@" (cap_seletor), 1 Back (cap_sair), 2 to 5 the levels "Level %ld: %@"
(cap_fase). Locked items get ", Locked" (cap_Block) added.

- A level is locked when the chapter is the furthest one reached and the level is past the furthest level.
  Chapters past the furthest one can't be reached (moving there only says "Locked").
- Moving between items (swipeRightDetected and swipeLeftDetected) plays chageButton.mp3 and speaks the item;
  at either end it plays errorButton.mp3. Input is ignored until the line has been spoken (swiping), or for
  0.2 seconds after the error sound.
- Changing chapter (didSwipeLeft and didSwipeRight) plays chageButton.mp3. The new chapter slides in over 1
  second, then its label is spoken and the selection goes back to the label. Moving on from the furthest
  chapter says "Locked". Going back from chapter 1 says "Back" and leaves to the main menu.
- Activating (doubleTapDetected): a locked item plays errorButton.mp3. Otherwise acceptButton.mp3 plays;
  Back plays it again, says "Back" after 0.5 seconds and leaves; a level says its name after 0.5 seconds and
  then starts (presentChapterWithStage, which saves "capitulo" and "fase").
- Swipe up (didSwipeUp) says "Back" and leaves.
- The scene's background map is visual only.

Deviation (DEVIATIONS.md): while an item is being spoken, any navigation key cuts the speech off and acts at
once, and Control silences it, instead of input waiting for the line to finish.
"""

from ..game.map_generator import MapGenerator
from ..render.textures import TextureStore
from . import view as V

RATE = 0.55
SLIDE = 1.0          # the chapter labels move over 1 second
ERROR_HOLD = 0.2
ACTIVATE_PRE_DELAY = 0.5
ITEMS = 6            # the label, Back and four levels
CHAPTERS = 9


class CampaignSelectScene:
    in_menu = True
    is_active = True

    def __init__(self, app, chapter):
        self.app = app
        self.services = app.services
        self.chapter = chapter
        self.selection = 0
        self.swiping = False
        self.reading = False      # an item is being spoken and input waits for it (interruptible here)
        self.pending = None       # the timer of a chapter slide or an error hold still locking input
        self.swiping_from_slide = False
        self.leaving = False      # Back is under way: further keys are ignored so they can't restart it
        self.started = False
        self._build_view()

    # the look (visual only)

    def _build_view(self):
        """initWithSize:onChapter:'s look: the free mode map behind everything, two HologramaCampanha panels
        (320 by 284, centred at y 300 and 116.4), the portaLisaCampanha frame over the screen (z 9) and the
        back picture at the top. The chapter title is spelled in letter pictures (scale 0.22) at y 443.75 and
        the four level names (scale 0.16, 156.8 points wide) in a 2 by 2 grid at (80, 284), (240, 284),
        (80, 100.3) and (240, 100.3). Locked items use the grey letters."""
        self.view = V.new_view()
        self.map = MapGenerator(self.view, self.services)
        self.map.free_mode()
        s = self.services.strings
        for y in (300.076, 116.423):
            panel = V.image('HologramaCampanha', 0, V.H - y - 142, 320, 284, z=8)
            self.view.add_child(panel)
        self.view.add_child(V.image('portaLisaCampanha', 0, 0, V.W, V.H, z=9))
        back = V.image(V.localized('back', s), 80, V.H - 545.143 - 22.857, 160, 45.7143, z=17)
        self.view.add_child(back)
        self.chapter_nodes = []
        self._show_chapter()

    def _show_chapter(self):
        for n in self.chapter_nodes:
            n.remove_from_parent()
        textures = _textures()
        title = V.glyph_text(self.strings().get('cap%d_title' % self.chapter), 0.22, 266.667,
                             not self.chapter_locked(), textures)
        title.position, title.z = (160.0, 443.75), 20
        nodes = [title]
        for level, pos in zip((1, 2, 3, 4), ((80, 284), (240, 284), (80, 100.347), (240, 100.347))):
            n = V.glyph_text(self.level_name(level), 0.16, 156.8, not self.level_locked(level), textures)
            n.position, n.z = pos, 16
            nodes.append(n)
        for n in nodes:
            self.view.add_child(n)
        self.chapter_nodes = nodes

    def step(self, dt):
        self.view.step(dt)

    def draw(self, surface, renderer):
        renderer.draw_scene(self.view, surface)

    # what the window calls

    def did_move_to_view(self):
        """Coming back from the Hangar shows this scene again; the original scene was never re-entered."""
        if self.started:
            self._build_view()      # its map was stopped when the Hangar opened
            return
        self.started = True
        self.swiping = False
        self.selection = 0
        self.services.voice.speak(self.chapter_label(), RATE)

    def stop_audio(self):
        self.map.stop()

    def player_shoot(self):
        pass

    def swipe_up(self):
        pass

    def speak_life(self):
        pass

    def handle_key(self, key):
        if self.leaving:
            return True
        if key == 'control':
            self.services.voice.stop()
            self._interrupt()
            return True
        self._interrupt()
        if key == 'right':
            self.did_swipe_left()
        elif key == 'left':
            self.did_swipe_right()
        elif key == 'escape':
            self.did_swipe_up()
        return True

    def menu_next(self):
        if self.leaving:
            return
        self._interrupt()
        self.swipe_right_detected()

    def menu_previous(self):
        if self.leaving:
            return
        self._interrupt()
        self.swipe_left_detected()

    def menu_first(self):
        """Home: the chapter name (a port addition, DEVIATIONS.md, "Home and End in menus")."""
        self._jump(0)

    def menu_last(self):
        """End: the last level."""
        self._jump(ITEMS - 1)

    def _jump(self, selection):
        if self.leaving:
            return
        self._interrupt()
        if self.swiping:
            return
        self.swiping = True
        if selection == self.selection:
            self._error()
            return
        self.services.effects.play('chageButton.mp3')
        self.selection = selection
        self._speak_item()

    def menu_activate(self):
        if self.leaving:
            return
        self._interrupt()
        self.double_tap_detected()

    def _interrupt(self):
        """Cuts off what's still locking input, so the next key acts at once (a deviation): an item being read
        is silenced, a chapter slide finishes now (quietly, since the key that interrupts it speaks), and the
        short hold after the end-of-list sound ends."""
        if self.reading:
            self.services.voice.stop()
            self.reading = False
            self.swiping = False
        timer, self.pending = self.pending, None
        if timer is not None and timer.valid:
            timer.invalidate()
            timer.fn()
            if self.swiping_from_slide:
                self.services.voice.stop()
        self.swiping_from_slide = False

    # text

    def strings(self):
        return self.services.strings

    def chapter_label(self):
        s = self.strings()
        return s.format('cap_seletor', self.chapter, s.get('cap%d_title' % self.chapter))

    def level_name(self, level):
        return self.strings().get('cap%d_lvl%d' % (self.chapter, level))

    def level_label(self, level):
        return self.strings().format('cap_fase', level, self.level_name(level))

    def locked(self, text):
        return '%s, %s' % (text, self.strings().get('cap_Block'))

    def chapter_locked(self):
        return self.services.globals.last_chapter < self.chapter

    def level_locked(self, level):
        g = self.services.globals
        return self.chapter_locked() or (g.last_chapter == self.chapter and level > g.last_level)

    def item_text(self, selection):
        if selection == 0:
            label = self.chapter_label()
            return self.locked(label) if self.chapter_locked() else label
        if selection == 1:
            return self.strings().get('cap_sair')
        level = selection - 1
        label = self.level_label(level)
        return self.locked(label) if self.level_locked(level) else label

    # moving between items

    def _done(self):
        self.swiping = False
        self.reading = False

    def _error(self):
        self.services.effects.play('errorButton.mp3')
        self.pending = self.services.scheduler.after(ERROR_HOLD, self._done)

    def _speak_item(self):
        self.reading = True
        self.services.voice.speak_then(self.item_text(self.selection), RATE, 0.0, 0.0, self._done)

    def swipe_right_detected(self):
        if self.swiping:
            return
        self.swiping = True
        if self.selection + 1 >= ITEMS:
            self._error()
            return
        self.services.effects.play('chageButton.mp3')
        self.selection += 1
        self._speak_item()

    def swipe_left_detected(self):
        if self.swiping:
            return
        self.swiping = True
        if self.selection < 1:
            self._error()
            return
        self.services.effects.play('chageButton.mp3')
        self.selection -= 1
        self._speak_item()

    # changing chapter

    def _slid_in(self):
        self._show_chapter()
        self.swiping = False
        self.selection = 0
        self.services.voice.speak(self.chapter_label(), RATE)

    def did_swipe_left(self):
        if self.swiping:
            return
        self.swiping = True
        self.services.effects.play('chageButton.mp3')
        self.load_next_chapter()

    def did_swipe_right(self):
        if self.swiping:
            return
        self.swiping = True
        self.services.effects.play('chageButton.mp3')
        self.load_previous_chapter()

    def load_next_chapter(self):
        last = self.services.globals.last_chapter
        if self.chapter < CHAPTERS and self.chapter < last:
            self.chapter += 1
            self.pending = self.services.scheduler.after(SLIDE, self._slid_in)
            self.swiping_from_slide = True
        if self.chapter >= last and self.chapter + 1 <= CHAPTERS:
            self.services.voice.speak(self.strings().get('cap_Block'), RATE)
        self.swiping = False

    def load_previous_chapter(self):
        if self.chapter < 2:
            self._leave(0.0)
            self.swiping = False
            return
        self.chapter -= 1
        self.pending = self.services.scheduler.after(SLIDE, self._slid_in)
        self.swiping_from_slide = True

    # activating

    def did_swipe_up(self):
        if self.swiping:
            return
        self._leave(0.0)

    def _leave(self, pre_delay):
        """Says "Back", then leaves (backMenuController). Once started, keys no longer restart it."""
        self.leaving = True
        self.services.voice.speak_then(self.strings().get('cap_sair'), RATE, pre_delay, 0.0, self.app.back_to_screen)

    def double_tap_detected(self):
        if self.swiping:
            return
        fx = self.services.effects
        if self.chapter_locked() or (self.selection >= 2 and self.level_locked(self.selection - 1)):
            fx.play('errorButton.mp3')
            return
        fx.play('acceptButton.mp3')
        voice = self.services.voice
        if self.selection == 1:
            fx.play('acceptButton.mp3')
            self._leave(ACTIVATE_PRE_DELAY)
        elif self.selection >= 2:
            level = self.selection - 1
            self.swiping = True
            voice.speak_then(self.level_name(level), RATE, ACTIVATE_PRE_DELAY, 0.0,
                             lambda: self.present_chapter_with_stage(level))

    def present_chapter_with_stage(self, stage):
        save = self.services.save
        save.set_integer('capitulo', self.chapter)
        save.set_integer('fase', stage)
        save.synchronize()
        self.app.start_chapter(self.chapter, stage)


_TEXTURES = None


def _textures():
    """The letter pictures' sizes, for laying out the text (shared with the renderer's store)."""
    global _TEXTURES
    if _TEXTURES is None:
        _TEXTURES = TextureStore()
    return _TEXTURES
