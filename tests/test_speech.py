import pytest

from nebula.audio.backend import NullBackend
from nebula.engine.scheduler import Scheduler
from nebula.speech.speech import GameVoice, NullRenderer

FRAME = 1 / 60


def make():
    audio, clock = NullBackend(), Scheduler()
    return GameVoice(audio, clock, NullRenderer(seconds_per_char=0.05)), audio, clock


def run(clock, seconds):
    for _ in range(int(round(seconds / FRAME))):
        clock.update(FRAME)


def line_seconds(text, rate):
    return len(text) * 0.05 * (0.5 / rate)


def test_completion_fires_on_the_first_poll_after_the_line_and_its_delays():
    voice, audio, clock = make()
    done = []
    text = 'Receiving commander message.'
    voice.speak_then(text, 0.55, 1.0, 0.5, lambda: done.append(clock.now))
    run(clock, 6.0)
    end = 1.0 + line_seconds(text, 0.55) + 0.5
    expected = (int(end / 0.3) + 1) * 0.3
    assert done == [pytest.approx(expected, abs=0.02)]


def test_completion_never_comes_before_the_third_poll():
    voice, audio, clock = make()
    done = []
    voice.speak_then('Hi', 0.55, 0.0, 0.0, lambda: done.append(clock.now))
    run(clock, 2.0)
    assert done == [pytest.approx(0.9, abs=0.02)]


def test_plain_speak_interrupts_and_queued_lines_wait():
    voice, audio, clock = make()
    voice.speak_queued('first line', 0.55)
    voice.speak_queued('second line', 0.55)
    voice.speak('Your life is 5', 0.55)
    run(clock, 5.0)
    assert [s[0] for s in voice.spoken] == ['first line', 'Your life is 5']


def test_queued_line_follows_with_its_pre_delay():
    voice, audio, clock = make()
    voice.speak_queued('one', 0.5)
    voice.speak_queued('two', 0.5, pre_delay=0.5)
    run(clock, 0.1)
    assert [s[0] for s in voice.spoken] == ['one']
    run(clock, 0.4)   # 'one' lasts 0.15 s, so 'two' is due at 0.65 s
    assert [s[0] for s in voice.spoken] == ['one']
    run(clock, 0.3)
    assert [s[0] for s in voice.spoken] == ['one', 'two']


def test_stop_cancels_the_completion():
    voice, audio, clock = make()
    done = []
    voice.speak_then('chap1_icarus1', 0.55, 0.0, 0.0, lambda: done.append(1))
    run(clock, 0.2)
    voice.stop()
    run(clock, 5.0)
    assert done == [] and not voice.speaking


def test_pause_holds_the_completion_but_not_the_speech():
    voice, audio, clock = make()
    done = []
    voice.speak_then('short', 0.55, 0.0, 0.0, lambda: done.append(clock.now))
    voice.pause()
    run(clock, 3.0)
    assert done == [] and not voice.speaking
    voice.resume()
    run(clock, 0.4)
    assert len(done) == 1


def test_a_new_completion_line_cancels_the_previous_one():
    voice, audio, clock = make()
    done = []
    voice.speak_then('chap5_icarus1', 0.55, 0.0, 0.0, lambda: done.append('first'))
    run(clock, 0.5)
    voice.speak_then('chap5_icarus2', 0.55, 0.0, 0.0, lambda: done.append('second'))
    run(clock, 6.0)
    assert done == ['second']


def test_plain_speak_does_not_cancel_a_pending_completion():
    voice, audio, clock = make()
    done = []
    voice.speak_then('chap1_icarus1', 0.55, 0.0, 0.0, lambda: done.append(1))
    run(clock, 0.2)
    voice.speak('Score: 10.', 0.6)
    run(clock, 5.0)
    assert done == [1]


def test_prism_renders_to_memory_without_playing():
    pytest.importorskip('prism')
    from nebula.speech.speech import PrismRenderer
    try:
        r = PrismRenderer('en')
    except RuntimeError:
        pytest.skip('no OneCore or SAPI voice on this machine')
    slow, ch, rate = r.render('Receiving commander message. Playing message.', 0.5)
    fast, _, _ = r.render('Receiving commander message. Playing message.', 0.6)
    assert ch == 1 and rate > 0
    assert 1.0 < len(slow) / rate < 6.0
    assert len(fast) < len(slow)


def test_clauses_split_after_punctuation_with_pauses():
    from nebula.speech.speech import split_clauses
    assert split_clauses('PUT YOUR HEADPHONES FOR A BETTER EXPERIENCE., Thunder at the right side.') == [
        ('PUT YOUR HEADPHONES FOR A BETTER EXPERIENCE.,', 0.45), ('Thunder at the right side.', 0.45)]
    assert split_clauses('Score: 120.') == [('Score:', 0.3), ('120.', 0.45)]
    assert split_clauses('Version 1.5 now') == [('Version 1.5 now', 0.0)]


def test_rendering_inserts_silence_between_clauses_only():
    from nebula.speech.speech import render_with_pauses
    calls = []

    def one(text, rate):
        calls.append(text)
        return [1.0] * 10, 1, 100
    pcm, channels, rate = render_with_pauses(one, 'Score: 120.', 0.55)
    assert calls == ['Score:', '120.']
    assert pcm == [1.0] * 10 + [0.0] * 30 + [1.0] * 10
