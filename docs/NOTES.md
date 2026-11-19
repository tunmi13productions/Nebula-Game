# Nebula study notes

Findings from studying the original iOS build. Raw dumps live in `decompiled/analysis/`.

## Source package

- `decompiled/Nebula.ipa`, 95.5 MB, unpacked into `decompiled/ipa/`.
- The app bundle is `Payload/BEPiDGame.app`. The executable is `BEPiDGame`. "BEPiD" is the Apple Developer Academy program in Brazil, which is where the game came from.
- Bundle id `com.CiladaGames.Nebula`. Display name "Nebula". Version 1.3, build 1.1. Built with Xcode 8.1 against iOS SDK 10.1. Minimum iOS 8.2.
- Portrait only. Runs on iPhone and iPad. Requires GameKit (Game Center).
- The intro splash sound is `Cilada Games.caf`. The credits and Localizable strings also mention "Gray Company" (contato@graycompany.com.br).

## Executable

- Mach-O, 32-bit armv7, PIE. Not encrypted (cryptid 0), so the code is readable.
- Written in Objective-C. Uses SpriteKit for scenes, AVFoundation for audio (AVAudioPlayer) and speech (AVSpeechSynthesizer), CoreMotion (likely tilt input, still to confirm), GameKit for multiplayer, StoreKit for the in-app purchase, MessageUI for the contact email.
- Bundles the GameAnalytics SDK (all `GA*` classes). That's analytics only and not part of the game.
- Full class dump: `decompiled/analysis/classes.txt`. All string literals: `decompiled/analysis/cfstrings.txt`.

## Classes that matter

- `Aureal` is the game's own positional audio engine, built on AVAudioPlayer. It has a listener position, a max distance and a max X. It works out volume and pan per sound from the object's position (`getNewVolume:`, `getAngularPan:`, `getLinearPan:`, `getPanBasedOnMaxX:`). There are two volume curves, `maskNormalSound:` and `maskMuffledSound:`. Sounds can be linked to a sprite so they follow it, and an `NSTimer` updates them (`updateAudio:`). This is the heart of the game and must be reproduced exactly in OpenAL.
- `AurealAudioObject` is a subclass of AVAudioPlayer that stores the linked sprite, the key name, the max volume and the last known position.
- `VoiceSynthesizer` wraps AVSpeechSynthesizer. Text lines (for example the I.C.A.R.U.S. ship computer messages) are spoken with TTS. In the port that maps to Prism.
- `SpaceShip` is used for both the player and enemies. It tracks life, max life, shield, max shield, score, ship code, shoot damage and a laser. Methods include moving left and right, shooting, power-ups, taking damage, and announcing "less than 50% health".
- `Boss` handles bosses: life, shield, boss code, a laser with charge sound, and shooting sequences.
- `Shoot` is a bullet node. `PowerUp` has a power type. There are four power-ups: life, shield, fast forward (speed) and fast shoot.
- `BaseScene` is the shared gameplay scene. `Chapter1Scene` to `Chapter9Scene`, `TutorialScene`, `FreeModeScene` and `VersusScene` subclass it. `CampaignScene` is the chapter and level selector.
- `MapGenerator` handles visual backgrounds per chapter and stage. It's mostly visual, but it also spawns fuel tanks (chapter 1) and Saturn debris (chapter 4), which may matter for gameplay.
- `CutScene` plays chapter intro cutscenes: narrated mp3 parts plus images.
- `Capitulo` holds chapter data: intro text, title, four level labels and a Roman numeral.
- `Global` is a singleton holding upgrade points (shot, time shot, life, shield, speed, win points), last chapter and level, the campaign purchase flag and free mode. It saves them with NSUserDefaults keys `Shoot_Points`, `TimeShoot_Points`, `Life_Points`, `Shild_Points`, `Speed_Points`, `Win_Points`, `last_Chapter`, `last_Level`, `purchased_Campaing`, `Campaign_Mode`.
- View controllers: intro, main menu, settings (the "Hangar" upgrade screen), tutorial selection, campaign purchase, info (about, credits, contact).

## Game structure

- Modes on the main menu: Campaign, Free Mode, Multiplayer (Versus over Game Center), Hangar (upgrades), Tutorial, About.
- Campaign: 9 chapters with 4 levels each. Earlier versions sold chapters 2 to 9 as the "full campaign" purchase; version 1.3 (this one) made it free, and `Global init` sets purchasedCampaign to YES (see MENUS.md).
- Chapter titles: 1 Refueling, 2 Direction, 3 Hyperdrive, 4 Home, 5 Burning, 6 Exodus, 7 Hope, 8 Revenge, 9 Pegasus. Level names are in the `capN_lvlM` strings.
- Tutorial: 6 sections, Movement, Enemies, Attack, Battle, Basic and Special (the menu order still needs checking against the code). Each step is a narrated mp3 `tut_X.Y`.
- Free mode is endless with a score and a best score.
- The upgrade screen spends available points on Life, Shield, Power shot, Attack speed and Ship speed.
- On launch, the intro shows "PUT YOUR HEADPHONES FOR A BETTER EXPERIENCE" and plays thunder on the right ("Thunder at the right side").

## Localization

- Two languages: English (`Base.lproj`) and Portuguese (`pt.lproj`). The Localizable.strings files are compiled binary plists with correct Unicode text. They are converted to `data/strings/en.json` and `pt.json` by `tools/extract_strings.py`.
- Every narrated mp3 has a Portuguese version (`name.mp3`) and an English version (`name_en.mp3`). The strings table maps each key to the file for that language.
- Some UI images are localized the same way, for example `sair.png` and `sair_en.png`.
- The Portuguese table has keys the English one lacks: `lbl_*_points_button`, `cap_Block`, `pause`. That may cause English fallbacks in the original. Check how the code handles it.
- Known quirk: in both languages `tut_6.2` points to the `tut_6.0` audio file. That's an original bug, reproduce it unless told otherwise.

## Audio assets

