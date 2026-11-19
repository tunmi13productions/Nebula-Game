# Deviations from the original

Each entry is a settled decision. Don't change a deviated behaviour unless the user brings it up.

## Steering uses the left and right arrow keys instead of tilt

- Original: the ship is steered by tilting the device. The accelerometer is sampled every 0.2 seconds. acceleration.x values between -0.04 and 0.04 count as zero. Each frame the ship moves by accelX * (W / Global.getSpeed()), and the movement state changes (left, right, stopped) when accelX goes past 0.05 or -0.05.
- Changed: holding the right arrow key feeds a fixed positive accelX and holding the left arrow key feeds the same value negated. With neither held, accelX is 0. Everything downstream of accelX (movement state, the move and stabilise calls, talking movement, clamping, the listener update) stays as in the original.
- Reason: a Windows PC has no accelerometer. Decided by the user on 2026-11-17.
- Tilt value: a held arrow key reads as acceleration.x = 0.3 (or -0.3). That's a moderate tilt, roughly 115 points per second with no speed upgrades. Chosen by the user after playtesting on 2026-11-17. It can still be overridden with "tilt" in the settings file.
- Faster steering: holding Shift with an arrow key reads as acceleration.x = 0.6 (or -0.6), twice the normal tilt, like tilting the device further. It can be changed with "fast_tilt" in the settings file. Added at the user's request on 2026-11-18.

## VoiceOver-gated behaviour always counts as VoiceOver running

- Original: some announcements and controls only happen when `UIAccessibilityIsVoiceOverRunning()` is true. These include the half-health line, the free-mode score after each kill, and swipe navigation with spoken items in the in-game menus. Without VoiceOver, menu items activate on a single touch.
- Changed: the port always takes the VoiceOver-running branch, and speaks through Prism.
- Reason: the port always uses screen reader output, so it matches the original as played with VoiceOver. Decided by the user on 2026-11-17.

## The full campaign is always unlocked, and the store is removed

- Original: chapters 2 to 9 needed an in-app purchase (`purchased_Campaing`). Without it, the campaign selector showed a lock overlay and opened `CompraCampanhaViewController` ("Full campaing not purchased", with Buy, Restore and back) through StoreKit.
- Changed: the purchase flag always counts as bought. The purchase screen, its texts and StoreKit are removed. Level-by-level progress unlocking (lastChapter and lastLevel) is unchanged.
- Reason: Apple in-app purchases don't exist on Windows. Decided by the user on 2026-11-17.

## Versus mode is left out for now

- Original: the main menu had a Multiplayer item that started `VersusScene`, a two-player match over Game Center (GameKitHelper, invites, "Start!", "Winner. The game will restart automatically.", "Draw"). It needed a Game Center login.
- Changed: the Multiplayer item and versus mode aren't ported.
- Reason: Game Center isn't available on Windows. Decided by the user on 2026-11-17, with the option to revisit later (for example as a local network mode) once the rest of the game works.

## Game Center leaderboard and GameAnalytics are removed

- Original: free mode reported each final score to the Game Center leaderboard "ModoLivre". The game also sent GameAnalytics events (stage begin, win and fail, plus SDK telemetry).
- Changed: neither exists in the port. The local best score (`bestScore`) is still saved and announced as in the original.
- Reason: Game Center isn't available on Windows. Analytics had no gameplay effect and would send player data to a third party.

## Missing English strings use the Portuguese meaning

- Original: these keys exist only in the Portuguese Localizable.strings, so in English the game showed and spoke the raw key:
  - `pause` (Portuguese "Jogo Pausado")
  - `cap_Block` ("Bloqueado")
  - `lbl_life_points_button`, `lbl_shield_points_button`, `lbl_speed_points_button`, `lbl_atkSpeed_points_button`, `lbl_power_points_button` (for example "Vida, %ld pontos. %d pontos disponíveis. Adicionar pontos.")
- Changed: English uses equivalent text:
  - `pause`: "Game paused"
  - `cap_Block`: "Locked"
  - `lbl_life_points_button`: "Life, %ld points. %d available points. Add points."
  - `lbl_shield_points_button`: "Shield, %ld points. %d available points. Add points."
  - `lbl_speed_points_button`: "Ship Speed, %ld points. %d available points. Add points."
  - `lbl_atkSpeed_points_button`: "Attack speed, %ld points. %d available points. Add points."
  - `lbl_power_points_button`: "Power shot, %ld points. %d available points. Add points."
  - The stat names follow the existing English `lbl_*_points` strings. Portuguese is unchanged.
