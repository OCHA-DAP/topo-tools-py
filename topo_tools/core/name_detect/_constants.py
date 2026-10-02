"""Pure literals for name-detect: kinds, severities, patterns and thresholds."""

ERROR = "error"
WARN = "warn"

SEVERITY = {
    "blank-name": ERROR,
    "placeholder-name": ERROR,
    "duplicate-name": WARN,
    "encoding-artifact": ERROR,
    "normalized-duplicate-name": WARN,
    "invisible-character": WARN,
    "unnormalized-unicode": WARN,
    "whitespace": WARN,
    "case-outlier": WARN,
    "mixed-script": WARN,
    "code-in-name": WARN,
}

# Kinds checked one name at a time, so a column-wide hit can roll up into one row.
PER_NAME_KINDS = (
    "blank-name",
    "placeholder-name",
    "encoding-artifact",
    "invisible-character",
    "unnormalized-unicode",
    "whitespace",
    "mixed-script",
    "code-in-name",
)

PLACEHOLDER_TOKENS = ("n/a", "n_a", "n.a.", "null", "none", "unknown", "undefined")

# A sibling name column is checked for blanks only when it is mostly filled.
SIBLING_FILLED_SHARE = 0.9

# case-outlier needs this share of a column's cased names in mixed case, and
# one all-caps word this long or two this short, so acronyms are skipped.
MIXED_CASE_SHARE = 0.9
CASE_LONG_WORD = 6
CASE_SHORT_WORD = 3

# code-in-name matches whole tokens of codes holding a letter and a digit.
CODE_IN_NAME_MIN_LENGTH = 3

# A kind hitting more than this share of a column (and at least ROLLUP_MIN_ROWS
# names) is reported as one column-level row.
ROLLUP_SHARE = 0.5
ROLLUP_MIN_ROWS = 5

# UTF-8 bytes read as cp1252: a lead byte (U+00C2-U+00EF as a character)
# followed by continuation bytes. Only the commonest leads, a C1 control or
# U+FFFD are flagged alone; any other lead needs a plausible repair.
_CONTINUATION = (
    r"[\x{80}-\x{BF}\x{152}\x{153}\x{160}\x{161}\x{178}\x{17D}\x{17E}\x{192}"
    r"\x{2C6}\x{2DC}\x{2013}\x{2014}\x{2018}-\x{201E}\x{2020}-\x{2022}\x{2026}"
    r"\x{2030}\x{2039}\x{203A}\x{20AC}\x{2122}]"
)
MOJIBAKE_PATTERN = (
    rf"[\x{{C2}}-\x{{DF}}]{_CONTINUATION}"
    rf"|[\x{{E0}}-\x{{EF}}]{_CONTINUATION}{_CONTINUATION}"
)
STRONG_MOJIBAKE_PATTERN = (
    rf"[\x{{C2}}\x{{C3}}]{_CONTINUATION}|\x{{E2}}\x{{20AC}}|\x{{EF}}\x{{BF}}\x{{BD}}"
    r"|[\x{80}-\x{9F}]"
)
REPLACEMENT_CHARACTER = "\ufffd"
# A repair is kept only if it yields Latin letters, digits, spaces and common
# punctuation, never a symbol, another script or a detached combining mark.
IMPLAUSIBLE_REPAIR_PATTERN = (
    r"[^\x{20}-\x{7E}\x{A0}-\x{24F}\x{1E00}-\x{1EFF}\x{2018}-\x{201D}"
    r"\x{2013}\x{2014}\x{20AC}]|[\x{A1}-\x{BF}\x{D7}\x{F7}]"
)

# cp1252's 0x80-0x9F characters; every other code point below 256 is its own byte.
CP1252_SPECIALS = {
    0x20AC: 0x80,
    0x201A: 0x82,
    0x0192: 0x83,
    0x201E: 0x84,
    0x2026: 0x85,
    0x2020: 0x86,
    0x2021: 0x87,
    0x02C6: 0x88,
    0x2030: 0x89,
    0x0160: 0x8A,
    0x2039: 0x8B,
    0x0152: 0x8C,
    0x017D: 0x8E,
    0x2018: 0x91,
    0x2019: 0x92,
    0x201C: 0x93,
    0x201D: 0x94,
    0x2022: 0x95,
    0x2013: 0x96,
    0x2014: 0x97,
    0x02DC: 0x98,
    0x2122: 0x99,
    0x0161: 0x9A,
    0x203A: 0x9B,
    0x0153: 0x9C,
    0x017E: 0x9E,
    0x0178: 0x9F,
}

# Format characters except ZWNJ/ZWJ (needed in Persian and Indic scripts),
# control characters, and any space other than U+0020.
INVISIBLE_PATTERN = r"[^\P{Cf}\x{200C}\x{200D}]|\p{Cc}"
# Roman numerals are capitals by convention, so case-outlier ignores them.
ROMAN_NUMERAL_PATTERN = r"^[IVXLCDM]+$"
ODD_SPACE_PATTERN = r"[^\P{Zs} ]|[\t\n\r]"

# Scripts whose letters look alike, so a word mixing them is a likely typo.
CONFUSABLE_SCRIPTS = ("Latin", "Cyrillic", "Greek")
