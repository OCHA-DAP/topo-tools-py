"""Pure literals for schema-detect: kinds and severities."""

ERROR = "error"
WARN = "warn"

SEVERITY = {
    "levels-undetected": ERROR,
    "level-skipped": ERROR,
    "multiple-parents": ERROR,
    "orphan-child": ERROR,
    "supplemental-column": WARN,
    "column-naming": WARN,
    "column-set-mismatch": WARN,
}
