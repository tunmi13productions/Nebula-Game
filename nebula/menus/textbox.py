"""A single-line text box for typing a name or an invite code (a port addition, DEVIATIONS.md, "Multiplayer
through a relay server").

The editing follows Haptix's TextInput (MIT License, copyright 2025 tunmi13productions), single-line only:
the caret sits between characters; moving reads the character at the caret, the way Windows edit fields do;
Shift with a movement selects, reading what was crossed and whether it was selected or unselected.

Keys: Left and Right by character, Control with them by word, Home and End, Shift with any of them to select;
Backspace and Delete, by word with Control; Control with A, C, X, V and Z. Typed characters arrive as text
events and are echoed. The edges play the game's error sound. Enter and Escape are left to the screen that
holds the box.
"""
import pygame

from .symbols import char_name

WORDS = {
    'en': {'blank': 'blank', 'selected': 'selected', 'unselected': 'unselected', 'deleted': 'deleted',
           'max': 'Maximum length reached', 'nothing_to_undo': 'Nothing to undo', 'undo': 'Undo',
           'no_selection': 'No selection', 'copied': 'copied', 'cut': 'cut', 'pasted': 'Pasted',
           'empty_clipboard': 'Clipboard is empty', 'edit': 'edit', 'characters': 'characters'},
    'pt': {'blank': 'em branco', 'selected': 'selecionado', 'unselected': 'não selecionado',
           'deleted': 'apagado', 'max': 'Tamanho máximo atingido', 'nothing_to_undo': 'Nada para desfazer',
           'undo': 'Desfazer', 'no_selection': 'Nenhuma seleção', 'copied': 'copiado',
           'cut': 'recortado', 'pasted': 'Colado', 'empty_clipboard': 'Área de transferência vazia',
           'edit': 'edição', 'characters': 'caracteres'},
}


def _clipboard_get():
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        data = pygame.scrap.get(pygame.SCRAP_TEXT) or b''
        return data.decode('utf-8', 'ignore').replace('\x00', '') if isinstance(data, bytes) else str(data)
    except Exception:
        return ''


def _clipboard_set(text):
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        pygame.scrap.put(pygame.SCRAP_TEXT, text.encode('utf-8'))
    except Exception:
        pass