- 207 audio files: 191 mp3 and 16 caf (PCM 16-bit). Full inventory with format, channels and duration: `decompiled/analysis/audio_inventory.txt`. All of them decode with soundfile (libsndfile).
- Ship engine loops: `Ship_1` to `Ship_50` plus extras. `ShipSounds.plist` maps `SpaceShipSound_N` (N from 0 to 50) to a sound file. Several map to `sonarpedra` (a rock sonar) and some are reused.
- Effects: shots, lasers, explosions, hits, power-up, swooshes left and right, screen boundaries left and right (`bound_left`, `bound_right`), radar beep, alarm, closing doors, warp.
- Music: `menuSound.mp3` (main menu, see MENUS.md), `Lino Rise - Channel Intro Pompeii.mp3`, `endingSound.mp3`, `Deep_Impact_3.mp3`.
- Missing: `intro_tut_en.mp3` and `tut_intro.mp3` are referenced by the `intro_tut` string but aren't in the bundle. `Impact.ttf` is listed as an app font but is also missing.

## Visual assets

- 226 png and 65 jpg, plus `Assets.car` (compiled asset catalog), two texture atlases (`gameTextures`, and `tch_gameTextures` for lower-end devices), 18 SpriteKit particle files (`.sks`) and the storyboards (compiled nibs for iPhone and iPad).
- The font `HACKED_Title.ttf` and a bitmap alphabet (`Alfabeto_X.png`, `AlfabetoAct_X.png`) are used for menu text.

## Decompilation setup

- Ghidra 12.2 headless, run with JDK 25. Pseudocode for all 1692 functions is in `decompiled/analysis/decompiled.c`, with real Objective-C method names (for example `Aureal::getNewVolume:`).
- Ghidra mangles floating point on this armv7 build because doubles are passed in integer register pairs. For any math, read the Thumb disassembly instead, or better, run the code in the tracing emulator. All the helper scripts live in `tools/re/` (see its README). The most useful one is `objc_trace.py`, which runs original methods and logs every SpriteKit, sound and speech call with exact values.
- Calls into imports often go through small thunks near 0x9e6cc. Their targets: 0x9e6cc is objc_release, 0x9e750 is cos, 0x9e75c is atan2.

## Recovered mechanics: Aureal audio engine

Coordinates are SpriteKit scene points with y pointing up. The player sits near the bottom of a portrait screen and enemies come from the top.

- Setup, in `BaseScene::createPlayerShip`: `configureMax_Y_Distance: H*1.25 max_X_distance: W andListenerPosition: playerShip.position inScene: self`. H and W are the scene frame height and width.
- Every frame, `BaseScene::update:` sets the listener position to the player ship's position.
- An `NSTimer` fires `updateAudio:` every 0.1 seconds.
- Each sound in the library is an AurealAudioObject keyed by a string. Its maxAudio defaults to 1.0 and isLinked to false.
- `executeOnceSoundNamed:inPosition:` configures the player at that position, sets loops to 0 and plays. `executeForeverSoundNamed:inPosition:` does the same with loops set to -1 (infinite).
- `linkSound:toObject:` attaches a sound to a sprite. It stores the sprite's current position as lastKnownPosition and sets isLinked to true.
- `updateAudio:` loops over every key in the library:
  - If the sound has no linked object: when it's not playing and isLinked is true, the key is queued for removal. Otherwise it's reconfigured at its lastKnownPosition.
  - If it has a linked object: when that object has no parent (it was removed from the scene), the sound is stopped immediately (option 2), unlinked and queued for removal. Otherwise it's reconfigured at the linked object's current position.
  - Queued keys are removed from the library afterwards.
- `configurePlayer:toExecuteInPosition: P`:
  - pan = getPanBasedOnMaxX(P), assigned to the AVAudioPlayer pan (AVAudioPlayer clamps pan to the range -1 to 1).
  - lastKnownPosition = P.
  - angle = atan2(P.y - listener.y, P.x - listener.x).
  - dist_vol = getNewVolume(P).
  - If angle < 0 (the sound is below, meaning behind, the player): factor = maskNormalSound(angle). Otherwise factor = maxAudio.
  - volume = dist_vol * factor.
  - Note: when the sound is behind, maxAudio is ignored, so a fade-out has no effect on sounds behind the player. That's an original quirk, keep it.
- `getNewVolume: P`: d = hypot(abs(P.x - lx), abs(P.y - ly)). Returns 1 - d / maxDistance, clamped to a minimum of 0. There's no upper clamp, but it can't exceed 1 anyway.
- `getPanBasedOnMaxX: P`: dx = P.x - lx. n = abs(int(W*0.5 - lx)), truncated toward zero. Returns cbrt(dx * (2 - n / W)) / cbrt(max_X). With the listener at the centre this reduces to cbrt(2*dx / W), a cube-root curve: pan rises steeply near the centre and flattens toward the edges.
- `maskNormalSound: a` and `maskMuffledSound: a` are byte-identical: min(1, (cos(2a) + 1) * 0.5 + 0.2). So a sound straight behind the player (a = -pi/2) plays at 0.2 of its distance volume, and a sound directly to the side plays at full volume.
- `getAngularPan:` returns cos(angle). `getLinearPan:` returns (P.x - lx) / max_X. Neither is used by configurePlayer. Check whether anything else calls them.
- `stopSoundNamed:withOptions:`: option 1 fades out, any other value stops immediately.
- `doVolumeFadeOutOnPlayer:`: maxAudio -= 1/6, then it stops if maxAudio <= 0, otherwise it repeats after 0.5 seconds. A full fade takes about 3 seconds.
- Aureal registers for app resign-active and become-active notifications to pause and resume.

## Recovered mechanics: input and movement

