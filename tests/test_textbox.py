"""The text box (after Haptix's TextInput) and the screen that holds it, driven by stand-in key events."""
import pygame

from nebula.menus.text_entry import TextEntryScreen
from nebula.menus.textbox import TextBox
from test_menus import at_main_menu


def key(k, mod=0, unicode=''):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=mod, unicode=unicode)


def text(t):
    return pygame.event.Event(pygame.TEXTINPUT, text=t)


def box(**kw):
    said, edges = [], []
    b = TextBox('Name', lambda t, interrupt=True: said.append(t), lambda: edges.append(1), **kw)
    return b, said, edges


def test_typing_echoes_and_moving_reads_the_character_at_the_caret():
    b, said, edges = box()
    for ch in 'Ace 1':
        b.handle_event(text(ch))
    assert b.text == 'Ace 1' and said[-2:] == ['space', '1']
    b.handle_event(key(pygame.K_HOME))
    assert said[-1] == 'A'
    b.handle_event(key(pygame.K_LEFT))
    assert edges == [1]
    b.handle_event(key(pygame.K_RIGHT, pygame.KMOD_CTRL))
    assert b.caret == 4 and said[-1] == '1'
    b.handle_event(key(pygame.K_END))
    assert said[-1] == 'blank'


def test_selection_deletion_and_undo():
    b, said, edges = box(value='Pilot 260')
    b.handle_event(key(pygame.K_LEFT, pygame.KMOD_SHIFT))
    assert said[-1] == '0 selected'
    b.handle_event(key(pygame.K_LEFT, pygame.KMOD_SHIFT))
    b.handle_event(key(pygame.K_LEFT, pygame.KMOD_SHIFT))
    b.handle_event(key(pygame.K_BACKSPACE))
    assert b.text == 'Pilot ' and said[-1] == '260 deleted'
    b.handle_event(key(pygame.K_z, pygame.KMOD_CTRL))
    assert b.text == 'Pilot 260' and said[-1] == 'Undo'
    b.handle_event(key(pygame.K_BACKSPACE, pygame.KMOD_CTRL))
    assert b.text == 'Pilot '


def test_length_limit_and_allowed_characters():
    b, said, edges = box(max_length=4, allowed=set('0123456789'))
    for ch in '12a345':
        b.handle_event(text(ch))
    assert b.text == '1234' and said[-1] == 'Maximum length reached'


def test_the_screen_reads_the_prompt_confirms_with_enter_and_cancels_with_escape():
    app, window, services = at_main_menu()
    done, cancelled = [], []
    screen = TextEntryScreen(app, 'Choose a pilot name.', 'Name', done.append, lambda: cancelled.append(1))
    app.push(screen)
    assert services.screen_reader.said[-1] == 'Choose a pilot name. Name, edit, blank'
    screen.menu_activate()
    assert done == [] and services.effects.played[-1] == 'errorButton.mp3'
    for ch in ' Nebula  482 ':
        screen.handle_text_event(text(ch))
    screen.menu_activate()
    assert done == ['Nebula 482']
    other = TextEntryScreen(app, 'Code', 'Code', done.append, lambda: cancelled.append(1))
    app.push(other)
    other.handle_key('escape')
    assert cancelled == [1]
