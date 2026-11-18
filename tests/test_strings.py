import os

from nebula.strings import LANGUAGES, Strings, choose_language, objc_format, windows_language


def test_both_tables_load_with_their_accents():
    pt = Strings('pt')
    assert pt.get('cap5_lvl2') == 'Mercúrio'
    assert pt.get('compra_transactionCompleteTitle') == 'Transação Completa'
    assert Strings('en').get('cap5_lvl2') == 'Mercury'


def test_missing_keys_fall_back_to_the_key_like_ios():
    assert Strings('pt').get('gameOver_menu') == 'gameOver_menu'


def test_english_fixes_replace_raw_keys():
    en = Strings('en')
    assert en.get('pause') == 'Game paused'
    assert en.get('cap_Block') == 'Locked'
    assert en.format('lbl_life_points_button', 3, 2) == 'Life, 3 points. 2 available points. Add points.'
    assert Strings('pt').get('pause') == 'Jogo Pausado'


def test_objective_c_formats():
    assert objc_format('Chapter %ld: %@', 3, 'HYPERDRIVE') == 'Chapter 3: HYPERDRIVE'
    assert objc_format('Score: %d.', 120) == 'Score: 120.'
    assert objc_format('100%% sure') == '100% sure'
    assert Strings('en').format('game_over_freemode', 50, 80) == 'Game Over. You scored 50 points! Best score: 80 points.'


def test_narration_keys_resolve_to_existing_localized_files():
    for lang in LANGUAGES:
        s = Strings(lang)
        for key in ('tut_1.0', 'tut_6.10', 'chapter1_part7', 'chapter9_part2'):
            assert os.path.exists(s.sound_path(key)), (lang, key)
    assert Strings('en').sound_path('tut_1.0').endswith('tut_1.0_en.mp3')
    assert Strings('pt').sound_path('tut_1.0').endswith('tut_1.0.mp3')


def test_tut_6_2_keeps_the_original_data_bug():
    assert Strings('en').get('tut_6.2') == 'tut_6.0_en.mp3'


def test_language_choice():
    assert choose_language({'language': 'pt'}) == 'pt'
    assert choose_language({'language': 'en'}) == 'en'
    assert choose_language({'language': 'fr'}) == windows_language()
    assert choose_language(None) in LANGUAGES


def test_settings_file_is_optional_and_overrides_language(tmp_path):
    from nebula.settings import load_settings
    assert load_settings(str(tmp_path / 'missing.json')) == {}
    bad = tmp_path / 'bad.json'
    bad.write_text('not json', encoding='utf-8')
    assert load_settings(str(bad)) == {}
    good = tmp_path / 'settings.json'
    good.write_text('{"language": "pt"}', encoding='utf-8')
    assert choose_language(load_settings(str(good))) == 'pt'
