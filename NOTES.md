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

## Open questions

- Exact input scheme: touch gestures, swipes ("SwipingLeft"), tilt through CoreMotion?
- Exact Aureal math: volume and pan curves, update rate, max distance values.
- Enemy stats, timings, spawn patterns per level, boss behavior, damage numbers.
- What VoiceOver-specific handling exists (button labels like "Continue, button" suggest the game spoke its own UI labels).
- Versus mode over Game Center: decide later how or whether to port it.

## Next step

Decompile the executable into readable pseudocode to answer the questions above.
