---
name: verify-duckdb-function
description: Use before writing or reviewing code that calls a DuckDB or DuckDB spatial extension function, or when asked about one's signature, parameters, or behavior. Never rely on recalled knowledge about DuckDB/spatial functions, verify against the installed version first.
---

# Verify a DuckDB function

**CLI, best for specific function lookups** (includes full description, parameter docs, return type):

```bash
# Check a specific function: signature + full description
duckdb -c "LOAD spatial; SELECT function_name, parameters, parameter_types, return_type, description FROM duckdb_functions() WHERE function_name ILIKE 'ST_Buffer'"

# List all spatial functions
duckdb -c "LOAD spatial; SELECT function_name, parameters, return_type FROM duckdb_functions() WHERE function_name ILIKE 'ST_%' ORDER BY function_name"

# Search by keyword in description
duckdb -c "LOAD spatial; SELECT function_name, description FROM duckdb_functions() WHERE description ILIKE '%voronoi%'"
```

**gh api, best for browsing the full spatial function reference** (always matched to the installed version):

```bash
# Fetch the full spatial functions reference: branch derived from installed DuckDB version
DUCKDB_REF=$(duckdb --version | sed 's/v\([0-9]*\.[0-9]*\)\.[0-9]* (\([^)]*\)).*/v\1-\2/' | tr '[:upper:]' '[:lower:]') && \
gh api "repos/duckdb/duckdb-spatial/contents/docs/functions.md?ref=${DUCKDB_REF}" --jq '.content' | base64 -d
```