- Reason: raw keys are meaningless to a listener. Decided by the user on 2026-11-17.

## Chapter title cards are spoken

- Original: each chapter intro cutscene starts with a title card, "Chapter" plus a Roman numeral and the chapter title (`chapterNNumber`, `capN_title`), shown while `Deep_Impact_3.mp3` plays. It was visual only and never spoken, even with VoiceOver.
- Changed: the title card text is also spoken through Prism when it appears. Timing and sound are unchanged.
- Reason: otherwise blind players never learn the chapter name at that point. Decided by the user on 2026-11-17.

## Touch gestures are mapped to keys

- Original: tap to fire (and to skip a cutscene), swipe up to pause, swipe down to hear your life. In menus with VoiceOver: swipe left and right to move between items, double tap to activate.
- Changed:
  - Space fires.
  - Escape opens the pause menu.
  - L speaks your life.
  - In menus, the up and down arrows move between items (with the same change and error sounds), Enter activates (with the accept sound), and Escape goes back.
  - Enter or Space skips a cutscene.
  - In the campaign selector, the up and down arrows move between items (the one-finger swipes), the right and left arrows go to the next and previous chapter (swipe left and swipe right), Enter activates and Escape is swipe up.
  - The UIKit screens (main menu, tutorial selection, Hangar, About) are read by the screen reader through Prism. VoiceOver's own navigation sounds have no counterpart.
- Reason: a PC has no touch screen. Decided by the user on 2026-11-17.

## Language override file

- Original: the language follows the device setting. Portuguese on a Portuguese device, otherwise English.
- Changed: the port follows the Windows display language the same way. It also reads an optional settings file that can force English or Portuguese.
- Reason: Windows players may use one language for the system and want the other for the game. Decided by the user on 2026-11-17.

## Game speech uses a Windows OneCore voice, and accessibility labels go to the screen reader

