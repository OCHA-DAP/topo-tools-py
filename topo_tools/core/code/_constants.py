"""Non-user-configurable constants shared by code-refactor/code-update."""

# No geometry column on either tool's tabular output, so core.io's GDAL-vector
# COPY_OPTS doesn't apply. Same dict as core.change's own tool-private copy.
TABLE_COPY_OPTS = {
    ".csv": "(FORMAT CSV, HEADER)",
    ".parquet": "(FORMAT PARQUET, COMPRESSION ZSTD, COMPRESSION_LEVEL 15)",
}
