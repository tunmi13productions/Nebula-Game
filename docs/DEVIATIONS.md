# Deviations from the original

Each entry is a settled decision. Don't change a deviated behaviour unless the user brings it up.

## Steering uses the left and right arrow keys instead of tilt

- Original: the ship is steered by tilting the device. The accelerometer is sampled every 0.2 seconds. acceleration.x values between -0.04 and 0.04 count as zero. Each frame the ship moves by accelX * (W / Global.getSpeed()), and the movement state changes (left, right, stopped) when accelX goes past 0.05 or -0.05.
- Changed: holding the right arrow key feeds a fixed positive accelX and holding the left arrow key feeds the same value negated. With neither held, accelX is 0. Everything downstream of accelX (movement state, the move and stabilise calls, talking movement, clamping, the listener update) stays as in the original.
- Reason: a Windows PC has no accelerometer. Decided by the user on 2026-11-17.
- Open detail: the fixed accelX magnitude isn't chosen yet. It has to be above 0.05 so the movement state changes. It gets tuned during testing and recorded here once settled.

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
- Reason: a PC has no touch screen. Decided by the user on 2026-11-17.

## Language override file

- Original: the language follows the device setting. Portuguese on a Portuguese device, otherwise English.
- Changed: the port follows the Windows display language the same way. It also reads an optional settings file that can force English or Portuguese.
- Reason: Windows players may use one language for the system and want the other for the game. Decided by the user on 2026-11-17.