class TextBox:
    def __init__(self, label, say, edge=None, language='en', max_length=0, allowed=None, value=''):
        """say(text, interrupt=True) speaks through the screen reader; edge() plays the edge sound. allowed,
        if given, is the set of characters that may be typed (digits for a code)."""
        self.label, self.say, self.edge = label, say, edge or (lambda: None)
        self.words = WORDS.get(language, WORDS['en'])
        self.max_length, self.allowed = max_length, allowed
        self.text = value
        self.caret = len(value)
        self.anchor = None
        self._undo = []
        self._typing = False

    # reading

    def describe(self):
        """The box as it is first read: label, kind and contents."""
        return '%s, %s, %s' % (self.label, self.words['edit'], self.text or self.words['blank'])

    @property
    def selection(self):
        if self.anchor is None or self.anchor == self.caret:
            return None
        return min(self.anchor, self.caret), max(self.anchor, self.caret)

    def _span(self, span):
        if not span:
            return self.words['blank']
        return char_name(span) if len(span) == 1 else span

    def _at(self, pos):
        return char_name(self.text[pos]) if pos < len(self.text) else self.words['blank']

    def _word_left(self, pos):
        while pos > 0 and self.text[pos - 1].isspace():
            pos -= 1
        while pos > 0 and not self.text[pos - 1].isspace():
            pos -= 1
        return pos

    def _word_right(self, pos):
        while pos < len(self.text) and not self.text[pos].isspace():
            pos += 1
        while pos < len(self.text) and self.text[pos].isspace():
            pos += 1
        return pos

    # moving

    def _go(self, new, extend, by_word=False):
        old, sel = self.caret, self.selection
        if extend:
            if self.anchor is None:
                self.anchor = old
            self.caret = new
            if new == old:
                self.edge()
                self.say(self._at(new))
                return
            lo, hi = min(old, new), max(old, new)
            now = self.selection
            chosen = bool(now) and now[0] <= lo and hi <= now[1]
            self.say('%s %s' % (self._span(self.text[lo:hi]), self.words['selected' if chosen else 'unselected']))
            return
        self.anchor = None
        if new == old and not sel:
            self.edge()
        self.caret = new
        if by_word and new < len(self.text):
            end = new
            while end < len(self.text) and not self.text[end].isspace():
                end += 1
            self.say(self._span(self.text[new:end]))
        else:
            self.say(self._at(new))

    def move(self, direction, by_word=False, extend=False):
        sel = self.selection
        if sel and not extend and not by_word:
            self._go(sel[0] if direction < 0 else sel[1], False)
            return
        if by_word:
            new = self._word_left(self.caret) if direction < 0 else self._word_right(self.caret)
        else:
            new = max(0, min(len(self.text), self.caret + direction))
        self._go(new, extend, by_word)

    def edge_jump(self, end, extend=False):
        self._go(len(self.text) if end else 0, extend)

    # editing

    def _save(self, typing=False):
        if typing and self._typing:
            return
        self._undo.append((self.text, self.caret, self.anchor))
        del self._undo[:-100]
        self._typing = typing

    def _replace(self, start, end, new):
        self.text = self.text[:start] + new + self.text[end:]
        self.caret, self.anchor = start + len(new), None

    def insert(self, new, typing=False):
        new = new.replace('\r', ' ').replace('\n', ' ')
        if self.allowed is not None:
            new = ''.join(c for c in new if c in self.allowed)
            if not new:
                self.edge()
                return False
        sel = self.selection or (self.caret, self.caret)
        if self.max_length:
            room = self.max_length - len(self.text) + (sel[1] - sel[0])
            if room <= 0:
                self.edge()
                self.say(self.words['max'])
                return False
            new = new[:room]
        self._save(typing)
        self._replace(sel[0], sel[1], new)
        return True

    def type_text(self, typed):
        if self.insert(typed, typing=True):
            self.say(char_name(typed) if len(typed) == 1 else typed, False)

    def delete(self, direction, by_word=False):
        sel = self.selection
        if sel:
            removed = self.text[sel[0]:sel[1]]
            self._save()
            self._replace(sel[0], sel[1], '')
            self.say('%s %s' % (self._span(removed), self.words['deleted']))
            return
        if direction < 0:
            if self.caret == 0:
                self.edge()
                self.say(self.words['blank'])
                return
            start = self._word_left(self.caret) if by_word else self.caret - 1
            removed = self.text[start:self.caret]
            self._save()
            self._replace(start, self.caret, '')
            self.say(self._span(removed))
        else:
            if self.caret >= len(self.text):
                self.edge()
                self.say(self.words['blank'])
                return
            end = self._word_right(self.caret) if by_word else self.caret + 1
            self._save()
            self._replace(self.caret, min(end, len(self.text)), '')
            self.say(self._at(self.caret))

    def undo(self):
        if not self._undo:
            self.say(self.words['nothing_to_undo'])
            return
        self.text, self.caret, self.anchor = self._undo.pop()
        self._typing = False
        self.say(self.words['undo'])

    def select_all(self):
        if not self.text:
            self.say(self.words['blank'])
            return
        self.anchor, self.caret = 0, len(self.text)
        self.say('%s %s' % (self._span(self.text), self.words['selected']))

    def copy(self, cut=False):
        sel = self.selection
        if not sel:
            self.say(self.words['no_selection'])
            return
        chosen = self.text[sel[0]:sel[1]]
        _clipboard_set(chosen)
        if cut:
            self._save()
            self._replace(sel[0], sel[1], '')
        self.say('%s %s' % (chosen, self.words['cut' if cut else 'copied']))

    def paste(self, text=None):
        text = _clipboard_get() if text is None else text
        if not text:
            self.say(self.words['empty_clipboard'])
            return
        if self.insert(text):
            self.say(self.words['pasted'])

    # events

    def handle_event(self, event):
        """A pygame TEXTINPUT or KEYDOWN event. Returns True when the box used it."""
        if event.type == pygame.TEXTINPUT:
            if event.text and event.text.isprintable():
                self.type_text(event.text)
            return True
        if event.type != pygame.KEYDOWN:
            return False
        mods = getattr(event, 'mod', 0)
        ctrl, shift = bool(mods & pygame.KMOD_CTRL), bool(mods & pygame.KMOD_SHIFT)
        if mods & pygame.KMOD_ALT:
            return False
        key = event.key
        if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_HOME, pygame.K_END):
            self._typing = False
        if key == pygame.K_LEFT:
            self.move(-1, ctrl, shift)
        elif key == pygame.K_RIGHT:
            self.move(1, ctrl, shift)
        elif key == pygame.K_HOME:
            self.edge_jump(False, shift)
        elif key == pygame.K_END:
            self.edge_jump(True, shift)
        elif key in (pygame.K_UP, pygame.K_DOWN):
            self.say(self.text or self.words['blank'])
        elif key == pygame.K_BACKSPACE:
            self.delete(-1, ctrl)
        elif key == pygame.K_DELETE:
            self.delete(1, ctrl)
        elif ctrl and key == pygame.K_a:
            self.select_all()
        elif ctrl and key == pygame.K_c:
            self.copy()
        elif ctrl and key == pygame.K_x:
            self.copy(cut=True)
        elif ctrl and key == pygame.K_v:
            self.paste()
        elif ctrl and key == pygame.K_z:
            self.undo()
        else:
            # printable keys arrive as TEXTINPUT; Enter, Escape and the rest belong to the screen
            return bool(getattr(event, 'unicode', '')) and event.unicode.isprintable() and not ctrl
        return True
