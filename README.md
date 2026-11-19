# Nebula Game for Windows

A port of Nebula Game, an iOS audio space shooter by Gray Company, to Windows, in Python. The original `.ipa` is the source of truth: the game's logic, timings, sounds, speech and visuals are reproduced from its decompiled code and data, and every intentional difference is recorded in [docs/DEVIATIONS.md](docs/DEVIATIONS.md).

It is an audiogame first. Sound carries everything; visuals are drawn only where the original had them.

The player's guide, shipped with every build, is [readme.txt](readme.txt).

## Running from source

Requires Python 3.12 on Windows.

```
python -m venv env
env\Scripts\python -m pip install -r requirements.txt
env\Scripts\python -m nebula
```

- `python main.py` does the same as `python -m nebula`; it is the entry point the release builds use.
- `tools/play.py` starts straight into a chapter, free mode or a tutorial, for testing.
- Progress is saved in `%APPDATA%\Nebula\save.json` and settings in `%APPDATA%\Nebula\settings.json`. The Systems screen in the game writes the settings.

## Libraries

- Audio: OpenAL Soft, through cyal. Sounds are positioned the way the original's Aureal audio class placed them.
- Speech: Prism (prismatoid). The game's own voice is rendered by a Windows OneCore voice into memory and played through the game's audio, so the game knows when each line ends. Interface labels go to the player's screen reader.
- Window, input and controllers: pygame. A controller's motion sensor is read through SDL directly, since pygame doesn't wrap it.
- soundfile and numpy for decoding audio.

## Tests

```
env\Scripts\python -m pytest -q
```

The tests run without sound: they use a silent audio backend, and nothing in them opens an audio device or a real controller. When running anything else that touches audio during development, set `ALSOFT_DRIVERS=null` so OpenAL Soft uses its null backend.

## Building and releasing

Builds use [game-release](https://github.com/tunmi13productions/game-release), configured in `release.json`.

```
env\Scripts\python release.py
```

This opens a menu to build for this computer, make a console test build, build Linux in WSL, check what would block a release, or release. A release tags the version in `main.py` and pushes the tag; the workflow in `.github/workflows/release.yml` then builds Windows, Linux and both kinds of Mac on GitHub and publishes them together.

## Layout

- `nebula/`: the game.
  - `engine/`: a small SpriteKit-style node, action and scheduler system.
  - `game/`: the scenes (chapters, free mode, tutorials), ships, bosses, map generation, the HUD and the cutscenes.
  - `menus/`: the interface screens: main menu, campaign selector, tutorial selection, Hangar, About and Systems.
  - `audio/`: the OpenAL backend, the positional Aureal port and the music and effect players.
  - `speech/`: the game voice and screen reader output.
  - `render/`: the renderer and texture loading.
  - `controller/`: game controllers, motion steering and vibration.
- `sounds/`, `images/`, `data/`: the original's assets, extracted from the `.ipa`. `data/` also holds the strings, particle emitters and cutscene timelines.
- `tools/`: asset extraction and the reverse-engineering tools (`tools/re/`, including an emulator-based tracer of the original's Objective-C).
- `docs/`: [NOTES.md](docs/NOTES.md) (what the original does, as found), [MENUS.md](docs/MENUS.md) (its screens) and [DEVIATIONS.md](docs/DEVIATIONS.md) (every difference, with the original behaviour and the reason).
- `tests/`: the test suite.

`decompiled/analysis/` holds extracted listings and the emulator traces the port was built from. The `.ipa` itself, its unpacked files, the full decompiled source and the Ghidra project are kept in `decompiled/` locally and are not in the repository.

## Credits

Nebula Game was made by Gray Company: developed by Bruno Moreira, Diego Pereira, Felipe Delazeri, Leonardo Gubert and Lucas Carletti, with revision and testing by Márcia Campos, Lucas Santurio, Raí Carvalho and Ricardo Rauber. Its sounds came from FreeSFX, OpenGameArt and SoundJay, and its graphics from OpenGameArt and MillionthVector.

Windows port by tunmi13productions. The controller motion module comes from Sixth Sense Reborn (MIT License).

## Disclaimer

This port is an unofficial fan project. It is not affiliated with, endorsed by or connected to Gray Company or Nebula Game's original developers. Nebula Game, including its sounds, music, graphics, voice recordings, text and story, belongs to its original creators and rights holders, and all rights to it remain theirs.

Gray Company is no longer operating, and the original game has been removed from the App Store: once deleted from a device, it can no longer be downloaded again, even from purchase history. This port exists to keep the game playable. If you are one of the original developers or hold the rights to the game, and you would like this port changed or taken down, please contact tunmi13productions and your request will be honoured.
