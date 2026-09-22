---
title: For agents
description: Ways to start a topo-tools session with an agent, pasted prompt or plugin install.
---

Paste this into an agent's prompt to start a session:

```text
Read https://ocha-dap.github.io/topo-tools-py/, then ask what
administrative boundary data needs cleaning and pick the matching tool.
```

Formal install of the [`topo-tools`](https://github.com/OCHA-DAP/topo-tools-py/blob/main/plugins/topo-tools) plugin:

```bash
/plugin marketplace add OCHA-DAP/topo-tools-py
```

Then, once that confirms:

```bash
/plugin install topo-tools@topo-tools
```
