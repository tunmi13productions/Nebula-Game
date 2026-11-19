"""How a single character is spoken in a text box: symbols are named, letters and digits are left as they are.

Taken from Haptix (haptix/symbols.py, MIT License, copyright 2025 tunmi13productions), unchanged apart from
this note. A port addition (DEVIATIONS.md, "Multiplayer through a relay server").
"""

SYMBOLS = {
    # Whitespace
    " ": "space",
    "\t": "tab",
    "\n": "new line",
    "\r": "carriage return",
    " ": "no-break space",
    # The keyboard's symbols
    "`": "grave accent",
    "~": "tilda",
    "!": "exclamation mark",
    "@": "at",
    "#": "number",
    "$": "dollar",
    "%": "percent",
    "^": "caret",
    "&": "and",
    "*": "star",
    "(": "left paren",
    ")": "right paren",
    "_": "underscore",
    "-": "dash",
    "=": "equals",
    "+": "plus",
    "[": "left bracket",
    "]": "right bracket",
    "{": "left brace",
    "}": "right brace",
    "\\": "backslash",
    "|": "bar",
    ";": "semicolon",
    ":": "colon",
    "'": "apostrophe",
    '"': "quote",
    ",": "comma",
    "<": "less than",
    ".": "period",
    ">": "greater than",
    "/": "slash",
    "?": "question mark",
    # Typography, often pasted in from elsewhere
    "‘": "left single quote",
    "’": "right single quote",
    "“": "left quote",
    "”": "right quote",
    "–": "en dash",
    "—": "em dash",
    "…": "ellipsis",
    "•": "bullet",
    "·": "middle dot",
    "§": "section",
    "¶": "paragraph",
    "¡": "inverted exclamation mark",
    "¿": "inverted question mark",
    "«": "left double angle quote",
    "»": "right double angle quote",
    # Money
    "¢": "cent",
    "£": "pound",
    "€": "euro",
    "¥": "yen",
    # Maths and units
    "×": "times",
    "÷": "divided by",
    "±": "plus or minus",
    "°": "degree",
    "µ": "micro",
    "½": "one half",
    "¼": "one quarter",
    "¾": "three quarters",
    "≠": "not equal",
    "≤": "less than or equal",
    "≥": "greater than or equal",
    "∞": "infinity",
    # Marks
    "©": "copyright",
    "®": "registered",
    "™": "trademark",
    "←": "left arrow",
    "↑": "up arrow",
    "→": "right arrow",
    "↓": "down arrow",
}


def char_name(char):
    """The spoken name of one character. Anything without a name, like a letter, comes back as it is."""
    return SYMBOLS.get(char, char)
