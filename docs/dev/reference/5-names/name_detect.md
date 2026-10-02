---
title: "name-detect"
sidebar:
  order: 3
  badge:
    text: Draft
    variant: caution
---

## Inputs

- `name-detect` MUST read the one input and reproject it to EPSG:4326 via
  `core.io.read_and_reproject()`, names untouched. It takes the coded
  finest-level layer, hierarchy embedded as columns.

## Level resolution

- With an explicit `name_field`/`code_field` pair (given together or not at
  all), each level's code column and name column MUST come from the
  templates, plus every numbered sibling of the name column present in the
  input (`adm2_name1`, `adm2_name2`, ...). A level with names but no code
  column MUST raise `ValueError`. Level 0's names are never checked; its
  code, if present, is level 1's parent, so one file MAY hold several
  countries.
- Without the pair, levels MUST come from structural detection
  (`core.schema_map.detect_level_columns_or_single()`). If a level is
  skipped or a column groups units like a level without being detected as
  one, `name-detect` MUST raise `ValueError` rather than compare names under
  the wrong parent.
- A level's parent is the next coarser resolved level's code; level 1 has
  none unless level 0 has a code.

## Checks

- Every check MUST run per level and per name column. Blank names are
  checked in a sibling column only when at least 90% of its units have a
  name.
- `name-detect` MUST report each of these kinds:

  | kind | severity | finding |
  | --- | --- | --- |
  | `blank-code` | error | a unit with no code, one row per parent |
  | `blank-name` | error | NULL, empty or whitespace only |
  | `placeholder-name` | error | `n/a`, `n_a`, `n.a.`, `null`, `none`, `unknown`, `undefined`, punctuation only, or the unit's own code |
  | `name-conflict` | error | one code with more than one name |
  | `encoding-artifact` | error | U+FFFD, a C1 control character, `Ã` or `Â` followed by a continuation byte, `â€`, or any other UTF-8 lead byte read as cp1252 when it repairs to plausible Latin text |
  | `duplicate-name` | warn | the same name for different codes under one parent |
  | `normalized-duplicate-name` | warn | names under one parent equal after ignoring case and punctuation between letters, or, for Latin names, accents when one of them has none |
  | `invisible-character` | warn | a format or control character, or a space other than U+0020; ZWNJ and ZWJ are allowed |
  | `unnormalized-unicode` | warn | NFC would compose characters (an accent stored as a separate character) |
  | `whitespace` | warn | leading, trailing or repeated spaces |
  | `case-outlier` | warn | Latin, Cyrillic or Greek only, and all lower case or all capitals with one capitalised word of at least 6 letters or two of at least 3 (Roman numerals ignored), where at least 90% of the column's other cased names are mixed case |
  | `mixed-script` | warn | one word with letters from more than one of Latin, Cyrillic and Greek |
  | `code-in-name` | warn | the name contains its own or its parent's code as a whole word (at least 3 characters, with a letter and a digit) |

- A unit with no code MUST be reported only as `blank-code`, never by
  another kind.
- A pair or group of units matched in several language columns MUST be
  reported once, from the first column that matches.
- A unit with `blank-name` MUST NOT be reported by another per-name kind in
  that column, and one with `encoding-artifact` MUST NOT also be reported as
  `invisible-character`.
- `suggested` MUST hold the fixed name for `whitespace`,
  `invisible-character` and `unnormalized-unicode`, and for
  `encoding-artifact` only when re-encoding as cp1252 and decoding as UTF-8
  succeeds and gives only Latin letters, digits, spaces and common
  punctuation.
- If one check fails, `name-detect` MUST still report the others.

## Outputs

- `name-detect` MUST always write the issues report, even with zero rows.
  It never modifies the input.
- When one per-name kind hits more than half of a column's names (and at
  least 5), it MUST be reported as one row for the column, with no code.
- A unit blank in several language columns MUST be one row, listing the
  columns.
- Columns: `key`, `kind`, `severity`, `level`, `name_column`, `code_a`,
  `name_a`, `code_b`, `name_b`, `suggested`, `reason`. A `.parquet` report
  MUST add `geometry` as its first column: the union of the unit's rows
  (both units' for a pair), NULL for a column row. A `.csv` report MUST be
  UTF-8 with a BOM.

## Configuration (`api.name_detect.detect()` / CLI)

- `name-detect` MUST process exactly one input file per call.
- `issues_path` MUST default to the input path with a `_name_issues` stem
  suffix and a `.csv` extension, and MUST end in `.csv` or `.parquet`,
  raising `ValueError` otherwise.
- `name-detect` MUST raise `FileExistsError` if `issues_path` already exists
  and overwriting wasn't requested.
- `step`, if given, MUST be one of `inputs`, `levels`, `checks`, `outputs`;
  any other value MUST raise `ValueError`.

## Examples

### Example 1: basic run, CSV report named automatically

    topo-tools name-detect admin3.parquet

### Example 2: explicit level columns, report with geometry

    topo-tools name-detect admin3.parquet admin3_name_issues.parquet \
      --name-field adm{n}_name --code-field adm{n}_code
