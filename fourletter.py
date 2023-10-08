import os
import pathlib, re

"""
Yucatan Woodpecker YUWO Melanerpes pygmaeus MELPYG
Yucatan Wren YUWR Campylorhynchus yucatanicus CAMYUC
+ Yuma Ridgway's Rail YRRA Rallus obsoletus yumanensis RALOBY
Zapata Rail ZARA Mustelirallus cerverai MUSCER
Zapata Sparrow ZASP Torreornis inexpectata TORINE
"""

global _codes
_codes = None

global _names
_names = None


def populate_code_dict():
    codes = {}
    names = {}
    for line in pathlib.Path('4letter.txt').read_text().split('\n'):
        m = re.match(r'(\+ )?([A-Z].+) ([A-Z]{4})[*]? ([A-Z].+) ([A-Z]{6})[*]?', line)
        if m:
            maybeplus, comname, code4, sci, code6 = m.groups()
            codes[code4] = comname
            codes[code6] = comname
            names[comname] = (code4, code6)
    return codes, names


def get_common_name_by_code(code):
    global _codes
    global _names
    if not _codes:
        _codes, _names = populate_code_dict()
    return _codes.get(str(code).upper(), None)


def code_by_common_name_substring(substring, max_items=10):
    global _codes
    global _names
    if not _names:
        _codes, _names = populate_code_dict()

    ctr = 0
    substring = substring.lower()
    for comname, (code4, code6) in _names.items():
        if substring in comname.lower():
            ctr += 1
            yield code4, comname
        else:
            for comnameword in comname.lower().split():
                if comnameword.startswith(substring):
                    ctr += 1
                    yield code4, comname
                    break
        if ctr >= max_items:
            break
