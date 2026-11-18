"""CutScene: the chapter intros (playIntroCutSceneChapter:completition:), traced with tools/re/trace_cutscene.py.

- Title card (capIntroWithName): Deep_Impact_3.mp3 plays. "Chapter %@" (chapterNNumber, with the chapter in
  Roman numerals) fades in over 1.5 seconds, then the chapter title (capN_title) over 2. At 5 seconds both
  fade out over 2, and at 7 seconds the narration starts. The card was never spoken in the original; here
  it goes to the screen reader when it appears (DEVIATIONS.md, "Chapter title cards are spoken").
- Narration: each part starts when the previous one ends, with no gaps. Most parts are localized mp3 files
  played by an AVAudioPlayer (chapterN_partM, which the strings table maps to the file). Some are spoken by
  the game voice at rate 0.55 with a pre-delay.
- After the last part everything fades out over 3 seconds, then the completion starts the chapter.
- skipCutScene (a tap; Enter or Space here) stops the speech and the narration and runs the completion at
  once. Deep_Impact_3.mp3 is an SKAction sound and keeps playing.
- The pictures that pan and fade over the narration are visual only.
"""
from ..audio.players import Narration

TITLE_TO_NARRATION = 7.0
FINAL_FADE = 3.0
RATE = 0.55

AUDIO, SPEAK = 'audio', 'speak'
PARTS = {
    1: [(AUDIO, 'chapter1_part%d' % i) for i in range(1, 8)],
    2: [(AUDIO, 'chapter2_part1'), (AUDIO, 'chapter2_part2')],
    3: [(AUDIO, 'chapter3_part%d' % i) for i in range(1, 4)],
    4: [(AUDIO, 'chapter4_part%d' % i) for i in range(1, 4)],
    5: [(SPEAK, 'chapter5_part1', 1.5)] + [(AUDIO, 'chapter5_part%d' % i) for i in range(2, 5)],
    6: [(SPEAK, 'chapter6_part1', 0.0), (AUDIO, 'chapter6_part2')],
    7: [(SPEAK, 'chapter7_part1', 0.0), (AUDIO, 'chapter7_part2'), (AUDIO, 'chapter7_part3')],
    8: [(SPEAK, 'chapter8_part1', 0.0), (AUDIO, 'chapter8_part2'), (SPEAK, 'chapter8_part3', 0.25)],
    9: [(AUDIO, 'chapter9_part1'), (AUDIO, 'chapter9_part2')],
}


def roman(n):
    """numberToRoman:"""
    out = ''
    for value, letters in ((10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')):
        while n >= value:
            out += letters
            n -= value
    return out


class CutScene:
    def __init__(self, services, chapter, on_done):
        self.services, self.chapter, self.on_done = services, chapter, on_done
        self.player = Narration(services.audio, services.scheduler)
        self.timer = None
        self.running = False
        self.step = 0

    def start(self):
        s = self.services.strings
        self.running = True
        self.services.effects.play('Deep_Impact_3.mp3')
        self.services.screen_reader.say('%s, %s' % (s.format('chapterNNumber', roman(self.chapter)),
                                                    s.get('cap%d_title' % self.chapter)))
        self.timer = self.services.scheduler.after(TITLE_TO_NARRATION, self._next)

    def _next(self):
        if not self.running:
            return
        parts = PARTS[self.chapter]
        if self.step >= len(parts):
            self.timer = self.services.scheduler.after(FINAL_FADE, self._finish)
            return
        part = parts[self.step]
        self.step += 1
        s = self.services.strings
        if part[0] == AUDIO:
            self.player.play(s.sound_path(part[1]), self._next)
        else:
            self.services.voice.speak_then(s.get(part[1]), RATE, part[2], 0.0, self._next)

    def _finish(self):
        if self.running:
            self.running = False
            self.on_done()

    def skip(self):
        """skipCutScene."""
        if not self.running:
            return
        self.running = False
        self.services.voice.stop()
        self.player.stop()
        if self.timer is not None:
            self.timer.invalidate()
        self.on_done()

    def stop(self):
        """Leaving the scene: silence, no completion."""
        self.running = False
        self.player.stop()
        if self.timer is not None:
            self.timer.invalidate()
