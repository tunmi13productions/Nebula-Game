# Port plan

How the Windows port is laid out and built. It covers architecture, folders and order of work. Behaviour comes from `NOTES.md`, `CHAPTERS.md`, `MODES.md` and `MENUS.md`. Every departure from the original goes in `DEVIATIONS.md`.

## Guiding rules

- Game logic never touches a sound device or the screen reader. It calls small audio and speech interfaces, and tests swap in silent fakes, so every test runs without sound.
- The original is built on SpriteKit actions (sequences, waits, moves with easing, run-block, repeat forever) plus timers. The port gets a small action system with the same semantics, so timings can be copied one to one from the traces instead of being re-imagined.
- Coordinates stay in the original's scene space: 320 by 568 points, y pointing up, player near the bottom. All formulas recovered so far (Aureal volume and pan, movement speed, entrances, shot speeds) are written against that size, so nothing has to be rescaled.
- The simulation runs at a fixed 60 updates per second, which is SpriteKit's frame rate. The `update:` logic (movement, listener) runs per tick, and Aureal's 0.1 second timer and BaseScene's 1 second loop run as scheduled actions.

## Libraries (all already installed)

- `cyal` for OpenAL. It ships an `OpenAL32.dll`. Step 1 confirms that it's OpenAL Soft and honours `ALSOFT_DRIVERS=null`. If it doesn't, the official OpenAL Soft DLL goes in the project instead.
- `prism` (the prismatoid package) for screen reader speech.
- `soundfile` to decode the original mp3 and caf files.
- `pygame` for the window, keyboard events and the frame clock. The window is only there to receive keys. No visuals beyond the original's are planned.
- `pytest` for tests. `numpy` only where audio processing needs it.

## Folder layout

- `nebula/`: the game package.
  - `main.py`: entry point. It opens the window, picks the language, and runs the scene loop.
  - `engine/`: generic pieces that know nothing about Nebula.
    - `actions.py`: the SpriteKit-style action system (sequence, group, wait, move to and move by with easing modes, run block, repeat, keyed actions, remove from parent).
    - `nodes.py`: a scene graph of positioned nodes with parent and children, so "removed from the scene" means the same thing as in the original. Aureal relies on it.
    - `physics.py`: contact detection with category, contact and collision bit masks and the shapes the original uses (circle, rectangle, polygon edge loop), firing begin and end contact like SpriteKit.
    - `scheduler.py`: delayed calls (performSelector afterDelay, dispatch_after, NSTimer).
  - `audio/`:
    - `aureal.py`: the positional audio engine as pure math plus sound bookkeeping, a direct copy of Aureal (volume, cube-root pan, the behind-the-player mask, linking, the 0.1 second update, the fade). It talks to a backend interface.
    - `backend.py`: the interface (load, play once or looped, set volume and pan, stop, pause, resume), plus a null backend that records calls for tests.
    - `openal_backend.py`: the real backend on cyal and OpenAL Soft. AVAudioPlayer pan and volume are reproduced with a stereo pan law (see open questions). Stereo files such as the swooshes, bounds and thunder play unspatialised, like AVAudioPlayer did.
    - `players.py`: the non-positional players the original used directly. That's SKAction playSoundFileNamed for effects, and AVAudioPlayer for music, narration and tutorial clips.
  - `speech/`: `speech.py` is a Prism wrapper with the VoiceSynthesizer behaviour (speak with rate, pre and post delays, completion callback, stop, pause), plus a null version for tests. The original's completion callbacks ("when the line finishes, spawn enemies") need an end-of-speech signal. See open questions.
  - `game/`: Nebula itself.
    - `globals.py`: Global (upgrade stats, formulas, save and load).
    - `ship.py`, `boss.py`, `shots.py`, `powerups.py`
    - `base_scene.py`: BaseScene (player, input handling, contacts, swoosh fields, side walls, base loop, in-game menus).
    - `chapters/chapter1.py` to `chapter9.py`
    - `free_mode.py`, `tutorial.py`, `cutscene.py`
    - `menus/`: intro, main menu, campaign selector, Hangar, tutorial selection, info.
  - `input.py`: keyboard mapping (arrow keys to accelX and the other keys below).
  - `strings.py`: localized text lookup with the original's fallback behaviour plus the documented fixes.
- `data/`: data copied or converted from the bundle.
  - `strings/en.json`, `strings/pt.json`: converted from the Localizable.strings files (legacy encoding fixed).
  - `ships.json`: the enemy table. `ship_sounds.json`: from ShipSounds.plist. `bosses.json`.
  - `textures.json`: texture sizes from the atlas plist, which some hitboxes and positions depend on.
- `sounds/`: the original audio files, copied unchanged with their original names.
- `tests/`: pytest suites. `conftest.py` sets `ALSOFT_DRIVERS=null` and uses the null audio and speech backends.
- `tools/re/`: the existing analysis tools. A differential tester gets added here (see testing).

## Testing approach

- Unit tests for the pure parts: the Aureal formulas against values computed from the recovered math, upgrade formulas, the enemy table, damage rules, the action system's timings.
- Differential tests against the original binary: `tools/re/objc_trace.py` can run the original code. For logic-heavy functions (every chapter's `destroyEnemy:`, free mode spawning, `inflictDamage:`, the Aureal functions), a test drives both the port and the emulated original with the same inputs (random counter states, random numbers) and requires identical outcomes. This is how the hand-transcribed and summarised chapter rules get verified.
- Scenario tests: whole stages run headless with scripted inputs, asserting the sequence of spoken lines, sounds and spawns matches the traces in `decompiled/analysis/traces/`.
- No test ever opens a real audio device.

## Order of work (one feature per commit)

1. Project skeleton, the cyal and OpenAL Soft check, null backends, test setup.
2. Action system, scheduler and scene graph, with tests.
3. Aureal and the OpenAL backend, with tests. Plus a manual listening check by you.
4. Speech wrapper on Prism.
5. Strings and language selection, and copying the sounds and data.
6. The player ship, movement, input and listener, the side walls and boundary sounds, and talking movement.
7. Shooting (player and enemy), swoosh fields, contacts and damage.
8. Enemies: spawning, entrances, movement, lasers, engine sounds.
9. Power-ups and the base loop.
10. The tutorial, the first fully playable thing and a good place for you to start playtesting.
11. Free mode.
12. Bosses.
13. Chapters 1 to 9, one per commit, each with its differential test.
14. Cutscenes, menus, Hangar, saving, the startup sequence.

## Decided

- Keys, language and the override file are recorded in DEVIATIONS.md.
- Sound files are committed to the private repository in `sounds/`.
- Pan law: balance (the side the sound is on stays at full level, the other side fades out), chosen by ear on 2026-11-17 with `tools/demo_aureal.py`. Constant power stays available in the backend but isn't used.
- Speech: game speech is a OneCore voice rendered through Prism and played by the game, and accessibility labels go to the screen reader (see DEVIATIONS.md).
