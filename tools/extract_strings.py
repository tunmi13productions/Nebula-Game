"""Converts the original Localizable.strings tables (binary plists) into data/strings/en.json and pt.json.

usage: python -I tools/extract_strings.py   (run from the repository root, with the ipa unpacked in decompiled/ipa)
"""
import json
import os
import plistlib

APP = os.path.join('decompiled', 'ipa', 'Payload', 'BEPiDGame.app')
for lproj, lang in (('Base.lproj', 'en'), ('pt.lproj', 'pt')):
    with open(os.path.join(APP, lproj, 'Localizable.strings'), 'rb') as f:
        table = plistlib.load(f)
    with open(os.path.join('data', 'strings', lang + '.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dict(sorted(table.items())), f, ensure_ascii=False, indent=1)
        f.write('\n')
    print(lang, len(table), 'strings')
