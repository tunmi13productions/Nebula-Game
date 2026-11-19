"""Localized text and language selection.

Lookups behave like NSLocalizedString with an empty default: a key missing from the language's table comes
back as the key itself. English gets the fixes listed in docs/DEVIATIONS.md (data/strings/en_fixes.json).
Formats use the original Objective-C placeholders (%ld, %d, %@), converted on the fly.
"""
import ctypes
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'strings')
SOUNDS = os.path.join(ROOT, 'sounds')
LANGUAGES = ('en', 'pt')
_PORTUGUESE_PRIMARY_LANGID = 0x16

_OBJC_FORMAT = re.compile(r'%(l?[di]|li|@|%)')


def _load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def windows_language():
    """'pt' if the system's display language is any Portuguese, otherwise 'en', like iOS picked pt.lproj or Base.
    On macOS and Linux, where there is no Windows display language, the locale settings decide."""
    try:
        langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    except (AttributeError, OSError):
        return _locale_language()
    return 'pt' if (langid & 0x3FF) == _PORTUGUESE_PRIMARY_LANGID else 'en'


def _locale_language():
    import locale
    for name in ('LC_ALL', 'LC_MESSAGES', 'LANG', 'LANGUAGE'):
        value = os.environ.get(name, '')
        if value:
            return 'pt' if value.lower().startswith('pt') else 'en'
    try:
        code = locale.getlocale()[0] or ''
    except (ValueError, TypeError):
        code = ''
    return 'pt' if code.lower().startswith('pt') else 'en'


def choose_language(settings):
    """The settings file's "language" ('en' or 'pt') wins. Otherwise the Windows display language decides."""
    lang = (settings or {}).get('language')
    return lang if lang in LANGUAGES else windows_language()


def objc_format(fmt, *args):
    """Applies Objective-C format placeholders (%ld, %d, %li, %@, %%) to args, in order."""
    values = iter(args)

    def sub(m):
        spec = m.group(1)
        if spec == '%':
            return '%'
        v = next(values)
        return str(int(v)) if spec != '@' else str(v)
    return _OBJC_FORMAT.sub(sub, fmt)


class Strings:
    def __init__(self, language):
        if language not in LANGUAGES:
            raise ValueError(language)
        self.language = language
        self.table = _load(language + '.json')
        self.table.update(_load('storyboard_%s.json' % language))   # main menu button titles
        if language == 'en':
            self.table.update(_load('en_fixes.json'))

    def get(self, key):
        return self.table.get(key, key)

    def format(self, key, *args):
        return objc_format(self.get(key), *args)

    def sound_path(self, key):
        """For narration keys (tut_1.0, chapter1_part1 ...) the table holds the localized file name."""
        return os.path.join(SOUNDS, self.get(key))
