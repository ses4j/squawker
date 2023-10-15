import doctest 
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


from difflib import SequenceMatcher
from heapq import nlargest as _nlargest

def code_by_common_name_substring(substring, max_items=10):
    """
    >>> list(code_by_common_name_substring('american golden plover'))
    [('AMGP', 'American Golden-Plover')]
    >>> list(code_by_common_name_substring('barn'))
    [('BARG', 'Barnacle Goose'), ('BARS', 'Barn Swallow'), ('BANO', 'Barn Owl')]
    >>> list(code_by_common_name_substring("Lincoln's sparrow"))
    [('LISP', "Lincoln's Sparrow")]
    >>> list(code_by_common_name_substring("Lincolns"))
    [('LISP', "Lincoln's Sparrow")]
    """

    global _codes
    global _names
    if not _names:
        _codes, _names = populate_code_dict()

    ctr = 0
    # substring = substring.lower()
    # substring = re.sub(r'[^a-z ]', ' ', substring)

    matches = get_close_matches(substring, _names.keys(), n=max_items, max_dropoff=0.9) #, n=max_items) #, cutoff=0.1)   

    for comname in matches:
        code4, code6 = _names[comname]
        yield code4, comname
        ctr += 1
        if ctr >= max_items:
            break

    # for comname, (code4, code6) in _names.items():
    #     if substring in comname.lower():
    #         ctr += 1
    #         yield code4, comname
    #     else:
    #         for comnameword in comname.lower().split():
    #             # breakpoint()
    #             if comnameword.startswith(substring):
    #                 ctr += 1
    #                 yield code4, comname
    #                 break
    #     if ctr >= max_items:
    #         break


def get_close_matches(word, possibilities, n=3, max_dropoff=0.6):
    if not n >  0:
        raise ValueError("n must be > 0: %r" % (n,))
    if not 0.0 <= max_dropoff <= 1.0:
        raise ValueError("cutoff must be in [0.0, 1.0]: %r" % (max_dropoff,))
    result = []
    
    s = SequenceMatcher()
    s.set_seq2(word.lower())
    for x in possibilities:
        s.set_seq1(x.lower())

        matching_blocks = s.get_matching_blocks()
        score = sum(float(triple[-1]) ** 1.25 + (0.5 if triple[0] == 0 else 0) + (0.5  if triple[1] == 0 else 0) for triple in matching_blocks)

        # if word == 'barn' and 'buff-collared' in x.lower() or x.lower() == 'barn owl':
        #     print(x, s.get_matching_blocks(), score)

        result.append((score, x))

    result = _nlargest(n, result)
    # print(result[:10])
    
    best_score = result[0][0]
    min_allowed = best_score * max_dropoff
    res = []
    for score, x in result:
        if score > min_allowed:
            res.append(x)
        else:
            break
    return res

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    # print(list(get_close_matches('barn', ['Barn Owl', 'Barn Swallow', 'Basrna'])))
