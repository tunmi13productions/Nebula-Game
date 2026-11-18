r"""The optional settings file, %APPDATA%\Nebula\settings.json. It's also where saved progress will live.

Recognised keys so far: "language", either "en" or "pt", overriding the Windows display language.
A missing or unreadable file means no overrides.
"""
import json
import os


def user_dir():
    base = os.environ.get('APPDATA') or os.path.expanduser('~')
    return os.path.join(base, 'Nebula')


def load_settings(path=None):
    path = path or os.path.join(user_dir(), 'settings.json')
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}
