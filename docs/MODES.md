# Free mode and tutorial

Recovered from `FreeModeScene`, `TutorialScene` and the shared `BaseScene` loop. Ship codes refer to the enemy table in `NOTES.md`. Narration files are named by their Localizable.strings key: the Portuguese file is `key.mp3` and the English one is `key_en.mp3`.

## Shared base loop (`BaseScene::baseActions`)

It runs every 1.0 second (action key "BaseActions") unless paused.

- Laser contact: if the player is still touching an enemy laser beam (the "toaster" contact is set, its ship is still in the scene, and the player is alive), the player takes that ship's shoot damage again. So a laser hits once on contact and then once per second while you stay in it. A fatal hit runs `endGame` after 1.5 seconds.
- Timed power-ups: only while timeBetweenPowerUps > 0. timeToNextPoweUp drops by 1 each tick. When it goes below 0: release a power-up of a random type between powerUpType1 and powerUpType2 (inclusive), then set timeToNextPoweUp to a random value between timeBetweenPowerUps and 2 * timeBetweenPowerUps. The campaign never sets these, so there are no timed power-ups there.
- Talking movement: while talkingMove and allowMove are both on, a repeating action (key "TalkingMovement") runs `talkingMoveAction` every 0.3 seconds, which speaks "Right", "Left" or "Stopped" when the movement state changes. Otherwise that action is removed.

## Free mode (`FreeModeScene`)

### Start

- The main menu music stops. BaseScene's `didMoveToView:` runs, and a countdown runs once per second (key "RegressiveCounter"). It speaks "3", "2", "1" at rate 0.55 while showing them, then shows and speaks "Start!" (`versus_Inicio`).
- After "Start!": createFirstEnemy runs after 0.5 seconds. Timed power-ups are set to timeBetweenPowerUps = 60 and timeToNextPoweUp = 60, with types 1 to 4 (life, shield, speed and fast shot are all possible).
- Score: every kill adds the ship's score and speaks "Score: N." at rate 0.6 (stage 0 counts as free mode). See NOTES.

### Enemy pools (built in initWithSize:)

- Base pool, 23 entries in this order: 0, 2, 1, 22, 9, 10, 40, 42, 4, 6, 47, 28, 17, 26, 28, 48, 29, 30, 32, 36, 17, 18, 19.
- Special pool, 18 entries in this order: 7, 8, 11, 43, 20, 23, 31, 34, 33, 44, 35, 3, 19, 25, 13, 16, 15, 27.
- Boss list, 8 entries: 1, 2, 3, 4, 5, 6, 9, 10.
- A kill counts as "base" if its code appears anywhere in the base pool (`isBaseEnemy:`). Codes 17 and 19 are in both pools, so a special 19 that's killed is handled as a base kill. Original quirk, keep it. Bosses report code 100, which isn't in the base pool, so they count as specials.

### Spawning

- Each pool has a sliding window of indexes [ini, fin]. A spawn picks a random index in the window (inclusive) and spawns that entry.
- createFirstEnemy: in-scene and total counts are set to 0. The base window starts at [0, 3] and the special window at [0, 1]. nextBaseType = random 4 to 8, nextSpecialType = random 8 to 13. Then releaseEnemyBaseEnemy.
- releaseEnemyBaseEnemy: only one base enemy is ever in the scene at a time. If none is present, it spawns one and totalBase += 1. Once totalBase is 10 or more and no special has ever been spawned, it also calls releaseEnemySpecialEnemy. So specials start after the tenth base enemy.
- releaseEnemySpecialEnemy: only one special at a time. If none is present: totalSpecial += 1. Every 10th special (totalSpecial divisible by 10) is a boss instead:
  - bossCode += 1. If it reaches 8 (the list length) it wraps to 1. The boss is `bossList[bossCode]`.
  - bossCode starts at 0 and is incremented before use, so the order is 2, 3, 4, 5, 6, 9, 10, then 2 again. Boss 1 never appears in free mode. Original quirk, keep it.
  - Otherwise, a random entry from the special window.
- destroyEnemy:
  - Base kill: baseInScene -= 1, then releaseEnemyBaseEnemy.
  - Special kill: specialInScene -= 1. Then:
    - If nextSpecialType < totalSpecial and fin < 17: nextSpecialType = totalSpecial + random 8 to 13, and the special window shifts up by one (both ends).
    - The same check runs for the base window: if nextBaseType < totalBase and fin < 22, nextBaseType = totalBase + random 4 to 8, and the base window shifts up by one.
    - Then releaseEnemySpecialEnemy.
  - The windows only advance on special kills, so difficulty climbs as you kill specials.
