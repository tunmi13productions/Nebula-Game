# Menus, cutscenes, startup and saving

Recovered from the view controllers, `CampaignScene`, `CutScene`, `BaseScene` menus and `Global`. Text in quotes is the English Localizable.strings value. The key is given in brackets where that's useful. Everything here was built for VoiceOver users: UIKit buttons carry accessibility labels, and the SpriteKit menus speak their items themselves.

## Startup (`IntroViewController`)

1. Headphones notice (`avisoDosFones`): it shows "PUT YOUR HEADPHONES" and "FOR A BETTER EXPERIENCE" with a headphones image. None of it is an accessibility element. With VoiceOver running, the game voice speaks "%@ %@, %@" built from `sound_1`, `sound_2` and `sound_3` ("PUT YOUR HEADPHONES FOR A BETTER EXPERIENCE., Thunder at the right side.") at rate 0.55 with a 2 second pre-delay, and the logo starts when the line ends. Without VoiceOver, a 5 second timer starts the logo instead.
2. Logo (`showLogo`, `animateLogo`): `thunder.mp3` plays at volume 0.8 (the file is silent on the left channel, so it's heard on the right only). `bg_logo.jpg` and `logo.png` fade in over 2 seconds and out over 2, then the main menu is pushed.
- `IntroViewController playSound` would play `Cilada Games.caf` at volume 0.5, but nothing calls it (the selector has no reference), so the studio sound never plays.

## Main menu (`MainMenuViewController`)

- Buttons, in screen order (VoiceOver order): Campaign (tag 1), Free Mode (tag 2), Tutorial (tag 3), Multiplayer (tag 4), Hangar (tag 5), About (tag 6). Titles come from the storyboard: English from the compiled Base storyboard, Portuguese from `pt.lproj/Main_iPhone.strings` (Campanha, Modo Livre, Tutorial, Multpleier, Hangar, Sobre). Centres on the 320 by 568 layout: Campaign (75, 105), Free Mode (242, 105), Tutorial (75, 283), Multiplayer (248, 291), Hangar (75, 468), About (255, 468).
- Every button plays `acceptButton.mp3` first (`Global playAcceptSoundButton`).
- Campaign and Free Mode (`buttonPressed:`): a loading view (`backTelaLoad`, an animated ship and a "Loading" label that isn't an accessibility element) fades in over 2 seconds. Then, with VoiceOver, the game voice says "Loading" (`tela_load`, rate 0.55), and the game view controller is pushed with gameType set to the button tag.
- Tutorial, Hangar and About (`openSecondaryMenu:`): push the "tutorial", "Settings" and "Info" view controllers.
- Multiplayer needs Game Center: "Attention" / "You must be logged into Game Center to enter multiplayer!".
- On first load a white flash fades over 1 second, then the doors open over 0.4 seconds while `closing_doors.caf` plays (doorAudio).
- Every viewDidAppear sets ControleCapitulo to "no".
- Music: `Global.mainMenuMusic` is played on viewDidAppear and stopped by gameplay scenes, but nothing ever creates that player (setMainMenuMusic: has no caller and the `menuSound` string has no reference). So the menu is silent apart from the doors, and `menuSound.mp3` is unused.
- First launch: `alertViewTutorial` ("Welcome, beginner!", "For a better game experience, consider playing the basic tutorial.", "Go to tutorial", "Cancel") is never called. Instead the tutorial selection screen starts the movement tutorial on its first visit (see below).

## Tutorial selection (`TutorialSelectionViewController`)

- BACK (`info_voltar`), a button across the top (frame 0, 0, width, height / 7), so VoiceOver reads it first. Then six buttons with the tutorial names as accessibility labels (`tut_movimento`, `tut_inimigo`, `tut_ataque`, `tut_batalha`, `tut_basico`, `tut_especial`: MOVEMENT, ENEMIES, ATTACK, BATTLE, BASIC, SPECIAL), tags 1 to 6.
- `tutorialSelected:` plays no accept sound. The loading view fades in over 2 seconds, then the game voice says "Loading" and the game view controller starts that tutorial.
- On viewDidLoad, if `primeiraVez` isn't 1, the screen selects a tutorial by itself and sets `primeiraVez` to 1: the movement tutorial with VoiceOver running, the basic one without.
- Back: `acceptButton.mp3`, the doors close over 1 second, then the screen is popped.
- "Next tutorial" (proximoTutorial) stores the new tutorial number as a string under the `tutorial` key.

## Campaign selector (`CampaignScene`, a SpriteKit scene)

- It's shown by the game view controller (gameType 1). `initWithSize:onChapter:` with no chapter (from the main menu) opens on lastChapter. The background is a free mode map generator, visual only.
- With VoiceOver running, everything is spoken by the game voice at rate 0.55. menuSelection 0 is the chapter label "Chapter %ld: %@" (`cap_seletor` with the `capN_title`), 1 is Back (`cap_sair`), 2 to 5 are the levels "Level %ld: %@" (`cap_fase` with `capN_lvlM`). Locked items get "%@, %@" with `cap_Block` ("Locked").
- Locks (`verifyProgress`): a level is locked when the chapter is lastChapter and the level is past lastLevel. Chapters past lastChapter are locked as a whole but can't be reached (below).
- didMoveToView speaks the chapter label (speakSentence:withRate:, no completion).
- Moving between items (one-finger swipes, `swipeRightDetected:` and `swipeLeftDetected:`): ignored while `swiping`. Past either end: `errorButton.mp3`, then swiping clears after 0.2 seconds. Otherwise `chageButton.mp3`, the selection moves, and the item is spoken with a completion that clears swiping, so input waits for each line to finish.
- Changing chapter (`didSwipeLeft:` for the next chapter, `didSwipeRight:` for the previous): ignored while swiping, then `chageButton.mp3`.
  - loadNextChapter: if the chapter is below 9 and below lastChapter, the next chapter slides in over 1 second, and its label is spoken when it arrives (selection back to 0). Then, if the chapter (after the move) isn't below lastChapter and isn't 9, "Locked" is spoken at once. When the move happened, the chapter label cuts it off a second later. Swiping is cleared at once.
  - loadPreviousChapter: on chapter 1 it says "Back" and then posts backMenuController, which leaves to the main menu. Otherwise the previous chapter slides in over 1 second and its label is spoken.
- `doubleTapDetected:`: ignored while swiping. A locked chapter or level plays `errorButton.mp3`. Otherwise `acceptButton.mp3` plays, and:
  - Back plays the accept sound again, says "Back" with a 0.5 second pre-delay, then backPressed posts backMenuController.
  - A level sets swiping, says the level name (`capN_lvlM` alone) with a 0.5 second pre-delay, then presentChapterWithStage.
  - The chapter label does nothing more.
- `didSwipeUp:`: says "Back", then backMenuController.
- `presentChapterWithStage:` saves `capitulo` and `fase`, then presents ChapterNScene at that stage.
- The purchase checks (`verifypurchasedCampaign`, `iniciaCompra`) never trigger, because `Global init` sets purchasedCampaign to YES.

## Game view controller notifications

- backMenuController: pops the game view controller (back to the screen that pushed it).
- backMenuCampanha (`backMenuCampaign`): for the campaign, the selector is shown again on the chapter saved in `capitulo`. When ControleCapitulo is "yes" it opens on lastChapter instead, adds 2 winPoints (2 more if lastChapter is now 5), saves the points and pushes the Hangar.
- proximoMissao (`proximaMissao`): `fase` + 1 is saved and that level of the same chapter starts.
- reinicia and novoJogo: the same level (or a new free mode game) starts again.

## In-game menus (BaseScene, SpriteKit menuObjects)

All of these use the menu navigation described in NOTES (with VoiceOver: swipe to move, `chageButton.mp3`, `errorButton.mp3` at the ends, double tap to activate with `acceptButton.mp3`). Index 0 is the title.

- Pause (`callPause`, from swipe up): title "pause" (the `pause` key exists only in Portuguese, "Jogo Pausado", so English shows and speaks the raw key "pause"). Items: "Continue, button", "Restart, button", "Leave game, button". It speaks "%@, %@" (the title and first item). All Aureal sounds pause and the scene pauses. Continue resumes all sounds.
- Free mode game over (`telaGameOver`): title "Game Over". It shows the score and best score. Items: "Back to menu button", "New game button". It speaks "Game Over. You scored N points! Best score: M points." (`game_over_freemode`) followed by the first item.
- Campaign game over (`telaGameOverCampanha`): title "Game Over". Items: "Select level button", "New game button" (restart). It speaks the title and first item.
- Mission complete (`missionComplete`): title "Mission completed". Items: "Select level button", "Next level button" (absent after level 4, which goes to the next chapter's level 1 through capitulo/fase). It speaks the title and first item. It also saves progress (below).
- Tutorial complete (`tutorialCompleto`): title "Tutorial Completed". Items: "Select tutorial button", "Next tutorial button".
- Activations post notifications that the GameViewController handles: "reinicia" (restart), "proximoTutorial", "backMenuCampanha", "novoJogo", "proximoMissao", "backMenuController".

## Hangar (`SettingsViewController`)

- It shows five stats, each with 0 to 5 filled points and a plus button: Life (`lbl_life`), Shield (`lbl_shield`), Moving (`lbl_speed`), Shooting (`lbl_atkSpeed`), Power (`lbl_power`), plus "%ld AVAILABLE POINTS" (`pontosDisponiveis`, showing winPoints), a ship image and BACK (`info_voltar`).
- BACK is a button across the top of the screen (frame 0, 0, width, height / 7), so VoiceOver reads it first. The available points label is centred at height / 7, below it, followed by the stat rows.
- Accessibility labels: each stat has a separate accessible label, "Life, N points" and so on (`lbl_*_points`, the `lbl_*Acces` labels). The plus buttons use `lbl_*_points_button` ("Life, N points. M available points. Add points."). Those button keys exist only in Portuguese, so English VoiceOver read raw keys there. Original quirk, fixed by a deviation.
- `checkForButtonLock` disables a plus button and takes it out of the accessibility order when the stat is at 5 or no points are left.
- `actionUpPower:` with no points left only refreshes the labels. Otherwise it plays the accept sound, spends 1 winPoint to add 1 point to the chosen stat (life, shield, speed, attack speed, which is timeShotPoints, or power, which is shotPoints), saves the points and rechecks the locks. Nothing is announced. `buildPoints` posts a layout-changed notification with an empty string, which doesn't move the VoiceOver focus.
- Back: the accept sound. If ControleCapitulo is "yes" it's set to "no". The doors close over 1 second, then the screen is popped.

## Upgrade points and progress

- Progress (missionComplete): when the finished level is the furthest one reached (fase == lastLevel and capitulo == lastChapter):
  - Levels 1 to 3: lastLevel += 1.
  - Level 4 of chapters 1 to 8: lastLevel = 1, lastChapter += 1, and ControleCapitulo = "yes" (a chapter was newly completed).
  - Then progress is saved.
- Points (GameViewController `backMenuCampaign`): when returning to the campaign with ControleCapitulo == "yes", winPoints += 2. If lastChapter is 5, another +2. Then points are saved and the Hangar opens automatically. So every newly finished chapter gives 2 points, with a one-time bonus of 2 after chapter 4.
- NSUserDefaults keys (Global): `Shoot_Points`, `TimeShoot_Points`, `Life_Points`, `Shild_Points`, `Speed_Points`, `Win_Points`, `last_Chapter`, `last_Level`, `purchased_Campaing`, `Campaign_Mode`, `bestScore`, `primeiraVez`, `ControleCapitulo`, plus per-mission keys `Missao_N_Capitulo_M_Completa`. The defaults for a fresh save still need confirming in `Global init` (lastChapter and lastLevel probably start at 1).

## Info screen (`InfoViewController`)

- Accessibility elements, top to bottom: BACK (`info_voltar`, across the top), an invisible label "About" (`info_sobre`) laid over the about image (the about text is drawn as an image, `sobre`), CREDITS (`info_credito`), OUR PAGE (`contato_pagina`), SEND EMAIL (`contato_email`), and the copyright label "GRAY COMPANY (C) All Rights Reserved" (`info_gray`). "Version 1.0" (`info_versao`) isn't used.
- SEND EMAIL (`sendMailAction:`) opens the mail composer to contato@graycompany.com.br with the subject "Gray Co. - Nebula". It's disabled when `canSendMail` is NO. OUR PAGE (`paginaAction:`) opens http://www.graycompany.com.br.
- CREDITS (`creditosPressed`) swaps the about part for a credits table and back. While the table shows, the about images are hidden, the "About" label leaves the accessibility order, and OUR PAGE and SEND EMAIL are disabled and taken out of the order. The CREDITS button stays and closes the table again.
- The table has 18 rows, from an array in viewDidLoad: " DEVELOPERS" (`cred_devs`), Bruno Moreira, Diego Pereira, Felipe Delazeri, Leonardo Gubert, Lucas Carletti, " SOUND DESIGN" (`cred_sounds`), FreeSFX, OpenGameArt, SoundJay, " GRAPHIC DESIGN" (`cred_design`), OpenGameArt, MillionthVector, " REVISION" (`cred_teste`), Marcia Campos, Lucas Santurio, Rai Carvalho, Ricardo Rauber. Rows starting with a space are headers. Rows 7, 8, 9, 11 and 12 are buttons labelled with the name that open the source's site (`buttonListAction:`): FreeSFX http://www.freesfx.co.uk/, OpenGameArt http://opengameart.org, SoundJay http://www.soundjay.com/, MillionthVector http://millionthvector.blogspot.de. The other rows are plain accessible text.
- In the English build, "Marcia", "Rai" and the copyright sign hold U+FFFD (the source files were saved in a legacy encoding). The Portuguese strings have them right: Márcia, Raí and ©.
- The credits name "Felipe Delazeri" differs from the chapter 9 credits text, which says "Felipe Riffel". Both are kept as they are.
- Back: the accept sound, the doors close over 1 second, then the screen is popped.
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
