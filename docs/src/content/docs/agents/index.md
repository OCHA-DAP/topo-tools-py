---
title: For agents
description: A prompt to paste into an agent to start a topo-tools session.
---

Paste this into an agent's prompt to start a session:

```text
Read https://ocha-dap.github.io/topo-tools-py/, then ask what
administrative boundary data needs cleaning and pick the matching tool.
```

Formal install of the [`topo-tools`](https://github.com/OCHA-DAP/topo-tools-py/blob/main/plugins/topo-tools/skills/cod-ab-cleaning/SKILL.md) plugin (includes the `cod-ab-cleaning` skill, invoked as `/topo-tools:cod-ab-cleaning`):

```bash
/plugin marketplace add OCHA-DAP/topo-tools-py
/plugin install topo-tools@topo-tools
```
