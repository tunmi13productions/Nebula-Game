r"""Builds and releases this game. Its settings are in release.json.

Run it with the game's venv, like env\Scripts\python release.py, for a menu.
The tool itself is game-release, shared by every game, so a fix to it reaches them all."""
from game_release.cli import main

main()