- There's also an `objetos:` method that drops a sprite with category 0x10 every so often. It's probably an obstacle. Check whether it's ever scheduled in free mode.

### End

- On death: touch is blocked, all sounds and speech stop, and the map generator stops. If the score beats `bestScore` (NSUserDefaults), it's saved. The score is reported to the Game Center leaderboard "ModoLivre". Then the free mode game-over screen appears (`game_over_freemode`: "Game Over. You scored N points! Best score: M points.").

## Tutorial (`TutorialScene`)

The tutorial selection screen chooses a section (tutorialType 1 to 6). Narration plays through the scene's own AVAudioPlayer (`playAudioFileNamed:completion:`), non-positional, each clip starting when the previous one finishes. Coordinates assume a 320 by 568 scene.

1. Movement (`tutorial1`): shooting and movement are disabled and talking movement is turned on. It plays tut_1.0, 1.1, 1.2, 1.3, then enables movement. There's no enemy and no scripted end. The player practises moving (with "Left", "Right", "Stopped" and the edge sounds) and leaves through the pause menu. Confirm there's no hidden end condition.
2. Enemies (`tutorial2`): movement and shooting are disabled.
   - It plays tut_2.0. When it finishes, an enemy (ship 1) spawns with its AI off and moves to (160, 454.4), which is 0.8H, over 1.5 seconds.
   - It plays tut_2.1, 2.2 and 2.3.
   - The enemy moves to x = 20 over 1 second. Then wait 2 seconds and play tut_2.4 (it's on the left).
   - The enemy moves to x = 300 over 2 seconds. Then wait 1 second and play tut_2.5 (now on the right).
   - The enemy fires (manualShot) and moves to x = 20 over 2 seconds. Then wait 1 second and play tut_2.6.
   - The enemy fires again and moves to x = 160 over 1 second. Then wait 0.5 seconds and play tut_2.7.
   - The enemy fires once more. Then movement is enabled and the enemy's normal AI starts (movement every 1 second, shooting every 1.0 second).
3. Attack (`tutorial3`): it plays tut_3.0 to 3.4, then enables movement and shooting and spawns ship 0 with normal movement. Each kill respawns another ship 0 (destroyEnemy calls createEnemy). There's no scripted end.
4. Battle (`tutorial4`): it plays tut_4.0 to 4.5, then enables movement and shooting. It sets timed power-ups of types 3 to 4 (speed and fast shot) with timeBetweenPowerUps = 20 and the first one after 5 seconds. It spawns ship 0 and calls `setRececiveDemage:` on it. The traced argument was 0, which would make it invulnerable. Confirm, since that looks odd for a battle lesson. A timer runs `checkIfEnded:`, which ends the tutorial once deathCounter > 0 (one kill).
5. Basic (`tutorial5`): it plays tut_5.0 and 5.1. A laser ship (7) spawns with its AI off and moves to (248, 454.4) over 1.5 seconds. It plays tut_5.2 and the laser ship fires once. It plays tut_5.3, then enables movement and shooting, and the laser ship fires every 3 seconds. On each kill, createEnemy runs with a counter (aux):
   - aux 0: shooting is disabled and tut_5.4 plays (then the completion block at 0x2f931, not traced).
   - aux 1 and 2: a fuel tank (46) spawns.
   - After that: endTutorial.
6. Special (`tutorial6`): movement and shooting are enabled from the start. It plays tut_6.0 to tut_6.10. Note that the `tut_6.2` key maps to the tut_6.0 audio file in both languages, an original data bug to keep. Then it spawns ship 0 and the generator is used (probably the nebula). On each kill, createEnemy uses aux:
   - aux 0: ship 0.
   - aux 1: laser ship 3.
   - aux 2 and 3: fuel tank 46.
   - After that: endTutorial.
- endTutorial: it stops the voice player, removes all actions, tears down the scene (`destroiCena`), then `endGame`. The tutorial's endGame shows the "Tutorial Completed" screen. Not traced yet.
- The menu section names are Movement, Enemies, Attack, Battle, Basic and Special (`tut_movimento`, `tut_inimigo`, `tut_ataque`, `tut_batalha`, `tut_basico`, `tut_especial`). The order in the selection menu, and which number each maps to, still need checking in `TutorialSelectionViewController`. The mapping above follows the tutorialN method numbers.
- The `intro_tut` key points to `intro_tut_en.mp3` and `tut_intro.mp3`, which aren't in the bundle. Find out who plays it and what happens when the file is missing.
