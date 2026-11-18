# Campaign chapter scripts

Recovered from `ChapterNScene` in the original binary. Each chapter has four levels ("stages"), chosen through BaseScene's `stageNumber`, 1 to 4. Ship codes refer to the enemy table in `NOTES.md`.

Conventions used below:

- "Speak X" means: show the line in the message window under the speaker name "I.C.A.R.U.S." and speak it through the synthesizer at rate 0.55. Delays are given as (pre, post) in seconds when they aren't zero.
- "Victory" means `defaultVictoriousAnimation`.
- "old" is an in-scene counter's value before the kill decremented it. "none left" means the in-scene count reached 0.
- Openings and endings were verified by tracing (`decompiled/analysis/traces/chapterN_stageM.txt`, made with `tools/re/trace_stage.py`).
- The authoritative kill rules are the translation in `nebula/game/chapters.py`. `tests/test_chapters.py` checks every chapter's `destroyEnemy:` against the original running in the emulator (`tools/re/chapter_oracle.py`), from random counter states and along whole simulated stages, comparing spawns, power-ups, the method the stage ends in, and all counters. The prose below is a summary. Where it and the code disagree, the code is right.

## Shared structure

- `didMoveToView:`: movement and shooting are disabled. The cutscene node is created, the chapter's MapGenerator stage is set up, and foreground generation is suspended.
  - Stage 1 only: the chapter intro cutscene plays (`playIntroCutSceneChapter: N`). Its completion removes the cutscene, resumes foreground generation, runs BaseScene's `didMoveToView:`, then `nextStage`.
  - Other stages: BaseScene's `didMoveToView:` runs, then `nextStage` straight away.
- `nextStage`: all six spawn counters are reset to 0 (small, medium and laser, each with a total and an "in scene" count). Movement and shooting are enabled. The stage's opening runs, then `didBeginStage:onChapter:onMode:` and `blockTouch: NO`.
- Each `createX` method increments the matching total and in-scene counters, then calls `createEnemyWithType:` with a fixed ship code.
- `destroyEnemy: code` is called whenever an enemy is gone. It drives all spawning and the win condition. It fires when:
  - a ship is killed by shooting or ramming;
  - a boss part or boss is killed;
  - a drifting ship (an ally or a rock) leaves the screen at the bottom. Its `pushSpaceShip` completion removes it and calls `destroyEnemy: 90`. So code 90 means "a drifter left the screen".
