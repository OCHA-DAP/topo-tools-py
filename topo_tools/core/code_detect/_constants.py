"""Pure literals for code-detect: kinds, severities and thresholds."""

ERROR = "error"
WARN = "warn"

SEVERITY = {
    "blank-code": ERROR,
    "name-conflict": ERROR,
    "duplicate-code": ERROR,
    "prefix-mismatch": ERROR,
    "split-unit": WARN,
    "format-outlier": WARN,
    "format-undetected": WARN,
}

# prefix-mismatch and format-outlier need this share of a level's codes to
# follow the rule, and at least FORMAT_MIN_CODES codes, before flagging the rest.
PREFIX_SHARE = 0.9
SHAPE_SHARE = 0.9
FORMAT_MIN_CODES = 10
