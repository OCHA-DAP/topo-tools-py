---
title: For agents
description: Ways to start a topo-tools session with an agent, pasted prompt or plugin install.
---

Paste this into an agent's prompt to clean and code a COD-AB administrative boundary layer:

```text
Read https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/plugins/topo-tools/skills/cod-ab/SKILL.md,
then follow it to clean and reconcile a COD-AB administrative boundary layer.
```

## Claude Code plugin

Install the [`topo-tools`](https://github.com/OCHA-DAP/topo-tools-py/blob/main/plugins/topo-tools) plugin:

```bash
/plugin install topo-tools --marketplace https://ocha-dap.github.io/topo-tools-py/marketplace.json
```

In VS Code, [click here](vscode://anthropic.claude-code/install-plugin?plugin=topo-tools&marketplace=https%3A%2F%2Focha-dap.github.io%2Ftopo-tools-py%2Fmarketplace.json) instead, it opens the Manage plugins dialog straight to the install step. For more information, see [Install plugins in VS Code](https://code.claude.com/docs/en/vs-code#install-plugins).

Once installed, invoke `/topo-tools:cod-ab` to clean, code, and package COD-AB administrative boundary polygons with topo-tools.