- Original: the game's own speech (I.C.A.R.U.S. lines, status lines like "Your life is 5", in-game SpriteKit menus, the countdown) went through AVSpeechSynthesizer, a text-to-speech voice separate from VoiceOver. It requested the English "Alex" voice, which most devices didn't have installed, so they fell back to the system voice for the device language. Rates were AVSpeechUtterance rates (0.55 and 0.6 against a default of 0.5). UIKit buttons and labels (main menu, Hangar, tutorial selection, info) were read by VoiceOver.
- Changed: the same split is kept. Game speech is rendered by a Windows OneCore voice through Prism (SAPI if OneCore isn't available), into memory, and played through the game's own audio output, centred. The voice is the first one matching the game language. Rates are passed through one to one, since Prism also uses a 0 to 1 scale with 0.5 as normal. UIKit-style labels go to the user's screen reader through Prism.
- Reason: Prism can't report when NVDA finishes speaking, and the game's scripts depend on that moment (spawns after I.C.A.R.U.S. finishes, for example). Rendering to memory gives the exact end of each line. Decided by the user on 2026-11-17.
- Pauses: AVSpeechSynthesizer paused clearly at punctuation, and the OneCore voice barely does. So the game voice renders each clause on its own and adds silence after it: 0.25 seconds after a comma, 0.3 after a colon or semicolon, 0.45 after a full stop, exclamation or question mark. The text itself is unchanged. Added at the user's request on 2026-11-18, after the headphones notice and the score were heard as run-on sentences.
- macOS and Linux: the engines tried are OneCore, SAPI, AVSpeech (macOS), Spiel and Speech Dispatcher (Linux), in that order, taking the first that can render to memory. If none can, the first that works speaks the line live, and the game waits for an estimate of its length (15 characters a second at rate 0.5) instead of its exact end; the speech volume setting doesn't reach a live engine. Added on 2026-11-18 for the macOS and Linux builds.
- Note: this machine has English OneCore voices only (David, Zira, Mark). Playing in Portuguese needs a Portuguese Windows voice installed, otherwise Portuguese text is read by an English voice.

## Chapter 7 stage 1 softlock is fixed

- Original: in chapter 7 stage 1 (Search), when the last medium ship (code 34) in the scene died with fewer than 5 mediums spawned, a new medium spawned only if the player's life was above 4, plus a life power-up when 4 mediums had spawned. With life 4 or less, only a life power-up dropped and no medium spawned. Small ships spawn a medium only once, so the medium count could stay below 4 forever and the stage could never be won. With no life upgrades the maximum life is 5, so a single hit before that kill was enough. The check reads "life < 5 and medium > 4", which can never be true inside a branch that already requires fewer than 5 mediums, so it was most likely a mistake.
- Changed: the medium always respawns. When the player's life is 4 or less, the life power-up still drops as before, and at full life the 4th medium still drops one. Everything else in the stage is unchanged.
- Reason: the original could leave the player stuck in an unwinnable stage with no way out except leaving. Decided by the user on 2026-11-17.

## The About screen's contact buttons are removed, and its credit links open in the browser

- Original: the About screen had OUR PAGE, which opened http://www.graycompany.com.br in Safari, and SEND EMAIL, which opened the in-app mail composer (MFMailComposeViewController) to contato@graycompany.com.br with the subject "Gray Co. - Nebula" and was disabled when the device couldn't send mail. The credit links (FreeSFX, OpenGameArt, SoundJay, MillionthVector) opened their sites in Safari.
- Changed: OUR PAGE and SEND EMAIL are removed. The credit links open in the default browser.
- Reason: Gray Company no longer exists; its site is down and its address no longer works, so the buttons would lead nowhere. Windows has no Safari, so the default browser stands in for it. The contact buttons were first ported as a mailto link and a browser link (decided on 2026-11-18), then removed at the user's request on 2026-11-18.

## Garbled characters in the English About screen are restored

- Original: the English build shows U+FFFD (the replacement character) in "Márcia Campos", "Raí Carvalho" and the copyright sign of "GRAY COMPANY © All Rights Reserved", because the source files were saved in a legacy encoding.
- Changed: the characters are restored as the Portuguese strings have them: Márcia, Raí and ©.
- Reason: a screen reader would read the replacement character aloud or skip it, garbling the names. Decided by the user on 2026-11-18.

## Spoken menu items can be interrupted

- Original: in the campaign selector, moving to an item spoke it with the game voice and ignored all input (swipes, chapter changes, double tap, swipe up) until the line had finished (the swiping flag, cleared by the speech completion). The in-game menus (pause, game over, mission complete, tutorial complete) speak their items without locking, and their speech can't be stopped.
- Changed: in the campaign selector, pressing a navigation key (the arrows, Enter or Escape) while an item is being read cuts the line off and acts at once. The same key during the one-second chapter slide finishes the slide at once (without reading the chapter) and then acts, and the 0.2 second hold after the end-of-list sound ends early. In the original all of these swallowed the key, which made Back feel unreliable. Once Back is under way (it says "Back", after half a second when activated, then leaves), further keys are ignored; in the original each further press restarted the wait, so pressing again kept postponing the exit. Control silences the line and unlocks input. In the in-game menus, Control silences the game voice. During play Control does nothing, because the level scripts wait for their spoken lines to finish.
- Reason: waiting for every item to be read in full made moving through chapters and levels slow, and keys pressed during the locks were lost. Requested by the user on 2026-11-18.

## Attack sounds cover their danger zone

- Original: enemy attack sounds were single points. A laser's charge and firing sounds (Laser_Charge, Laser_Firing) were linked to the laser ship, and a bullet's shot sound (Enemy_Shot_1, Enemy_Shot_2) to the bullet, all panned with Aureal's cube-root curve. But a beam or a falling bullet hits the player anywhere its column comes within the player's hitbox half-width (w / 2 at node scale 1.5) plus its own half-width: about 56 points for a beam (W / 100) and 58 for a bullet (radius 5), at 320 points wide. Small offsets pan strongly (about 50% at 20 points, 70% at 56), so an attack that sounded clearly to one side could still hit.
- Changed: these sounds are heard from the attack's column clamped to a zone of a quarter of the player's width (w / 4 at node scale 1.5) plus the attack's half-width, times 1.5: about 45 points either side for a beam and 47 for a bullet, a little inside the real hit range. While the player is inside the zone they sound straight ahead, like standing in front of a machine; outside it they sit at the distance past the zone's edge, so they only start to pan once the player is clear. Height, volume falloff and everything else are unchanged. This applies to laser ships, boss lasers (whose column is the gun's offset from the boss), enemy bullets and boss bullets. The 1.5 factor can be changed with "danger_zone" in the settings file.
- Reason: by ear the original's danger zones couldn't be judged, so players were hit while the attack sounded off to the side. Suggested by the user on 2026-11-18 for "the shooting sound", after the laser audibility question in NOTES.md; first applied to lasers only, then to bullets too after the user was hit by bullets in chapter 1 level 2. Tuned by ear by the user: the exact hit range first felt too narrow, so the factor became 1.5; then a zone built on half the player's width felt too wide, and the user settled on a quarter of it.

## Settings screen

- Original: there was no settings screen. Tilt sensitivity, volume and speech rate came from the device itself (how far it was tilted, the volume buttons, and the fixed rates the game passed to its speech synthesizer). The main menu had five buttons, ending with About.
- Changed: a settings screen, called Systems (Sistemas in Portuguese), is added. It takes the place of the main menu's Multiplayer button, which the port leaves out with versus mode: SYSTEMS is painted over MULTIPLAYER on the right door picture in the game's own orange letter pictures (images/rightDoorSystems_en_4.png and rightDoorSystems_4.png, built by tools/make_systems_door.py), and the item is read fourth, after Tutorial, where Multiplayer stood. F1 from the main menu also opens it. Up and down move between options; left and right change the focused one, and the new value is spoken. Options: steering speed (tilt for an arrow key, 0.1 to 1.0, default 0.3), fast steering speed (with Shift, default 0.6), danger zone width (default 1.5), sound, music and speech volumes (0 to 100%, default 100%), speech rate (a multiple of the original rates, 0.5 to 1.8, default 1), language (follow Windows, English or Portuguese, applied after a restart) and window size (1x to 3x, default 1.5x). Changes are saved to settings.json at once and take effect immediately except for the language. The labels, and a short explanation of each option spoken when it's focused, are the port's own English and Portuguese text. The screen draws only its own text on black. The sub screens' doors use the same changed right door, so the doors stay consistent.
- Reason: keyboard steering has no physical tilt, and volume and speech rate had no in-game control on Windows; editing settings.json by hand is not reasonable for players. Requested by the user on 2026-11-18. The defaults keep the original's behaviour.

## Home and End in menus

- Original: VoiceOver itself let the player jump to the first or last element on screen with a four-finger tap near the top or bottom of the screen. On the interface screens (main menu, tutorial selection, Hangar, About) that reached the first and last button. The in-game menus (pause, end of level, free mode results) and the campaign selector were not ordinary VoiceOver elements: the game read its own swipes there and moved one item at a time, so a four-finger tap had nothing in them to jump to.
- Changed: Home and End stand for VoiceOver's four-finger taps, the way the arrows stand for swipes, so on the interface screens (and the Systems screen) they jump to the first and last element as VoiceOver did. The same keys also jump in the in-game menus and the campaign selector (Home to the chapter name, End to the last level), which the original couldn't do; there the jump plays the change sound, or the error sound when already there, as moving past either end does.
- Reason: on the interface screens it reproduces a VoiceOver gesture the original's players had. In the game's own menus it is a convenience, so the same keys work everywhere. Requested by the user on 2026-11-18; the VoiceOver gesture pointed out by the user the same day.

## Game controllers

- Original: the game was played on the phone: tilting it steered (the accelerometer's acceleration.x, read every 0.2 seconds), taps and swipes did the rest, and nothing vibrated.
- Changed: game controllers work alongside the keyboard (nebula/controller). The first pad attached is the one read, and connecting or disconnecting one is announced through the screen reader.
  - Buttons stand for keys: the D-pad and left stick for the arrows (sideways held, for steering), Cross or A for Enter in menus and Space in play (fire, skip a cutscene), Circle or B for Escape in menus, Options or Start for Escape in play (pause), Triangle or Y for L (speak life), and L1 and R1 for Home and End.
  - A pad with a motion sensor (a DualSense, DualShock 4 or Switch Pro pad) steers by being rolled left and right: its roll becomes acceleration.x, as the phone's tilt did, through the same 0.2 second sampling and dead zone, so a small roll drifts and a large one is fast. Rolling the pad fully onto its side is a tilt of 1, scaled by the controller tilt sensitivity setting. A held steering key or button wins over the roll. The roll is read through SDL's sensor calls, which pygame doesn't wrap (the motion module comes from Sixth Sense Reborn, MIT License, the same authors).
  - The pad vibrates: a short buzz on both motors when the player is hit (shield or life), a long strong buzz when the player explodes, a small pulse on the light motor for a power-up, and the left (low) or right (high) motor when the ship arrives at that edge of the screen.
  - The Systems screen has controller tilt steering on or off, controller tilt sensitivity, and controller vibration on or off. Shaking the pad does nothing.
- Reason: a pad's motion sensor is the closest Windows has to the phone's tilt, and vibration gives a sense of touch the keyboard can't. Requested by the user on 2026-11-18, with the vibration patterns chosen by the user.
