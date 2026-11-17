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
- Campaign: 9 chapters with 4 levels each. Chapter 1 is free. The rest need the "full campaign" purchase.
- Chapter titles: 1 Refueling, 2 Direction, 3 Hyperdrive, 4 Home, 5 Burning, 6 Exodus, 7 Hope, 8 Revenge, 9 Pegasus. Level names are in the `capN_lvlM` strings.
- Tutorial: 6 sections, Movement, Enemies, Attack, Battle, Basic and Special (the menu order still needs checking against the code). Each step is a narrated mp3 `tut_X.Y`.
- Free mode is endless with a score and a best score.
- The upgrade screen spends available points on Life, Shield, Power shot, Attack speed and Ship speed.
- On launch, the intro shows "PUT YOUR HEADPHONES FOR A BETTER EXPERIENCE" and plays thunder on the right ("Thunder at the right side").

## Localization

- Two languages: English (`Base.lproj`) and Portuguese (`pt.lproj`). The Localizable.strings files are in a legacy encoding, not UTF-8.
- Every narrated mp3 has a Portuguese version (`name.mp3`) and an English version (`name_en.mp3`). The strings table maps each key to the file for that language.
- Some UI images are localized the same way, for example `sair.png` and `sair_en.png`.
- The Portuguese table has keys the English one lacks: `lbl_*_points_button`, `cap_Block`, `pause`. That may cause English fallbacks in the original. Check how the code handles it.
- Known quirk: in both languages `tut_6.2` points to the `tut_6.0` audio file. That's an original bug, reproduce it unless told otherwise.

## Audio assets

- 207 audio files: 191 mp3 and 16 caf (PCM 16-bit). Full inventory with format, channels and duration: `decompiled/analysis/audio_inventory.txt`. All of them decode with soundfile (libsndfile).
- Ship engine loops: `Ship_1` to `Ship_50` plus extras. `ShipSounds.plist` maps `SpaceShipSound_N` (N from 0 to 50) to a sound file. Several map to `sonarpedra` (a rock sonar) and some are reused.
- Effects: shots, lasers, explosions, hits, power-up, swooshes left and right, screen boundaries left and right (`bound_left`, `bound_right`), radar beep, alarm, closing doors, warp.
- Music: `menuSound.mp3`, `Lino Rise - Channel Intro Pompeii.mp3`, `endingSound.mp3`, `Deep_Impact_3.mp3`.
- Missing: `intro_tut_en.mp3` and `tut_intro.mp3` are referenced by the `intro_tut` string but aren't in the bundle. `Impact.ttf` is listed as an app font but is also missing.

## Visual assets

- 226 png and 65 jpg, plus `Assets.car` (compiled asset catalog), two texture atlases (`gameTextures`, and `tch_gameTextures` for lower-end devices), 18 SpriteKit particle files (`.sks`) and the storyboards (compiled nibs for iPhone and iPad).
- The font `HACKED_Title.ttf` and a bitmap alphabet (`Alfabeto_X.png`, `AlfabetoAct_X.png`) are used for menu text.

## Decompilation setup

- Ghidra 12.2 headless, run with JDK 25. Pseudocode for all 1692 functions is in `decompiled/analysis/decompiled.c`, with real Objective-C method names (for example `Aureal::getNewVolume:`).
- Ghidra mangles floating point on this armv7 build because doubles are passed in integer register pairs. For any math, read the Thumb disassembly instead. The helper scripts used for that (Mach-O string dump, ObjC class dump, Thumb disassembler with stub and literal resolution) were kept in the session scratchpad. They're small and easy to rewrite.
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

## Open questions

- Input on Windows: the original steers by tilt and shoots by tap, with swipes for pause and life. A keyboard mapping will be a deviation and needs a decision with the user. Arrow keys could feed a fixed accelX value, but which value, and should holding a key ramp it?
- What 0x10 and 0x40 really are. Find where those category bits are assigned.
- Enemy table: `SpaceShip::initEnemyOfType:inParentView:` and `createEnemyWithLife:withScore:withShootingTime:andMovmentTime:inParentView:`. That gives life, score, fire rate and movement per ship code, and the mapping to engine sounds through ShipSounds.plist.
- Laser behaviour (`laserShoot`, the boss laser, the Laser_Charge and Laser_Firing sounds).
- Boss behaviour per chapter (`Boss` class).
- Per-chapter level scripts: `ChapterNScene` and `didBeginStage:onChapter:onMode:`, spawn timing, I.C.A.R.U.S. lines, win conditions.
- Free mode difficulty curve (`nivel_FreeMode`), and power-up spawn timing (`timeToNextPoweUp`, `timeBetweenPowerUps`).
- Tutorial script (`TutorialScene`), cutscene timing (`CutScene`), menus and view controllers, intro sequence, save data.
- How the enemy engine sound is attached (`createEnemyWithType:` and `SpaceShipSound_%ld`) and how `beep_radar` and `alarm` are used.
- Damage model: shield versus life in `inflictDamage:`, plus the half-health announcement and the "Shield down" line.
- Versus mode over Game Center: decide later how or whether to port it.
- The scene size to use on Windows. The original uses device points (320 wide on iPhone). All the formulas scale with W and H, so the port can pick one iPhone resolution (320x568 is the likely choice) and keep it.

## Next step

Continue the study through the open questions above, in roughly that order. Enemies and the damage model come first, since every level depends on them.