- `releaseLife` (chapter 1) and `releasePowerUpOfType: 1` spawn a life power-up with a looping `beep_radar.caf`. Power-up types: 1 is life, 2 is shield, 3 is speed, 4 is fast shot.
- `baseActions` (chapter override, runs on BaseScene's periodic loop): when the player's life is exactly 2 and no power-up has been released yet in this stage, it releases a life power-up once.
- `endGame` (the player died, or chapter 6's ally limit was hit): didFailStage, stop all sounds and speech, BaseScene endGame, remove the life bar, show the campaign game-over screen.
- `endGameVictorious`: didWinStage, wait 2 seconds, then `missionComplete`.
- Boss stages: in every chapter, any `destroyEnemy:` during stage 4 ends the level (`endLvl`, or Victory directly). Since only the boss is present, that means killing the boss.

## Chapter 1: Refueling

Spawn methods: createSmallEnemy is ship 0. createTank is ship 46 (the fuel tank). createMediumEnemy is ship 2. createLaserEnemy1 is ship 7. createLaserEnemy2 is ship 8.

### Stage 1 (The Beginning)

- Opening (`intro`): speak `chap1_icarus1` (1, 0). When done: hide the window, then createSmallEnemy.
- Kill rules:
  - Ship 2: mediumInScene -= 1. If none are left and medium < 3: createMediumEnemy, and if medium is now 2, release a life power-up.
  - Ship 0: smallInScene -= 1. If none are left and (medium < 3 or mediumInScene != 0): createSmallEnemy, and if small is now 5, also createMediumEnemy.
  - After any kill: if medium == 3 and smallInScene == 0, Victory.

### Stage 2 (Obstacles)

- Opening (`intro2`): createSmallEnemy and createMediumEnemy at once, with no message.
- Kill rules:
  - Ship 7: laserInScene -= 1. If none are left and laser < 3: createLaserEnemy1.
  - Ship 2: mediumInScene -= 1. If none are left and medium <= 3: createMediumEnemy. Otherwise, if medium == 4 (whether or not mediums are left), release a life power-up and createLaserEnemy1.
  - Ship 0: smallInScene -= 1. If none are left and (laser < 3 or laserInScene != 0): createSmallEnemy.
  - After any kill: if laser == 3 and smallInScene == 0, Victory.

### Stage 3 (Approximation)

- Opening (`intro3`): speak `chap1_icarus1.2` (1, 0), the fuel tank warning. When done: hide the window, createTank, createLaserEnemy1.
- Kill rules:
  - Ship 0 or 46: smallInScene -= 1. If none are left and (laser < 3 or laserInScene != 0): createSmallEnemy or createTank, 50/50.
  - Ship 7: laserInScene -= 1. If none are left: if laser < 1, createLaserEnemy1. If laser == 1, release a life power-up and createLaserEnemy2.
  - Ship 8: laserInScene -= 1. If none are left and laser < 5: createLaserEnemy2.
  - After any kill: if laser == 5 and smallInScene == 0, Victory.

### Stage 4 (Hostile Station)

- Opening (`stage4Loop`): movement and shooting are disabled. Speak `chap1_icarus2` (0, 1). When done: speak `chap1_icarus3` (mercenary ship sighted), wait 0.5 seconds, then makeBossEntrance.
- makeBossEntrance: a blurred, upside-down Boss_01 sprite slides down over 4 seconds (visual only). When done: it's removed, Boss 1 spawns, and movement and shooting are enabled again.
- Boss killed, so endLvl (runs once): movement and shooting are disabled. The refuelling station sprite appears. Speak `chap1_icarus4` (arrived, docking). The ship moves toward the station and shrinks. Then endGameVictorious.

## Chapter 2: Direction

Ships: small1 is 10, small2 is 41, medium1 is 40, medium2 is 43, laser1 is 42 (a laser ship).

### Stage 1 (The Coordinates)

- Opening (`intro1`): speak `chap2_icarus1` (1, 0). When done: createSmallEnemy1.
- Kill rules:
  - Ship 40: mediumInScene -= 1. If none are left and medium < 5: createMediumEnemy1.
  - Ship 10: smallInScene -= 1. If none are left and (medium < 5 or mediumInScene != 0): createSmallEnemy1, and if small is now 2, also createMediumEnemy1.
  - After any kill: if medium == 5 and smallInScene == 0, Victory.

### Stage 2 (The Path)

- Opening (`intro2`): speak `chap2_icarus2` (1, 0), the nebula warning, and resume foreground (nebula) generation. When done: createSmallEnemy1 and createSmallEnemy2.
- Kill rules:
  - Ship 42: laserInScene -= 1. If none are left and laser < 4: if laser == 2, release a life power-up. Then createLaserEnemy1.
  - Ship 41 or 10: smallInScene -= 1. If none are left:
    - If small > 3 and laser < 4: if laser == 0, release a life power-up and createLaserEnemy1. Then createSmallEnemy2.
    - If small > 3 and laser >= 4: createSmallEnemy2 only if laserInScene >= 1.
    - If small <= 3: createSmallEnemy2.
  - After any kill: if laser == 4 and smallInScene == 0, Victory.

### Stage 3 (Approximation)

- Opening: createSmallEnemy2 and createLaserEnemy1 at once.
- Kill rules:
  - Ship 43: mediumInScene -= 1. If none are left and medium < 2: release a life power-up, createMediumEnemy2.
  - Ship 42: laserInScene -= 1. If none are left and laser < 5: if laser > 3, createMediumEnemy2, otherwise createLaserEnemy1.
  - Ship 41: smallInScene -= 1. If none are left and (medium < 2 or mediumInScene > 0): createSmallEnemy2.
  - After any kill: if medium == 2 and smallInScene == 0, Victory. A medium may still be alive at that point. Original behaviour, keep it.

### Stage 4 (Deception)

- Opening (`stage4Loop`): movement and shooting are disabled. Speak `chap2_icarus3` (big enemy ship near the planet). When done: Boss 2 spawns, and movement and shooting are enabled. There's no blurred approach in this chapter.
- Boss killed, so endLvl: speak `chap2_icarus4` (destroyed, landing), then Victory.

## Chapter 3: Hyperdrive

Ships: small1 is 43, small2 is 22, small3 is 21, medium1 is 6, medium2 is 20, laser1 is 23 (a laser ship).

### Stage 1 (Charged Up)

- Opening (`intro1`): speak `chap3_icarus1` (Pluto is this way, warp engine charging). When done: createSmallEnemy1 and createMediumEnemy1.
- Kill rules:
  - Ship 6: mediumInScene -= 1. If none are left and medium < 2: createMediumEnemy1.
  - Ship 43: smallInScene -= 1. If none are left and small < 2: createSmallEnemy1.
  - After any kill: if medium == 2, small == 2, and both in-scene counts are 0 or less: endStage1.
- endStage1: movement and shooting are disabled. Speak `chap3_icarus2` (warp engine at 100 percent, jumping). Then the warp visual plays with `science_fiction_warp_dimensional.mp3`, then endGameVictorious.

### Stage 2 (Jump)

- Opening: createSmallEnemy2 only.
- Kill rules:
  - Ship 20: mediumInScene -= 1. If none are left: if medium < 5, createMediumEnemy2. Otherwise release a life power-up and createLaserEnemy1.
  - Ship 23: laserInScene -= 1. If none are left and laser < 4: if laser == 2, release a life power-up. Then createLaserEnemy1.
  - Ship 22: smallInScene -= 1. If none are left:
    - If small > 5 and laser > 3 and laserInScene < 1: nothing spawns.
    - Otherwise: if small > 5 and medium == 0, release a fast-shot power-up and createMediumEnemy2. Then createSmallEnemy2.
  - After any kill: if laser == 4 and smallInScene == 0, Victory.

### Stage 3 (No Vision)

- Opening (`intro3`): speak `chap3_icarus3` (not enough energy, warp aborted), then `chap3_icarus4` (huge nebula field ahead). When done: createSmallEnemy2 and createMediumEnemy2.
- Kill rules:
  - Ship 20: mediumInScene -= 1. If none are left: if medium < 4, createMediumEnemy2. Otherwise release two life power-ups and createLaserEnemy1.
  - Ship 21: smallInScene -= 1. If none are left and (laser < 2 or laserInScene > 0): createSmallEnemy3.
  - Ship 22: smallInScene -= 1. If none are left: if small < 2, createSmallEnemy2. Otherwise release a speed power-up and a fast-shot power-up, then createSmallEnemy3.
  - Ship 23: laserInScene -= 1. If none are left and laser < 2: createLaserEnemy1.
  - After any kill: if laser == 2 and smallInScene == 0, Victory.

### Stage 4 (Pluto)

- Opening (`stage4Loop`): movement and shooting are disabled. Speak `chap3_icarus5` (arriving at Pluto, enemy base in range). When done: makeBossEntrance, which is the blurred Boss_03 approach over 4 seconds, then Boss 3, and movement and shooting are enabled.
- Boss killed: Victory directly. There's no endLvl line in this chapter.

## Chapter 4: Home

Ships: rocks only, through createSmallEnemy.

- createSmallEnemy picks `getRandomNumberBetween: 0 maxNumber: 3` (which is arc4random % 4) and compares the result with 49, 48 and 47. It can never match, so it always spawns ship 50, the largest rock (life 6, damage 5). The emulator confirms this. Original bug, keep it.

### Stage 1 (Neptune)

- Opening (`intro1`): speak `chap4_icarus1` (enemy base at Neptune). When done: Boss 4.
- Any kill: Victory.

### Stage 2 (Rings of Death)

- Opening (`intro2`): speak `chap4_icarus2` (the rings of Saturn, avoid the rocks). When done: createSmallEnemy.
- Kill rules: every destroyEnemy, whether shot, rammed, or passed off-screen (code 90), does smallInScene -= 1. Then:
  - If small < 5: one createSmallEnemy.
  - Otherwise, if small < 20:
    - If old < 2: two createSmallEnemy.
    - If old == 2: one.
    - If old > 2: none.
  - After any kill: if small >= 20 and smallInScene <= 0, Victory.

### Stage 3 (Jupiter)

- Opening (`intro3`): speak `chap4_icarus3` (enemy base at Jupiter). When done: Boss 6.
- Any kill: Victory.

### Stage 4 (Mars)

- Opening (`intro4`): speak `chap4_icarus4` (enemy base at Mars). When done: Boss 10.
- Boss killed, so endLvl: speak `chap4_icarus5` (arriving at Earth, contacting the commander), then Victory.

## Chapter 5: Burning

Ships: small1 is 28, small2 is 29, medium1 is 31, laser1 is 30 (a laser ship).

### Stage 1 (Venus)

- Opening (`intro1`): speak `chap5_icarus1` (destroy the mothership, fuselage is thick), then `chap5_icarus2` (lure it to the Sun). When done: createSmallEnemy1, and createSmallEnemy2 after 3 seconds.
- Kill rules:
  - Ship 31: mediumInScene -= 1.
  - Ship 29: smallInScene -= 1. If old < 3:
    - If small < 6: createSmallEnemy2.
    - Otherwise, if old < 2 and small == 6: createMediumEnemy1, then createSmallEnemy1.
  - Ship 28: smallInScene -= 1. If old < 3:
    - If small < 5: createSmallEnemy1.
    - Otherwise, if old < 2 and small <= 6: createMediumEnemy1, then createSmallEnemy2.
  - After any kill: if small >= 6 and the small, medium and laser in-scene counts are all 0, Victory.

### Stage 2 (Mercury)

- Opening: createSmallEnemy1 and createSmallEnemy2.
- Kill rules:
  - Ship 28: smallInScene -= 1. If old < 3: if small < 3, createSmallEnemy1, else if laser < 4, createLaserEnemy1.
  - Ship 29: smallInScene -= 1. If old < 3 and laser < 4: createSmallEnemy2. There's also an unreachable branch (small < 1 and laser == 4: createLaserEnemy1 plus a fast shot).
  - Ship 30: laserInScene -= 1. If none are left: if laser < 4, createLaserEnemy1, else if laser == 4, createMediumEnemy1.
  - Ship 31: mediumInScene -= 1.
  - After any kill: if laser == 4 and the small, laser and medium in-scene counts are all 0, Victory.

### Stage 3 (Almost There)

- Opening: createMediumEnemy1 and createLaserEnemy1.
- Kill rules:
  - Ship 28: smallInScene -= 1. If old < 6: createLaserEnemy1.
  - Ship 29: smallInScene -= 1. If old < 3 and laser < 5: createMediumEnemy1.
  - Ship 30: laserInScene -= 1. If none are left and laser < 5: if laser == 2, release a fast-shot power-up. Then createSmallEnemy1.
  - Ship 31: mediumInScene -= 1. If laser < 5: createSmallEnemy2.
  - After any kill: if laser >= 5 and the small, medium and laser in-scene counts are all 0, Victory.

### Stage 4 (The Sun)

- Opening (`stage4Loop`): speak `chap5_icarus3` (we're at the Sun's surface, finish it). When done: Boss 5.
- Boss killed: the `boss` node is removed, then endLvl: speak `chap5_icarus4` (mothership destroyed, route back to Earth). Then makePlayerTurnAround, a visual sequence where the ship turns and flies off over a few seconds, then endGameVictorious.

## Chapter 6: Exodus

Ships: small1 is 4, laser1 is 5 (a laser ship). The allied civilian ships are medium1 37, medium2 38 and medium3 39. small2 (22) and small3 (21) are defined but not used in the rules read so far.

- inocentCounter: +1 for each allied ship (37 to 39) that's destroyed. Allies leaving the screen (code 90) don't count. After any kill in stages 2 to 4, if inocentCounter > 4 (that is, 5 allies destroyed) the stage is lost: `endGame`. That matches `chap6_icarus2`.
- Stage 1 (Escort): opening is createSmallEnemy1 and createLaserEnemy1. Laser ships respawn up to 8, with a fast-shot power-up released when laser is 1 or 4. Small ships respawn while laser < 8 or a laser is present. Victory when laser == 8 and no small ships remain.
- Stage 2 (Rush): opening is speak `chap6_icarus1` (allies detected, avoid them), then `chap6_icarus2` (0.5, 0) (destroying 5 allies means critical failure). When done: createMediumEnemy1. Allies keep streaming down. Each one that's killed or leaves the screen is replaced (random type on code 90) until 20 have spawned. Victory when medium >= 20 and none are in the scene.
- Stage 3 (Frontline): opening is createMediumEnemy1 and createMediumEnemy2. The same ally stream as stage 2, denser: a code 90 with at most one ally left spawns two. Victory at 20 allies spawned with none left.
- Stage 4 (Ambush): opening (`intro4`) is speak `chap6_icarus3` (0.5, 0.5) (mercenary ambush). When done: createSmallEnemy1, createLaserEnemy1, and releases a fast-shot and a speed power-up. Killing small ships spawns random allies. Lasers respawn up to 3, with a shield power-up at laser 1. When laser >= 3 and no small or ally ships remain: endLvl, which speaks `chap6_icarus4` (last ship of the ambush), then Victory.
- Unused code: Chapter6Scene has a `stage4Loop` and a makeBossEntrance that build a blurred Boss_01 with three invisible laser-capable hitbox ships (codes 100, 101, 102) and a wiggle, and baseActions keeps those three ships' life in step. nextStage sends stage 4 to `intro4`, so none of it is reachable. Not ported.

## Chapter 7: Hope

Ships: small1 is 36, small2 is 33, small3 is 32, medium1 is 34, medium2 is 44, medium3 is 35, laser1 is 3 (a laser ship).

- Stage 1 (Search): opening is speak `chap7_icarus1` (0.5, 0) (day 0, coordinates received), then `chap7_icarus2` (0.5, 0.5) (140 million civilian ships following). When done: createSmallEnemy1. Waves of 36s and 34s, with power-ups that depend on the player's life. Victory once 8 small and 4 medium have spawned and none remain.
- Stage 2 (Leader): opening is speak `chap7_icarus3` (0.5, 0) (day 152). When done: createSmallEnemy2. Mixed 33, 44 and 35 waves.
- Stage 3 (Distant Planet): opening is speak `chap7_icarus4` (0.5, 0) (day 241). When done: createLaserEnemy1. Lasers up to 4, with smalls (32) and mediums (35, 44) mixed in.
- Stage 4 (New Home): opening is speak `chap7_icarus5` (0.5, 0) (day 364, planet in sight), then `chap7_icarus6` (0.5, 0.5) (mothership located). When done: Boss 7. Boss killed: the boss node is removed, then endLvl speaks `chap7_icarus7` (mission complete, landing and colonisation), then Victory.

## Chapter 8: Revenge

Ships: small1 is 17, small2 is 18, medium1 is 19, medium2 is 25, laser1 is 27 (a laser ship).

- Stage 1 (One Way Trip): opening is speak `chap8_icarus1` (0.5, 0.5) (tracing their homeworld). When done: createSmallEnemy1, and createSmallEnemy2 after 3 seconds.
- Stage 2 (Determination): opening is createSmallEnemy2 and createMediumEnemy1.
- Stage 3 (Shoot Everything): opening is createLaserEnemy1 and createMediumEnemy2. Lasers respawn (up to 5 or 6) with smalls and mediums (19 and 25, up to 7). Victory when laser >= 5 and nothing remains.
- Stage 4 (Arrival): opening is speak `chap8_icarus2` (0.5, 0.5) (approaching Pegasus, defence ship sighted). When done: Boss 8. Boss killed, so endLvl: speak `chap8_icarus3` (enemy destroyed, arrived), then Victory.
- Note: the strings table also has `chapter8_part1` ("Sending message."), `chapter8_part2` (an mp3) and `chapter8_part3` ("Message sent."). They're likely used by the chapter 8 or 9 cutscene. Check in CutScene.

## Chapter 9: Pegasus

Ships: small1 is 12, small2 is 14, medium1 is 13, medium2 is 16, laser1 is 15 (a laser ship).

- Stage 1 (Ice and Metal): opening is speak `chap9_icarus1` (0.5, 0.5) (route to the nearest planet rift). When done: createSmallEnemy1.
- Stage 2 (Root of the Problem): opening is createSmallEnemy2.
- Stage 3 (Descent): opening is createMediumEnemy2. The `enterGround` sequence (black fade, metal ground and crack textures) belongs to this part of the descent. It ends in Victory. Confirm when it's triggered.
- Stage 4 (For Earth!):
  - Opening (`finalBossIntro`): speak `chap9_icarus2` (0.5, 1.5) (a 99.9 percent chance of not surviving, carry on?). Then speak `chap9_icarus3` (silence taken as confirmation, core guardian sighted). When done: makeBossEntrance, which spawns Boss 9 and enables movement and shooting.
  - Boss killed, so endLvl: movement and shooting are disabled. Speak `chap9_icarus4` ("Sir, it has been an honor."). Then `endItAll`:
    - A white overlay fades in over 4 seconds while `chap9_icarus5` is spoken (your logs were sent to New Earth).
    - Speak `chap9_icarus6` ("Brace for impact in 3..."), then speak "2..." and "1...". Those two are hard-coded strings, not localized, so they're the same in both languages. Original quirk, keep it.
    - Play `endingSound.mp3`. Wait 5 seconds, `runFastCredits`, wait 8 seconds, then fade out.
