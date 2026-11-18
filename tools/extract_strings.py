"""Converts the original Localizable.strings tables (binary plists) into data/strings/en.json and pt.json,
and the main menu storyboard's button titles into data/strings/storyboard_en.json and storyboard_pt.json
(English from the compiled Base storyboard, Portuguese from pt.lproj/Main_iPhone.strings).

usage: python -I tools/extract_strings.py   (run from the repository root, with the ipa unpacked in decompiled/ipa)
"""
import json
import os
import plistlib
import re
import sys

sys.path.insert(0, os.path.join('tools', 're'))
from nib import load as load_nib  # noqa: E402

APP = os.path.join('decompiled', 'ipa', 'Payload', 'BEPiDGame.app')
for lproj, lang in (('Base.lproj', 'en'), ('pt.lproj', 'pt')):
    with open(os.path.join(APP, lproj, 'Localizable.strings'), 'rb') as f:
        table = plistlib.load(f)
    with open(os.path.join('data', 'strings', lang + '.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dict(sorted(table.items())), f, ensure_ascii=False, indent=1)
        f.write('\n')
    print(lang, len(table), 'strings')


def storyboard_titles():
    nib = os.path.join(APP, 'Base.lproj', 'Main_iPhone.storyboardc', '5tV-GJ-fYG-view-O4S-3N-WaP.nib')
    objs = load_nib(nib)
    text = lambda i: [v for k, v in objs[i][1] if k == 'NS.bytes'][0].decode()
    en = {}
    for cls, values in objs:
        if cls == 'NSLocalizableString':
            d = dict(values)
            en[text(d['NSKey'][1])] = d['NS.bytes'].decode()
    with open(os.path.join(APP, 'pt.lproj', 'Main_iPhone.strings'), encoding='utf-8', errors='replace') as f:
        pt = {k: v for k, v in re.findall(r'^"([^"]+)" = "([^"]*)";', f.read(), re.M) if k in en}
    for lang, table in (('en', en), ('pt', pt)):
        with open(os.path.join('data', 'strings', 'storyboard_%s.json' % lang), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(dict(sorted(table.items())), f, ensure_ascii=False, indent=1)
            f.write('\n')
        print('storyboard', lang, len(table), 'strings')


storyboard_titles()
