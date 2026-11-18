r"""Saved progress, the port of the original's NSUserDefaults, in %APPDATA%\Nebula\save.json.

Keys keep the original names (bestScore, Life_Points, last_Chapter and so on), so docs/MENUS.md applies.
"""
import json
import os

from .settings import user_dir


class SaveData:
    def __init__(self, path=None):
        self.path = path
        self.data = {}
        if path is not None:
            try:
                with open(path, encoding='utf-8') as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self.data = loaded
            except (OSError, ValueError):
                pass

    @classmethod
    def default(cls):
        return cls(os.path.join(user_dir(), 'save.json'))

    @classmethod
    def in_memory(cls):
        return cls(None)

    def integer(self, key):
        """integerForKey: 0 when missing."""
        value = self.data.get(key, 0)
        return value if isinstance(value, int) else 0

    def set_integer(self, key, value):
        self.data[key] = int(value)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def synchronize(self):
        """Writes the file atomically. In-memory saves do nothing."""
        if self.path is None:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=1, sort_keys=True)
        os.replace(tmp, self.path)
