# Reverse-engineering tools

These are the helper scripts used to study the original iOS binary (`decompiled/ipa/Payload/BEPiDGame.app/BEPiDGame`, 32-bit armv7 Thumb, Objective-C). They are analysis aids only and are not part of the game.

Requirements: Python 3.12 with `lief`, `capstone` and `unicorn`. Ghidra 12.2 with JDK 25 for the pseudocode export.

Run Python scripts that read the binary with `python -I` (isolated mode). The tracer scripts import `objc_trace` and take the tools folder as their first argument.

- `ExportDecomp.java`: Ghidra headless post-script. It writes pseudocode for every function to the path given as its argument. The output goes to `decompiled/analysis/decompiled.c`, which is not committed.
- `fn.sh`: prints functions from the pseudocode dump by name regex.
- `macho_info.py`: sections, linked libraries and encryption status.
- `objc_dump.py`: class dump (ivars, properties, methods, implementation addresses). Its output is `decompiled/analysis/classes.txt`.
- `cfstrings.py`: every string literal. Its output is `decompiled/analysis/cfstrings.txt`.
- `thumbdis.py <bin> <start> <end>`: Thumb disassembly with import stubs named and literal pools decoded.
- `refs.py <bin> <start> <end>`: compact list of selectors, strings, classes, constants and calls referenced in a range. Useful for blocks that Ghidra didn't turn into functions.
- `emu_enemies.py <bin> 0x416c8`: runs the enemy constructor for every type code and prints its stats.
- `objc_trace.py`: the tracing emulator. It runs original methods under Unicorn, executes methods implemented in the binary for real, and mocks and logs framework calls (SpriteKit actions, sounds, speech and so on) with decoded arguments. Blocks passed to the framework are captured and can be run afterwards.
  - Note: on iOS armv7, 64-bit arguments are only 4-byte aligned and can be split between r3 and the stack.
  - The scene frame is 320 by 568 points.
  - `arc4random` returns `Tracer.rand_value`.
- `trace_bosses.py <tools> <bin> <outdir>`: writes a trace per boss to `decompiled/analysis/traces/`.
- `scan_class.py <ClassName>`: walks a class's whole code range in address order, including blocks between methods, and prints each method's selectors, strings, constants and calls. It's the quickest way to see a scene's flow.
- `trace_stage.py <chapter> <stage> [method]`: runs a campaign stage opening (or another scene method) in the tracing emulator, runs every captured block in order, and prints the narration, delays, spawns and boss creation. Its output is `decompiled/analysis/traces/chapterN_stageM.txt`.
- `trace_tutorial.py <section>`: traces a tutorial section (narration order, enemy moves, waits) with audio playback mocked.
- `trace_cutscene.py <chapter>`: traces a chapter intro cutscene (title card, narration order, images) with audio playback mocked.

Caveat: a message sent to nil (for example to the player ship when a traced scene never created one) returns 0 and isn't logged, just like on iOS. A trace can therefore miss calls such as `[playerShip setRececiveDemage:NO]`. Cross-check anything that affects the player against `decompiled.c`.
