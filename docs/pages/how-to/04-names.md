---
title: "4. Review names"
---

Fourth step of [preparing an administrative boundary
release](administrative-boundary-release/). Continues from the coded
output of [step 3](03-codes/). No dedicated tool yet, `schema-fill` is
built for bulk/global dataset production, not per-country name review, so
this step is manual investigation, generally covering:

- **Duplicates under the same parent**: two units sharing a name (or a
  near-identical one) under the same immediate parent.

      SELECT adm1_code, adm2_name, COUNT(*)
      FROM admin2_coded.parquet
      GROUP BY adm1_code, adm2_name
      HAVING COUNT(*) > 1;

- **Near-duplicates from a typo, not a real distinct name**: DuckDB's
  `jaro_winkler_similarity()`/`levenshtein()` flag close-but-not-exact
  pairs under the same parent for a human to confirm.

- **Blank or placeholder names**: any `adm{N}_name` that's `NULL`, empty,
  or still holds a source-system default.

- **Encoding artifacts**: mojibake (e.g. `Ã©` where `é` was intended),
  usually from a source file read with the wrong encoding.

- **Renamed vs. mistyped, against the reference release**: for a unit
  whose p-code already existed in `{ref_version}`, compare its name now
  against its name then. A real administrative rename is expected and
  fine, a diverging spelling of the same unit isn't.

- **Parent-name conflicts from `schema-join`**: each `value-mismatch` row
  in stage 1's issues file is a child whose own `adm{N}_name` differs
  from its parent layer's, which `schema-join` added as `adm{N}_name{k}`.
  Pick one spelling per parent unit and write it to `adm{N}_name` on
  every child under it. Drop that `schema-join` sibling only once no row
  still differs from `adm{N}_name`. Keep any `adm{N}_name{k}` mapped from
  the source in stage 1, since it's an alternate name, not a conflict.

Record every finding in an issues file (reusing the shared schema:
`key`, `kind`, `reason`, `unit_a`, `unit_b`, `parent_fid`, `geom`, every
other column null), `kind` one of `duplicate-name`, `near-duplicate-name`,
`blank-name`, `encoding-artifact`, `name-drift`. Unlike every other tool's
issues file, write this one even when it has zero rows: it's the only
artifact this stage produces, and Setup step 4 checks for its presence
(not its row count) to know this stage is done.

Next: [package for output](05-packaging/).
