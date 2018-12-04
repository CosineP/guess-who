#!/usr/bin/env python
# -*- coding: utf-8 -*-
# MODIFIED AND SIMPLIFIED FROM:
# https://github.com/AppliedEllipsis/pyEmoji/blob/master/pyEmoji.py

module_info = {
'NAME': "pyEmoji",
'ORIGINAL_AUTHOR': "Applied Ellippsis", # leave this
'AUTHOR': "cosine", # change this to you
'DESCRIPTION': '''
Generates a random emoji for python2 and python3.
''',
'REPO_URL': 'https://github.com/AppliedEllipsis',
'VERSION': "0.1.2a",
'LICENSE': "GPLv3",
}

import sys, random

UNICODE_VERSION = 6

# Parts taken from: https://gist.github.com/shello/efa2655e8a7bce52f273
# can possibly use json from https://github.com/iamcal/emoji-data in future, instead of ranges
EMOJI_RANGES_UNICODE = {
    6: [ # http://www.unicode.org/charts/PDF/Unicode-6.0/U60-1F300.pdf
        (0x0001F300, 0x0001F320),
        (0x0001F330, 0x0001F335),
        (0x0001F337, 0x0001F37C),
        (0x0001F380, 0x0001F393),
        (0x0001F3A0, 0x0001F3C4),
        (0x0001F3C6, 0x0001F3CA),
        (0x0001F3E0, 0x0001F3F0),
        (0x0001F400, 0x0001F43E),
        (0x0001F440, 0x0001F440),
        (0x0001F442, 0x0001F4F7),
        (0x0001F4F9, 0x0001F4FC),
        (0x0001F500, 0x0001F53C),
        (0x0001F540, 0x0001F543),
        (0x0001F550, 0x0001F567),
        (0x0001F5FB, 0x0001F5FF),
    ],
    7: [ # http://www.unicode.org/charts/PDF/Unicode-7.0/U70-1F300.pdf
        (0x0001F300, 0x0001F32C),
        (0x0001F330, 0x0001F37D),
        (0x0001F380, 0x0001F3CE),
        (0x0001F3D4, 0x0001F3F7),
        (0x0001F400, 0x0001F4FE),
        (0x0001F500, 0x0001F54A),
        (0x0001F550, 0x0001F579),
        (0x0001F57B, 0x0001F5A3),
        (0x0001F5A5, 0x0001F5FF),
    ],
    8: [ # http://www.unicode.org/charts/PDF/Unicode-8.0/U80-1F300.pdf
        (0x0001F300, 0x0001F579),
        (0x0001F57B, 0x0001F5A3),
        (0x0001F5A5, 0x0001F5FF),
    ],
    9: [ # http://www.unicode.org/charts/PDF/Unicode-9.0/U90-1F300.pdf
        (0x0001F300, 0x0001F5FF),
    ]
}

NO_NAME_ERROR = '(No name found for this codepoint)'

if UNICODE_VERSION in EMOJI_RANGES_UNICODE:
    emoji_ranges = EMOJI_RANGES_UNICODE[UNICODE_VERSION]
else:
    emoji_ranges = EMOJI_RANGES_UNICODE[-1]

# build emoji table to take random from
emojis = []
for r in emoji_ranges:
  emojis += range( r[0], r[-1] )

# returns a random emoji (char value, doule escaped value, unicode name)
def random_emoji():
    emoji_decimal = random.choice(emojis)
    emoji_escaped = b"\\U%08x" % emoji_decimal
    emoji_char = emoji_escaped.decode('unicode-escape') # python2 work-around is to decode with unicode-escape
    return emoji_char

if __name__ == "__main__":
    emoji = random_emoji()
    print( 
        emoji
        ) 

