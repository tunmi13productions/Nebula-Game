"""Speech interface (the original's VoiceSynthesizer) and a silent recording version for tests.

The Prism-backed implementation is added in step 4 of the plan.
"""


class Speaker:
    def speak(self, text, rate=0.55, pre_delay=0.0, post_delay=0.0, on_done=None):
        """Speaks text at an AVSpeechUtterance-style rate (0.5 is the iOS default). on_done runs when the line ends."""
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def pause(self):
        raise NotImplementedError

    def resume(self):
        raise NotImplementedError


class NullSpeaker(Speaker):
    """Says nothing. It records lines in `spoken` and keeps completion callbacks until a test calls finish()."""

    def __init__(self):
        self.spoken = []
        self.pending = []

    def speak(self, text, rate=0.55, pre_delay=0.0, post_delay=0.0, on_done=None):
        self.spoken.append((text, rate, pre_delay, post_delay))
        if on_done is not None:
            self.pending.append(on_done)

    def finish(self):
        """Test helper: completes every pending line in order."""
        while self.pending:
            self.pending.pop(0)()

    def stop(self):
        self.pending.clear()

    def pause(self):
        pass

    def resume(self):
        pass
