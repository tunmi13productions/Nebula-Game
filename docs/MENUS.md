# Menus, cutscenes, startup and saving

Recovered from the view controllers, `CampaignScene`, `CutScene`, `BaseScene` menus and `Global`. Text in quotes is the English Localizable.strings value. The key is given in brackets where that's useful. Everything here was built for VoiceOver users: UIKit buttons carry accessibility labels, and the SpriteKit menus speak their items themselves.

## Startup (`IntroViewController`)

1. Headphones notice (`avisoDosFones`): it shows "PUT YOUR HEADPHONES" and "FOR A BETTER EXPERIENCE" with a headphones image. With VoiceOver running, it speaks "%@ %@, %@" built from `sound_1`, `sound_2` and `sound_3`, which reads "PUT YOUR HEADPHONES FOR A BETTER EXPERIENCE., Thunder at the right side.". `thunder.mp3` plays (the file is silent on the left channel, so it's heard on the right only). The notice stays about 5 seconds.
2. Logo (`showLogo`, `animateLogo`): `bg_logo.jpg` and `logo.png`. `Cilada Games.caf` plays (the studio sound). The logo animates for about 2 seconds, then the segue "goToMenu" opens the main menu.

## Main menu (`MainMenuViewController`)

- Music: `menuSound.mp3`, looping. It's kept in `Global.mainMenuMusic` and stopped by gameplay scenes (free mode stops it on entry). Notifications "playMenuMusic" and "stopMenuMusic" control it.
- Visual: the nebula background and sliding doors ("leftDoor", "rightDoor"). `closing_doors.caf` belongs to the door animation. Confirm when it plays.
- Buttons (Portuguese titles from Main_iPhone.strings, English from the Base storyboard, which still needs reading): Campaign (Campanha), Free Mode (Modo Livre), Multiplayer (Multpleier), Hangar, Tutorial, About (Sobre).
- Pressing a button plays `acceptButton.mp3` (`Global playAcceptSoundButton`). Campaign, Free Mode and Multiplayer go through a loading screen showing "Loading..." (`tela_load`). Hangar, Info and Tutorial open their own screens ("Settings", "Info", "tutorial").
- First launch (`primeiraVez`): an alert titled "Welcome, beginner!" says "For a better game experience, consider playing the basic tutorial." with the buttons "Go to tutorial" and "Cancel".
- Multiplayer needs Game Center: "Attention" / "You must be logged into Game Center to enter multiplayer!".

## Campaign selector (`CampaignScene`, a SpriteKit menu)

- It shows one chapter at a time: "Chapter %ld: %@" (`cap_seletor`), with the chapter title from `capN_title` and Roman numerals from the `Capitulo` class. Below that are four level buttons labelled "Level %ld: %@" (`cap_fase`, with the level names from `capN_lvlM`) and a back button "Back" (`cap_sair`).
- Swipe left and right change the chapter (`loadNextChapter` and `loadPreviousChapter`), speaking the new chapter label. With VoiceOver, swipes inside the chapter move through the level items, playing `chageButton.mp3` and speaking each one, and a double tap opens the selected level.
- Locks:
  - `verifyProgress`: levels and chapters past the saved progress (lastChapter, lastLevel) are greyed out and locked.
  - `verifypurchasedCampaign`: without the full campaign purchase, chapters after 1 show a "block" overlay. In Portuguese a locked chapter speaks "Bloqueado" (`cap_Block`). That key is missing in English, so English falls back to the raw key "cap_Block". Original quirk.
  - Choosing a locked chapter without the purchase starts the in-app purchase flow (`iniciaCompra`, then `CompraCampanhaViewController`): "Full campaing not purchased" / "To continue playing after chapter 1 you must purchase the full campaing mode." with the buttons "Buy", "Restore" and "back".
- `presentChapterWithStage:` starts the chosen ChapterNScene at that stage through a loading screen.

## In-game menus (BaseScene, SpriteKit menuObjects)

All of these use the menu navigation described in NOTES (with VoiceOver: swipe to move, `chageButton.mp3`, `errorButton.mp3` at the ends, double tap to activate with `acceptButton.mp3`). Index 0 is the title.

- Pause (`callPause`, from swipe up): title "pause" (the `pause` key exists only in Portuguese, "Jogo Pausado", so English shows and speaks the raw key "pause"). Items: "Continue, button", "Restart, button", "Leave game, button". It speaks "%@, %@" (the title and first item). All Aureal sounds pause and the scene pauses. Continue resumes all sounds.
- Free mode game over (`telaGameOver`): title "Game Over". It shows the score and best score. Items: "Back to menu button", "New game button". It speaks "Game Over. You scored N points! Best score: M points." (`game_over_freemode`) followed by the first item.
- Campaign game over (`telaGameOverCampanha`): title "Game Over". Items: "Select level button", "New game button" (restart). It speaks the title and first item.
- Mission complete (`missionComplete`): title "Mission completed". Items: "Select level button", "Next level button" (absent after level 4, which goes to the next chapter's level 1 through capitulo/fase). It speaks the title and first item. It also saves progress (below).
- Tutorial complete (`tutorialCompleto`): title "Tutorial Completed". Items: "Select tutorial button", "Next tutorial button".
- Activations post notifications that the GameViewController handles: "reinicia" (restart), "proximoTutorial", "backMenuCampanha", "novoJogo", "proximoMissao", "backMenuController".

## Hangar (`SettingsViewController`)

- It shows five stats, each with 0 to 5 filled points and a plus button: Life (`lbl_life`), Shield (`lbl_shield`), Moving (`lbl_speed`), Shooting (`lbl_atkSpeed`), Power (`lbl_power`). It also shows "%ld AVAILABLE POINTS" (`pontosDisponiveis`, showing winPoints).
- Accessibility labels: the stat labels read "Life, N points" and so on (`lbl_*_points`). The plus buttons use `lbl_*_points_button` ("Life, N points. M available points. Add points."). Those button keys exist only in Portuguese, so English VoiceOver reads raw keys there. Original quirk. A screen-changed accessibility notification is posted after changes.
- `actionUpPower:` spends 1 winPoint to add 1 point to the chosen stat (life, shield, speed, attack speed, which is timeShotPoints, or power, which is shotPoints), then saves. `checkForButtonLock` disables a plus button when the stat is at 5 or no points are left.
- Back: "BACK" (`info_voltar`). It resets ControleCapitulo to "no".

## Upgrade points and progress

- Progress (missionComplete): when the finished level is the furthest one reached (fase == lastLevel and capitulo == lastChapter):
  - Levels 1 to 3: lastLevel += 1.
  - Level 4 of chapters 1 to 8: lastLevel = 1, lastChapter += 1, and ControleCapitulo = "yes" (a chapter was newly completed).
  - Then progress is saved.
- Points (GameViewController `backMenuCampaign`): when returning to the campaign with ControleCapitulo == "yes", winPoints += 2. If lastChapter is 5, another +2. Then points are saved and the Hangar opens automatically. So every newly finished chapter gives 2 points, with a one-time bonus of 2 after chapter 4.
- NSUserDefaults keys (Global): `Shoot_Points`, `TimeShoot_Points`, `Life_Points`, `Shild_Points`, `Speed_Points`, `Win_Points`, `last_Chapter`, `last_Level`, `purchased_Campaing`, `Campaign_Mode`, `bestScore`, `primeiraVez`, `ControleCapitulo`, plus per-mission keys `Missao_N_Capitulo_M_Completa`. The defaults for a fresh save still need confirming in `Global init` (lastChapter and lastLevel probably start at 1).

## Info screen (`InfoViewController`)

- Sections: "About", "CREDITS" (developers, sound design: FreeSFX, SoundJay, MillionthVector; graphic design; revision), "CONTACT US" with "SEND EMAIL" (contato@graycompany.com.br, subject "Gray Co. - Nebula") and "OUR PAGE". Copyright "GRAY COMPANY (C) All Rights Reserved", and "Version 1.0" (`info_versao`, even though the bundle is 1.3).
- The chapter 9 ending runs fast credits and speaks `credits_voice`.

## Chapter intro cutscenes (`CutScene`)

Traced with `tools/re/trace_cutscene.py`. Each chapter's intro does this:

1. Title card: `Deep_Impact_3.mp3` plays while "Chapter N" (in Roman numerals) and the chapter title fade in over 1.5 to 2 seconds. They stay about 5 seconds, then fade out over 2. The title card isn't spoken in the original, even with VoiceOver.
2. Narration, each part starting when the previous one ends (non-positional AVAudioPlayer, localized mp3), over panning and fading images:
   - Chapter 1: chapter1_part1 to part7.
   - Chapter 2: chapter2_part1 and part2.
   - Chapter 3: chapter3_part1 to part3.
   - Chapter 4: chapter4_part1 to part3.
   - Chapter 5: speak "Receiving commander's message. Playing message." (`chapter5_part1`, TTS), then chapter5_part2 to part4.
   - Chapter 6: speak `chapter6_part1` (the same line), then chapter6_part2.
   - Chapter 7: speak `chapter7_part1`, then chapter7_part2 and part3.
   - Chapter 8: speak "Sending message." (`chapter8_part1`), then chapter8_part2, then speak "Message sent." (`chapter8_part3`).
   - Chapter 9: chapter9_part1 and part2.
3. Then the completion block starts the chapter (see CHAPTERS.md). A tap at any point skips the cutscene (`skipCutScene`).

- Unused text: the mission report strings (`cap1_lvl1_intro`, `cap1_lvl3_intro`, `cap1_lvl4_ending`), `capN_main_intro` (most are placeholders like "Descricao5") and `intro_tut` aren't referenced by any code path found. The narration is in the mp3 files instead.

## Leftovers

- Versus mode (`VersusScene`, GameKitHelper): two players over Game Center, with "Start!", "Winner. The game will restart automatically." and "Draw". Not studied in depth, and needs a decision before it's ported.
- GameAnalytics: the didBeginStage, didWinStage and didFailStage callbacks only send analytics events. They have no gameplay effect.
