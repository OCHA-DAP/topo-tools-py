# AGENTS.md: topo-tools sample data

Sample inputs for [topo-tools](https://github.com/OCHA-DAP/topo-tools-py), grouped by ISO3 country code. Each collection holds one GeoParquet file, a PMTiles archive and a default style.

## Layout

Files sit at `{{iso3}}/{{year}}/{{iso3}}_admin{{n}}/{{iso3}}_admin{{n}}.parquet`. Demo inputs, one folder per topo-tools tool group, sit at `{{iso3}}/demo/{{group}}/{{tier}}/`. The only country so far is the Netherlands, see [nld/AGENTS.md](nld/AGENTS.md).

## Reading

Every file is GeoParquet 1.1 with a per-row `bbox` column. DuckDB reads it over HTTP:

```sql
INSTALL spatial; LOAD spatial;
SELECT * FROM read_parquet('{data}/nld/2025/nld_admin2/nld_admin2.parquet') LIMIT 5;
```

## License

CC-BY-4.0. Credit the producer named in each country's catalog.