- Steering is tilt. CMMotionManager accelerometer, update interval 0.2 seconds.
- `outputAccelerationData:`: currentMaxAccelX is reset to 0 on every sample. Then it's set to acceleration.x if that's above 0.04 or below -0.04, otherwise it stays 0. Y is effectively always 0.
- `update:` runs every frame (SpriteKit, 60 fps), unless paused or movement isn't allowed:
  - If accelX > 0.05: the ship enters state 1 and `moveSpaceshipToLeft` is called once on entering the state.
  - If accelX < -0.05: the ship enters state 2 and `moveSpaceshipToRight` is called once on entering the state.
  - Otherwise: it enters state 0, calling `estabilizaSpaceshipToLeft` if coming from state 1 or `estabilizaSpaceshipToRight` if coming from state 2.
  - x += accelX * velocidadeMovimento, clamped to the range shipWidth/2 to W - shipWidth/2. Y doesn't change.
  - Then the audio listener is moved to the ship's position.
  - The state names look reversed relative to the method names. `talkingMoveAction` speaks state 1 as "Right" and state 2 as "Left", and x increases with accelX, so state 1 really is moving right. Check what the moveSpaceshipTo methods actually do (likely the sprite tilt plus the swoosh sounds).
- velocidadeMovimento = W / Global.getSpeed(). The speed power-up sets it to W / 10.
- Player Y = shipHeight + (H/3) * valorPosicao. valorPosicao is 0.17 on iPhone and 0.09 on iPad.
- `talkingMoveAction` (when the talking-move option is on and movement is allowed): when the movement state changes, it speaks "Right", "Left" or "Stopped" through the synthesizer at rate 0.6.
- Taps: `touchesEnded` skips the cutscene if one is playing. Otherwise, if not paused and not in a menu, it calls `playerShoot`.
- Swipe up: pause, if not in a menu. Swipe down: speaks "Your life is N" at rate 0.55.
- In-game menus (game over, pause and so on): when VoiceOver is running, swipe left and right move through menuObjects, play `chageButton` and speak the item name. At the ends they play `errorButton`. A touch on an item selects and speaks it, and a double tap activates it. Without VoiceOver, a touch activates the item directly. Index 0 of menuObjects is skipped (it's probably the title).
- Speech rates used: 0.55 (most announcements) and 0.6 (movement talk). These are AVSpeechUtterance rates, where 0.5 is the iOS default.

## Recovered mechanics: physics categories and collisions

SpriteKit physics category bits:

- 0x1 is the player ship.
- 0x2 is an enemy ship.
- 0x4 is a player shot.
- 0x8 is an enemy shot.
- 0x10 is something a player shot destroys on contact, and the player removes on contact. It's probably an obstacle such as a fuel tank or rock. Still to confirm.
- 0x20 is a power-up.
- 0x40 is the "toaster", most likely an enemy laser beam. While the player touches it, damage is applied once on contact begin. It's cleared on contact end.
- 0x80 is the right swoosh field. 0x100 is the left swoosh field.
- 0x200 is a side wall.

What happens on each contact (`BaseScene::didBeginContact:`), ignored while paused:

- Player shot (4) with 0x10: both nodes stop their actions and are removed.
- Player (1) with 0x10: the 0x10 node is removed.
- Player shot (4) with enemy (2): the shot plays the arrayPower_3 animation and is removed. `enemy_hit.caf` plays (non-positional SKAction). The enemy takes Global.getShot damage. If that kills it: `destroyEnemy:` with its ship code, then `addScore:` after 0.9 seconds.
- Enemy (2) with player (1): `destroyEnemy:` and `player_hit.caf`. The player takes damage equal to the enemy's shoot damage, and if that kills the player, `endGame` runs after 1.5 seconds. Then the enemy takes damage equal to its own life, which kills it.
- Enemy shot (8) with player (1): the shot animates and is removed. If this shot isn't the same one as `lastShoot` (this guards against double hits), it becomes lastShoot, `player_hit.caf` plays, and the player takes the shooter's shoot damage. If that kills the player: allowMove is set to NO and `endGame` runs after 1.5 seconds.
- Player shot (4) with enemy shot (8): `colisaoTiro.mp3` plays and both shots animate and are removed.
- Player (1) with power-up (0x20): the power-up is removed. Then by type:
  - 1, life: speaks "Life collected!", plays `Power-Up.caf`, calls `restoreLife`.
  - 2, shield: speaks "Shield collected!", plays `Power-Up.caf`, calls `restoreShield`.
  - 3, speed: speaks "Speed collected!", plays `Power-Up.caf`, sets velocidadeMovimento to W/10, calls `startingPowerUpOfTipe: 3`.
  - 4, fast shot: sets powerUpShot to YES, speaks "Fast shooting collected!", plays `Power-Up.caf`, calls `startingPowerUpOfTipe: 4`.
  - All of these speak at rate 0.55.
- Player (1) with toaster (0x40): the player takes the toaster owner's shoot damage, and `endGame` runs after 1.5 seconds if that's fatal.
- Enemy shot (8) with the left swoosh field (0x100): `Swoosh_Left.caf` plays. With the right swoosh field (0x80): `Swoosh_Right.caf` plays. This is the near-miss whoosh.
- Player (1) with a side wall (0x200): only if shouldLateralPlayHitSound is set. If talkingMove is on, it speaks "End of Screen" at rate 0.6. It plays `bound_right.mp3` if the player x is at least W/2, otherwise `bound_left.mp3`. Then the flag is cleared. `didEndContact:` sets it again when contact with a wall ends, and clears the toaster when contact with 0x40 ends.

## Recovered mechanics: swoosh fields and side walls

- `createSwooshSoundFields`: two invisible rectangles, each shipWidth*0.7 wide and 10 high. The left one is centred at (player.x - shipW/2 - fieldW/2, player.y + shipH/2). The right one is centred at (player.x + shipW/2 + fieldW/2, player.y + shipH/2). Both are attached to the ship with fixed joints, so they move with it. Ship rotation is disabled. The left is category 0x100 and the right is 0x80, and both test contact against enemy shots (8).
- `createSideWalls`: two invisible walls, 3 wide and shipHeight tall, at x = 0 and x = W, at the player's y. Category 0x200, testing contact against the player (1).

## Recovered mechanics: shots

- Player auto-fire: `startingShootLoop` repeats forever (key "BlockShoot"): run a block, then wait Global.getTimeShot seconds. The block presumably re-enables canShoot. Confirm by reading the block at 0x64cb1.
- `playerShoot` (on tap): needs (canShoot or powerUpShot), not paused, and allowShoot. It spawns a shot sprite at (player.x, player.y * 1.2), sized (shipW*0.5, shipH*0.2), with a physics circle of radius W/30. Category 4, contact 0x12 (enemy and 0x10), collision 0xC. The shot animates its frames at 0.04 seconds per frame and moves to y = H + 20 over 1.0 second, then is removed. Then canShoot is set to NO and the ship's `soundTiroWithBullet: nil` runs.
- So a tap fires at most once per getTimeShot interval, unless fast shot is active.
- Enemy auto-fire: `SpaceShip::startShooting: t` repeats forever (key "ShootingAction"): run the shoot block, then wait t seconds.
- `SpaceShip::shoot:`: if the scene isn't active or the ship's life is 0 or less, the ship removes itself through autodestruction. If not paused, there's a 50% chance (arc4random & 1) of firing on each tick:
  - Laser ships (ship codes 3, 5, 7, 8, 15, 23, 27, 30, 42 and 100 to 102) call `laserShoot` instead, unless a laser is already active.
  - Everyone else spawns a bullet: an EnemyShoot texture, size parent_width/6, physics circle radius 5, starting at (enemy.x, enemy.y - shipH/2). It moves to y = -20 over 1.5 seconds, then is removed. Its frame animation runs at 0.8 seconds per frame. Category 8, contact 5 (player and player shot), collision 8. It's tinted with the ship colour, then `soundTiroWithBullet:` is called with the bullet.
- `manualShot` (the ship's own forced shot) is the same but uses Fireball textures, size parent_width/12, moving to y = -20 over 1.5 seconds with frames at 0.03 seconds.
- `soundTiroWithBullet:` picks the shot sound by ship code:
  - Laser ships: no shot sound here, because the laser has its own sounds.
  - 98 (the player): `PlayerGun.caf` through SKAction, non-positional.
  - 0, 21, 22 and 41: `Enemy_Shot_1.caf`.
  - Everyone else: `Enemy_Shot_2.mp3`.
  - Enemy shot sounds go through `executeSoundNamed:withFormat:andNode:`. That creates a new Aureal sound with a unique numeric key, links it to the bullet and plays it once at the bullet's position. So the shot sound travels with the bullet down the screen toward the player, panned and attenuated by Aureal.
- `executeWithoutLinkSoundNamed:withFormat:inPosition:` does the same but leaves the sound at a fixed position.

## Recovered mechanics: enemy push

- `pushSpaceShip` moves the ship by (random from -W/4 to W/4, -2*H) over a random 5 to 8 seconds. Ship codes 37 to 39 use 2 to 5 seconds instead, and codes 47 to 50 use 3 to 6 seconds. The ship also spins pi radians every 3 seconds, forever. A completion block follows (at 0x3f3fc, not read yet).

## Recovered mechanics: upgrades (Global)

Points per stat range from 0 to 5.

- getTimeShot (seconds between auto shots): 1 - 0.1 * points for points 0 to 4, and 0.5 at 5 or more.
- getShot (shot damage): points + 1, maximum 6.
- getLife: 5 * points + 5, maximum 30.
- getShield: points, maximum 5.
- getSpeed (the divisor of screen width): 50 - 5 * points, minimum 25. A lower value means faster movement.

## Recovered mechanics: damage model (`SpaceShip::inflictDamage:`)

- Damage only applies while receciveDemage is true. It's set true at creation.
- If shield > 0, the hit removes exactly 1 shield point, whatever its damage, and life is untouched. For the player (ship code 98), it speaks "Your shield is N", or "Shield Down." when the shield reaches 0.
- Otherwise life -= damage. If life is 0 or less, `destroyShip` runs and the method returns YES (killed).
- If the ship survives:
  - The first time life drops to half of max life or below, and only if VoiceOver is running, it speaks "Enemy with less than 50% health." This applies to any ship, the player included, even though the text says "Enemy". Original quirk, keep it.
  - For the player, it speaks "Your life is N". If life is exactly 1, `alarm.caf` starts repeating every 4 seconds (action key "alarme").
- `restoreLife`: +1 life up to max. For the player it speaks "Your life is N", and stops the alarm once life is above 1. `restoreShield`: +1 shield up to max shield. For the player it speaks "Your shield is N".
- All of these speak at rate 0.55.
- VoiceOver gating: several announcements only happen when `UIAccessibilityIsVoiceOverRunning()` is true. The port always runs with screen reader output through Prism, so those branches should count as running. Confirm with the user before treating it as settled.

## Recovered mechanics: destroying a ship (`SpaceShip::destroyShip`)

- Ship codes 100 to 105 also call the scene's `destroyEnemy:`. In BaseScene that's an empty method that subclasses override.
- `removeSpaceshipOnAutodestruction: NO` stops the player alarm, removes the laser emitter and laser body for laser ships, removes the life bar, the sprite and all actions.
- The engine sound is stopped immediately. Its key is the ship's soundIDEnumerator.
- A random explosion plays at the ship's last position, not linked: one third each `explosion_1.caf`, `Explosion_.mp3`, `explosion.mp3`.
- The rest is visual (explosion animation and score particles). In free mode the score particle flies toward the score label.
- For the player: canShoot is set to NO, the "BlockShoot" auto-fire loop is removed, and a death animation plays.

## Recovered mechanics: enemy spawning (`BaseScene::createEnemyWithType:`)

- The ship is created with `initEnemyOfType:inParentView:`.
- The engine sound is `ShipSounds.plist["SpaceShipSound_<code>"]`. Its extension is caf for code 43 and codes above 46 (that's `Ship_44.caf` and `sonarpedra.caf`), otherwise mp3. It's added to Aureal under the next numeric key, linked to the ship, and started with `executeForeverSoundNamed` (infinite loop). The key is stored on the ship so destroyShip can stop it.
- So every enemy is a looping engine sound that Aureal moves with it. That's how the player locates enemies.
- Power-ups (`releasePowerUpOfType:`) work the same way with a looping `beep_radar.caf` linked to the power-up node.

## Recovered mechanics: enemy table (`SpaceShip::initEnemyOfType:inParentView:`)

Each line gives the ship code, then life, score, fire interval in seconds, movement interval in seconds, and the damage the ship's shots (or the ship ramming you) deal. Laser ships are marked. Their fire interval is the gap between laser cycles, and they don't move.

- 0: life 2, score 10, fire 2.0, move 0.9, damage 1
- 1: life 3, score 12, fire 1.3, move 1.0, damage 1
- 2: life 5, score 12, fire 2.0, move 1.0, damage 1
- 3 (laser): life 30, score 25, fire 1.2, move 1.0, damage 1
- 4: life 20, score 50, fire 1.2, move 0.8, damage 3
- 5 (laser): life 80, score 55, fire 1.2, move 1.0, damage 3
- 6: life 25, score 30, fire 1.5, move 3.0, damage 5
- 7 (laser): life 7, score 25, fire 1.2, move 1.0, damage 1
- 8 (laser): life 13, score 17, fire 1.5, move 1.0, damage 1
- 9: life 12, score 35, fire 1.0, move 1.0, damage 1
- 10: life 13, score 17, fire 1.5, move 1.0, damage 1
- 11: life 15, score 40, fire 1.0, move 1.0, damage 1
- 12: life 18, score 35, fire 0.8, move 0.3, damage 2
- 13: life 46, score 55, fire 1.0, move 1.0, damage 10
- 14: life 25, score 45, fire 1.0, move 0.5, damage 5
- 15 (laser): life 50, score 58, fire 1.0, move 1.0, damage 4
- 16: life 45, score 55, fire 1.0, move 1.0, damage 12
- 17: life 35, score 50, fire 1.0, move 0.8, damage 4
- 18: life 60, score 80, fire 0.9, move 1.0, damage 6
- 19: life 65, score 70, fire 1.5, move 1.5, damage 8
- 20: life 30, score 29, fire 1.3, move 2.0, damage 3
- 21: life 32, score 75, fire 1.0, move 1.0, damage 2
- 22: life 6, score 25, fire 1.0, move 0.2, damage 2
- 23 (laser): life 35, score 34, fire 1.3, move 1.0, damage 2
- 24: life 35, score 90, fire 0.8, move 1.0, damage 3
- 25: life 90, score 175, fire 1.8, move 1.6, damage 8
- 26: life 42, score 100, fire 0.7, move 1.0, damage 3
- 27 (laser): life 70, score 110, fire 0.6, move 1.0, damage 4
- 28: life 40, score 115, fire 1.0, move 0.6, damage 2
- 29: life 55, score 120, fire 1.2, move 1.0, damage 4
- 30 (laser): life 57, score 125, fire 1.5, move 1.0, damage 4
- 31: life 60, score 135, fire 1.6, move 2.0, damage 8
- 32: life 58, score 130, fire 0.8, move 1.0, damage 6
- 33: life 63, score 135, fire 0.7, move 1.0, damage 6
- 34: life 65, score 140, fire 1.0, move 1.1, damage 4
- 35: life 70, score 150, fire 0.7, move 1.0, damage 6
- 36: life 75, score 155, fire 0.7, move 1.0, damage 5
- 37: life 1, score -100, fire 1.0, move 1.0, damage 5. Allied ship (chapter 6 escort). Destroying it costs 100 points.
- 38: life 1, score -100, fire 1.0, move 2.0, damage 7. Allied.
- 39: life 1, score -100, fire 1.0, move 3.0, damage 8. Allied.
- 40: life 15, score 18, fire 1.5, move 1.0, damage 2
- 41: life 15, score 17, fire 1.4, move 0.5, damage 1
- 42 (laser): life 19, score 20, fire 1.3, move 1.0, damage 1
- 43: life 22, score 25, fire 2.0, move 3.0, damage 4
- 44: life 80, score 270, fire 0.6, move 1.0, damage 8
- 45: life 140, score 300, fire 0.6, move 1.0, damage 12
- 46: life 1, score 5, fire 1.0, move 1.0, damage 2. A drifting object (engine sound Ship_50). Probably the chapter 1 fuel tank.
- 47: life 1, score 5, fire 1.0, move 1.0, damage 2. A rock (sound sonarpedra).
- 48: life 3, score 10, fire 1.0, move 1.0, damage 3. A rock.
- 49: life 4, score 15, fire 1.0, move 1.0, damage 4. A rock.
- 50: life 6, score 20, fire 1.0, move 1.0, damage 5. A rock.
- 100, 101, 102, 104, 105: life 30, score 1000, fire 1.0, move 1.0, damage 1. These are invisible hitbox parts of a boss (clear-colour rectangles placed at fixed spots). 100 to 102 count as laser ships.
- 103: life 50, score 1000, fire 1.0, move 1.0, damage 1. A boss part.
- The player is code 98.

Laser ship codes: 3, 5, 7, 8, 15, 23, 27, 30, 42 and 100 to 102.

Other notes:

- Sprite sizing: the texture `SpaceShips_<code>` is scaled to fit a box of W/4.3, keeping its aspect ratio. The ship node then gets scale 0.8. The hitbox comes from `setPhysicsBodySpecs` (not read yet).
- Life bars (visual only) are skipped for codes 37 to 39, 46 to 50, and 100 and up.
- Verified: the original constructor was run in a Unicorn ARM emulator for all 57 type codes (Objective-C calls stubbed, the createEnemy arguments captured), and every value matches this table. The same technique works for any other table-like function.

## Recovered mechanics: enemy entrance and behaviour

- Every enemy starts at (W/2, H + its height), just above the top of the screen.
- Normal ships: they move to a random x between shipW and W - shipW, and a random y between 0.75H and 0.9H, over 1.5 seconds with ease in-out. Then they start shooting (every fire-interval seconds) and moving, and the physics body is switched on.
- Movement (`SpaceShip::move:`), on each movement-interval tick: 50% chance to do nothing. Otherwise the ship moves to a random x between shipW/2 and W - shipW/2 and a random y between 0.7H and 0.85H, with ease in-out. The move takes the interval itself if that's 1 second or less, 1.5 seconds if it's up to 3, otherwise 2 seconds. If the scene is inactive or the ship's life is 0, the ship removes itself.
- Laser ships: they move to x = 1.8*shipW or x = W - 1.8*shipW (random side) and a random y between 0.8H and 0.85H, over 1.0 second. Then they start the laser cycle with no movement.
- Allies (37 to 39), the drifting object (46) and rocks (47 to 50): they move to a random x and y = 1.5H (off the top) over 1.5 seconds. Then the physics body is switched on and `pushSpaceShip` runs: they drift down by 2H over 5 to 8 seconds (allies 2 to 5 seconds, rocks 3 to 6 seconds) with a random sideways drift of up to W/4, spinning. They don't shoot. They hurt by ramming (enemy-with-player contact).

## Recovered mechanics: laser cycle (`SpaceShip::laserShoot`)

Sets laserAtivo and runs this sequence:

1. `Laser_Charge.caf` plays, linked to the ship (positional), and the charge particle effect is created.
2. Wait 1.0 second.
3. `Laser_Firing.mp3` plays, linked to the ship, and the effect intensifies.
4. Wait 1.5 seconds.
5. The beam's physics body is created: a rectangle W/50 wide and H tall, hanging straight down from the ship (anchor at the top centre). Category 0x40 (the "toaster"), contact with the player.
6. Wait a random 3 to 7 seconds (whole seconds).
7. The effect fades and the firing sound is stopped with the fade option (about 3 seconds). The beam is cleaned up and laserAtivo is cleared.

So 0x40 is the enemy laser beam, which hits once on contact begin. The player has about 2.5 seconds of charge and firing sound to get out of the column before the beam turns harmful.

## Recovered mechanics: power-up duration

- Speed and fast-shot power-ups last 10 seconds (the power bar shrinks to 0 over 10 seconds). Then `endPowerUpOfType:` runs.
- Fast shot (4): speaks "Fast shooting ended" and clears powerUpShot.
- Speed (3): speaks "SpeedUp ended" and restores velocidadeMovimento to W / getSpeed.

## Recovered mechanics: scoring

- `addScore:` adds the ship's score to scoreCounter.
- In stage 0 (free mode), with VoiceOver running, it speaks "Score: N." at rate 0.6 after every kill. deathCounter goes up by 1.

## Recovered mechanics: bosses (`Boss` class)

Full call traces for every boss are in `decompiled/analysis/traces/boss_NN.txt`, produced by `tools/re/trace_bosses.py`. The coordinates there assume a 320 by 568 scene. Summary:

- Created with `initBoss: code onParentScene:`. The texture is `Boss_NN` (code 1 to 10). The sprite is anchored at its centre and sized to the texture on iPhone (setScale 1 on the inner node). The sizes are large, for example Boss 1 is 481 by 417. The boss usually stops with its centre on the top edge, so it covers the top of the screen and overhangs the sides.
- Stats, read from the emulator after init:
  - 1: life 30, damage 1
  - 2: life 50, damage 2
  - 3: life 65, damage 3
  - 4: life 70, damage 4
  - 5: life 80, damage 5
  - 6: life 120, damage 4
  - 7: life 120, damage 4
  - 8: life 120, damage 1
  - 9: life 180, damage 9
  - 10: life 70, damage 4
  - All bosses have shield 0 and score 1000.
- `Boss::inflictDamage:` works like the ship version: a shield point absorbs a hit, otherwise life drops, and at 0 or below `destroyBoss` runs and it returns YES. Bosses have no announcements, life bar or alarm.
- Entrance: it starts above the screen (Boss 2 starts off to the side at (833, 406)) and moves to (W/2, H) over 5 seconds, 6 for Boss 7. Boss 6 stops at (W/2, 0.75H) instead.
- After the entrance (completion block), the physics body is set as a polygon edge loop, scaled to the sprite, with category 2 (enemy) and contact 21 (player, player shot and 0x10). Then the movement loop starts and the attack loop runs forever, one tick per interval. The interval is 1.0 second by default, 0.6 for bosses 3 and 10, 0.7 for 5, about 0.7 plus 0.6 chained for 7 and 8, and 0.8 for 9.
- Movement loops (repeat forever, coordinates relative to the current position):
  - 1: bob down 45.44 and back up, 2 seconds each.
  - 2: (+32, +56.8) in 1 second, (-64, 0) in 2, (0, -56.8) in 1, then back to (W/2, H) in 1.
  - 3: +128 in 2 seconds, -256 in 4, back to centre in 2.
  - 4 and 10: +96 in 2, -192 in 4, back in 2.
  - 5 and 8: +64 in 2, -128 in 4, back in 2.
  - 6: +160 in 2, -320 in 4, back to (W/2, 0.75H) in 2.
  - 7: +32 in 5, -64 in 6, back in 4.
  - 9: +32 in 2, (-64, +56.8) in 4, back in 2.
- Attack interval: after the entrance, the boss waits its interval and then runs its attack block, forever. The intervals are 1.0 seconds for bosses 1, 2, 4 and 6, 0.6 for 3, 7, 8 and 10, 0.7 for 5, and 0.8 for 9.
- Attack blocks: each boss has its own block (0x20958 for boss 1, 0x20c74 for boss 2, up to 0x2268c for boss 10). Each one steps through a fixed cycle of firing points, relative to the boss, using atualShootPoint. The cycles were traced with `tools/re/trace_boss_attacks.py`, and they're encoded in `nebula/game/boss.py` as ATTACKS and checked tick by tick against the original by `tests/test_bosses.py`. In outline:
  - Boss 1: every tick tries a laser from one of three points, plus a bullet from 0.15 of the width to the left or right.
  - Boss 2: bullets sweeping across five points.
  - Bosses 3, 4 and 10: bullets from three points (left, centre, right), and 4 and 10 repeat the centre.
  - Boss 5: right bullet, left bullet, a rest, then a laser.
  - Boss 6: alternately a centre bullet and a laser.
  - Boss 7: four steps including a laser. One of its bullet points is 708 points below the boss, so that bullet starts below the screen and drifts up to y = -20 out of earshot. Original oddity, kept.
  - Boss 8: right bullet, laser, left bullet, left bullet.
  - Boss 9: a double bullet on the left, a coin flip (getRandomNumberBetween(0, 100): laser when even, otherwise a centre bullet), then a double bullet on the right.
- Boss bullets: a Fireball, size W/12, physics circle radius 5, starting at the firing point and moving to y = -20 over 1.5 seconds. Sound `Enemy_Shot_1.caf`, linked and positional.
- Boss lasers: the same charge, firing and beam sequence as a laser ship, but the beam is a child of the boss. It sits at (point.x, point.y - h/2) relative to the boss centre, W/50 by H (6.4 points wide, not rounded like ships), and moves with the boss. It holds for a random 3 to 7 whole seconds: laserTime is never assigned anywhere, so it's always 0 and the random duration is always used. Then it retreats to y = h over 3 seconds while the firing sound fades.
- `destroyBoss`: it plays `explosion_1.caf`, waits 0.3 seconds, plays `Explosion_.mp3`, waits 0.2 seconds, plays `explosion.mp3` (all non-positional). It removes the physics body, plays the explosion animation, then a completion block runs (not traced yet, probably the scene's boss-defeated hook).
- Bosses have no engine sound. They're heard only through their bullets, lasers and explosions. Boss getShipCode returns 100, which is what destroyEnemy: receives.

## Open questions

- Input on Windows: steering is decided (left and right arrow keys, see DEVIATIONS.md). Still open: the fixed accelX magnitude, plus the keys for firing (tap), pause (swipe up), speaking life (swipe down) and menu navigation (swipes and double tap).
- What 0x10 is. Find where that category bit is assigned.
- `setPhysicsBodySpecs` (hitbox sizes) and the texture sizes from the atlas plist, since sizes affect collisions.
- Boss parts 100 to 105: only used by the possibly dead chapter 6 stage4Loop (see CHAPTERS.md). Confirm nothing else creates them.
- Chapter scripts are in `docs/CHAPTERS.md`, and the chapters are ported in `nebula/game/chapters.py` with emulator-checked kill rules. didBeginStage, didWinStage and didFailStage only send analytics. defaultVictoriousAnimation: the ship waits 1 second, flies to (W/2, H + 100) over 3, waits 1 and shrinks over 2, then endGameVictorious, which waits 2 seconds and opens missionComplete. The map generator is visual only: its fuel tanks, debris and background ships have no physics and no sound.
- Free mode and tutorial are in `docs/MODES.md`, with a few items to confirm listed there.
- Menus, cutscenes, startup, Hangar and saving are in `docs/MENUS.md`. Versus mode is still unstudied.
- Versus mode over Game Center: studied on 2026-11-19, see "Versus mode" below. Not ported yet.
- The scene size to use on Windows. The original uses device points (320 wide on iPhone). All the formulas scale with W and H, so the port can pick one iPhone resolution (320x568 is the likely choice) and keep it.
- Laser audibility (raised by the user on 2026-11-18; resolved by the deviation "Attack sounds cover their danger zone"): a laser's charge and firing sounds come from the laser ship, a single point, and the beam falls straight down from it. The beam is only W/50 (6.4 points) wide, but the player's hitbox is an octagon w wide (w = W/4.5) on a node scaled 1.5, about 107 points. So the beam hits whenever the laser ship is within about 56 points of the player's centre, roughly a third of the screen. Aureal's cube-root pan makes small offsets sound large: about 50% panned at 20 points and about 70% at 56 points, still inside the danger zone. A laser that sounds clearly to one side can therefore still hit. Warning time is 2.5 seconds (1 s charge, 1.5 s firing sound); clearing 56 points takes about 0.5 s with an arrow, 0.25 s with Shift. Options if this is revisited, each a deviation: pan the laser sounds linearly, or add a cue when a charging laser is lined up with the player.

## Next step

Continue the study through the open questions above, in roughly that order. Enemies and the damage model come first, since every level depends on them.

## Implementation notes

- SpriteKit timing modes (easeIn, easeOut, easeInEaseOut, used for enemy and boss moves) aren't documented by Apple. `nebula/engine/actions.py` uses the usual sine curves: 1 - cos(t*pi/2), sin(t*pi/2) and (1 - cos(t*pi))/2. They only affect positions in the middle of a move, so their effect on audio is a slightly different pan and volume path during movement.
- Possible future input: a DualSense (or other controller) accelerometer could feed accelX directly, which would be closer to the original tilt than the arrow keys. SDL2 exposes controller sensors, but pygame doesn't, so it needs SDL2 access beyond pygame. Raised by the user on 2026-11-17; built on 2026-11-18 (DEVIATIONS.md, "Game controllers"). A DualSense lying flat reads about 10.1 m/s2 on SDL's y axis.

## Images

- `tools/extract_images.py` copies the iPhone images, the `gameTextures` atlas and `HACKED_Title.ttf` into `images/`, and decodes the asset catalog into `images/catalog/`.
- `Assets.car` is a BOM store (`tools/re/car.py`). Its 17 bitmaps are BGRA with premultiplied alpha, compressed with LZVN (`tools/re/lzvn.py`), either in one block or as KCBC row chunks. Facets: FotoPadrao, backbar, base_score, crack1, enemyLife, lifeBar, lifeEnemy, mais (stored as the rendition "as.png"), mais_block, nebulaMenu1 (the 640 by 1136 main menu background with the NEBULA title), nebulaMenu1_3.5 (the 3.5 inch version), nebulaMenu_iPad, phones (the headphones picture), powerUpBar, shieldBar, ship (the Hangar ship), shot.
- The `gameTextures` atlas has 7 sheets and 310 textures. Entries give textureRect, spriteOffset, spriteSourceSize and textureRotated (rotated entries are stored turned 90 degrees). The `tch_` atlas and `tch_` images are the lower quality set used on iPod touch and older iPads; the port uses the full set.
- The 18 `.sks` files are SpriteKit particle emitters (keyed archives).
- Most loose bundle pngs (165 of 169) are Apple CgBI pngs; `tools/extract_images.py` converts them.
- Particle emitters: `tools/extract_emitters.py` converts the 18 `.sks` files to `data/emitters.json`. Uses traced so far: the laser (one of MyParticle, MyParticle1 to 3, picked with `arc4random() & 3` inside laserShoot's sequence, so that draw is part of the game's random sequence), the score burst on a kill (score.sks), the starfield (starField.sks), ships 37 to 39 (ShipNNFlyParticle) and the asteroids.
- Particle textures are drawn upright, as their images are. The chapter 6 background ship emitters set a particle rotation of pi/2, so their ships show lying on their side and stretched by the emitter's xScale and yScale (which apply after each particle's rotation). Whether the original looked like that couldn't be checked; a theory that SpriteKit drew rotated atlas textures as stored was ruled out, since it would also turn the starfield's streaks sideways.
- MapGenerator (`nebula/game/map_generator.py`) draws from the game's arc4random and arc4random_uniform when it places items, as the original did. Recipes for free mode and all 36 chapter stages were traced with the emulator; see the module docstring.
- destroyShip draws `arc4random() & 1` after the explosion sound to pick Explosion_1 (Explosion02 frames) or Explosion_2 (Explosion03 frames). The port makes the same draw, so the game's random sequence stays in step. Enemies (not the player, code 98) also send off the score.sks sparkle, which flies to (W/2, 0.95 H).

## App Store listing

The original listing (App Store id 874292053, bundle com.CiladaGames.Nebula), as supplied by the user on 2026-11-18 from its copy on App Pure (iphone.apkpure.com). Apple's page has been removed. Verbatim, including its typos:

Nebula is a spaceship battle arcade game that will provide you a new experience. With many features such as 3D audio, device movements and accessibility for the visually impaired.

"Nebula is a fantastic game. It is both challenging and addicting. It is a must download."
- Liam Erven

FEATURES:
- Gaming Modes: Campaign, Free and Multiplayer.
- 3D audio*, allowing play without vision.
- 48 enemy spaceships
- Campaign with storyline
- Upgradeable spaceship.
- Detailed tutorials
- 9 chapters and 36 levels

*For a better experience, use your headphones.

STORY:
During the last great inter-galactic war, the Spacial Defense Force created the Nebula project, an army of defense and attack composed by 2000 spaceships. The project got it's name due to the difficult the pilots had to perform combats in space, as they face huge nebulas that limited their vision and scrambled their systems. Because of this, engineers have invested heavily to develop a technology that would allow us to hear other ships and unknown objects.

Version 1.3's What's New, from a mirror (soft112), dated 2016-12-05: "Major bug-fixes throughout the game." "Upgraded device compatibility." "Voice-Over bug-fixes." "Full campaign now included in the game, no more in-app purchases!"

## Versus mode (studied 2026-11-19, from decompiled.c)

Two players, peer to peer over a Game Center match. Game Center only did three things: named the players (alias and photo), matched them (GKMatchmakerViewController: auto-match or invite friends; invite message "Venha jogar NEBULA comigo!"; invites accepted from outside the game start it too, MainMenuViewController player:didAcceptInvite:), and carried the game's own messages between the two phones (GKMatch sendDataToAllPlayers, reliable mode). There is no host: both phones run the same VersusScene and trust each other.

Messages (raw C structs, first int is the type):
- 3, specs, 16 bytes: device type, lifePoints, shieldPoints (Hangar upgrades). Sent by matchStarted. The receiver builds the opponent's ship with life = 5 + 5 * lifePoints (30 at 5 or more) and shield = min(shieldPoints, 5), answers with 4, and starts the 5 second MAX_WAITING_TIME watchdog.
- 4, 4 bytes: specs received. Starts the countdown timer (regressiveCount:).
- 0, move, 20 bytes: x, own life, the opponent's life and shield as the sender sees them. Sent by a repeating timer (sendMove:) while the round is live. The receiver moves the opponent's ship to x (scaled between iPhone and iPad screen widths), and applies damage wherever the sender reports less life or shield than it has (both views converge on the lower values).
- 1, shot, 4 bytes: the opponent fired. The receiver spawns the opponent's bullet (arrayPower_2 frames) under the opponent's ship, falling towards the player, with soundTiroWithBullet: as for enemy shots.
- 6, 4 bytes: round over, sent by teste. A receiver not already waiting stops moving and shooting and starts the end timer.

Round flow: the lobby plays LinoRise_ChannelIntroPompeii.mp3 at half volume while matchmaking (searchCanceled goes back to the menu). matchStarted starts the nebula map (MapGenerator initVersusMapInScene: / beginNebulaGenerationForVersus), stops the lobby music and sends specs. The countdown label (Futura 60, "3") counts down with the game voice speaking each number, then versus_Inicio ("Start!"); gameStarter becomes YES and moving and shooting are allowed. The opponent's ship carries SpaceShipSound as a positional loop (enemyShipSound), so the player hears where it is. Hits: didBeginContact: plays enemy_hit.caf or player_hit.caf with the explosion frames and inflicts damage locally. When a life reaches 0, the end timer leads to screenBeforeRestart: a black box (boxFinalMultiplayer, or boxMultiplayerEmpate for a draw) with the winner's Game Center photo (FotoPadrao.png as fallback) and alias, versus_Vitoria ("Winner. The game will restart automatically.") or versus_Empate ("Draw") spoken, and a menu with game_selecionar; then restartGame rebuilds both ships and calls matchStarted again. A player disconnecting (match:player:didChangeState:) or a failed send ends the match and returns to the menu.

Still to recover from the machine code (doubles the decompiler drops): the sendMove: interval, the countdown and end timer intervals, and the restart delay.
