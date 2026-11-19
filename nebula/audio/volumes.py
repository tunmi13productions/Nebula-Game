"""The player's volume and speech rate settings (a deviation, see DEVIATIONS.md, "Settings screen").

One shared object, read wherever a sound's volume is set: sounds (Aureal's positional sounds and the
effects), music (the menu music) and speech (the game voice and the narration clips), each from 0 to 1, and
the game voice's rate as a multiple of the original rates. All 1.0 by default, which is the original.
"""


class Volumes:
    def __init__(self):
        self.sounds = 1.0
        self.music = 1.0
        self.speech = 1.0
        self.speech_rate = 1.0


VOLUMES = Volumes()
