r"""The optional settings file, %APPDATA%\Nebula\settings.json. It's also where saved progress will live.

Recognised keys (all optional; the Settings screen writes them):
- "language": "en" or "pt", overriding the Windows display language ("auto" or missing follows Windows).
- "tilt": the acceleration a held arrow key stands for (default 0.3).
- "fast_tilt": the same with Shift held (default 0.6).
- "danger_zone": how wide attack sounds stay centred, as a multiple (default 1.5).
- "sound_volume", "music_volume", "speech_volume": 0 to 1 (default 1).
- "speech_rate": the game voice's rate as a multiple of the original rates (default 1).
- "scale": pixels per point for the window (default 1.5).
- "controller_tilt": "on" or "off", steering by rolling a motion-sensing controller (default on).
- "controller_tilt_scale": how much roll counts as a full tilt, as a multiple (default 1).
- "vibration": "on" or "off", controller vibration (default on).
- "game_voice": "voice" (the game's own voice, default) or "screen_reader" (experimental).
- "player_name": the pilot name in multiplayer (asked for on the first visit).
- "server": the multiplayer relay as host:port (default tunmi13.com:13013).
A missing or unreadable file means no overrides.
"""
import json
import os
import sys


def user_dir():
    r"""Where the save and settings live: %APPDATA%\Nebula on Windows, ~/Library/Application Support/Nebula
    on macOS, and $XDG_DATA_HOME/Nebula (~/.local/share/Nebula) on Linux, as Sixth Sense Reborn does."""
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    elif sys.platform == 'darwin':
        base = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support')
    else:
        base = os.environ.get('XDG_DATA_HOME') or os.path.join(os.path.expanduser('~'), '.local', 'share')
    return os.path.join(base, 'Nebula')


def load_settings(path=None):
    path = path or os.path.join(user_dir(), 'settings.json')
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


DEFAULTS = {'tilt': 0.3, 'fast_tilt': 0.6, 'danger_zone': 1.5, 'sound_volume': 1.0, 'music_volume': 1.0,
            'speech_volume': 1.0, 'speech_rate': 1.0, 'scale': 1.5, 'language': 'auto',
            'controller_tilt': 'on', 'controller_tilt_scale': 1.0, 'vibration': 'on', 'game_voice': 'voice',
            'player_name': '', 'server': ''}


def setting(settings, key):
    value = settings.get(key, DEFAULTS[key])
    if key == 'danger_zone' and 'danger_zone' not in settings and 'laser_zone' in settings:
        value = settings['laser_zone']
    return value


def save_settings(settings, path=None):
    """Writes the settings file atomically."""
    path = path or os.path.join(user_dir(), 'settings.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def apply_settings(settings, services, tilt, window=None):
    """Puts the settings into effect: steering, the danger zone, volumes, speech rate and the window size.
    The language is read at start-up only."""
    from .audio.volumes import VOLUMES
    if tilt is not None:
        tilt.tilt = float(setting(settings, 'tilt'))
        tilt.fast_tilt = float(setting(settings, 'fast_tilt'))
    services.danger_zone = float(setting(settings, 'danger_zone'))
    VOLUMES.sounds = float(setting(settings, 'sound_volume'))
    VOLUMES.music = float(setting(settings, 'music_volume'))
    VOLUMES.speech = float(setting(settings, 'speech_volume'))
    VOLUMES.speech_rate = float(setting(settings, 'speech_rate'))
    services.haptics.enabled = setting(settings, 'vibration') != 'off'
    services.voice.reader_mode = setting(settings, 'game_voice') == 'screen_reader'
    if window is not None and hasattr(window, 'set_scale'):
        window.set_scale(float(setting(settings, 'scale')))
    pads = getattr(window, 'pads', None)
    if pads is not None:
        pads.tilt_enabled = setting(settings, 'controller_tilt') != 'off'
        pads.tilt_scale = float(setting(settings, 'controller_tilt_scale'))
