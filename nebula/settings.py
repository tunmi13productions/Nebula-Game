r"""The optional settings file, %APPDATA%\Nebula\settings.json. It's also where saved progress will live.

Recognised keys so far:
- "language": "en" or "pt", overriding the Windows display language.
- "tilt": the acceleration a held arrow key stands for (default 0.3, provisional until playtested).
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
