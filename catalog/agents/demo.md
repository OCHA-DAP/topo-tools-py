# AGENTS.md: Netherlands demo inputs

Input layers for trying topo-tools on Dutch boundaries. Each folder is named after a topo-tools tool group and holds one folder per tier, with the files that group's tools take. Tool outputs aren't stored here: run the tool to produce them.

| Input | Tools | Contents |
|---|---|---|
| [schema/admin2-simplified](schema/admin2-simplified/AGENTS.md) | `schema-map`, `schema-crosswalk` | 342 gemeenten with CBS column names, simplified to 100 m |

Every input is built from [nld/2025/nld_admin2](../2025/nld_admin2/AGENTS.md) by `catalog/build_demo.py` in [topo-tools-py](https://github.com/OCHA-DAP/topo-tools-py). The conventions are in [../AGENTS.md](../AGENTS.md).
