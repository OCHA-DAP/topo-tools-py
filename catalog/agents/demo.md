# AGENTS.md: Netherlands demo inputs

Input layers for trying topo-tools on Dutch boundaries. Each folder is named after the tool it's for and holds the files that tool takes, simplified to 100 m. Tool outputs aren't stored here: run the tool to produce them.

| Input | Tool | Contents |
|---|---|---|
| [schema-map](schema-map/AGENTS.md) | `schema-map` | 342 gemeenten with CBS column names |
| [schema-join](schema-join/AGENTS.md) | `schema-join` | 342 gemeenten and 12 provincies, each with its own code and name |

The gemeenten come from [nld/2025/nld_admin2](../2025/nld_admin2/AGENTS.md) and the provincies from Kadaster Bestuurlijke Gebieden, built by `catalog/build_demo.py` in [topo-tools-py](https://github.com/OCHA-DAP/topo-tools-py). The conventions are in [../AGENTS.md](../AGENTS.md).
