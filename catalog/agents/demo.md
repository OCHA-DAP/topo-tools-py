# AGENTS.md: Netherlands demo inputs

Input layers for trying topo-tools on Dutch boundaries. Each folder is named after one tool and holds that tool's inputs, one per tier. Tool outputs aren't stored here: run the tool to produce them.

| Input | Tool | Contents |
|---|---|---|
| [schema-crosswalk/admin2-simplified](schema-crosswalk/admin2-simplified/AGENTS.md) | `topo-tools schema-crosswalk` | 342 gemeenten with CBS column names, simplified to 100 m |

Every input is built from [nld/2025/nld_admin2](../2025/nld_admin2/AGENTS.md) by `catalog/build_demo.py` in [topo-tools-py](https://github.com/OCHA-DAP/topo-tools-py). The conventions are in [../AGENTS.md](../AGENTS.md).
