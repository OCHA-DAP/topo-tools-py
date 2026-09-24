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

Install the [`topo-tools`](https://github.com/OCHA-DAP/topo-tools-py/blob/main/plugins/topo-tools) plugin using any one of the options below. Option 1 also turns on automatic updates. Once installed, invoke `/topo-tools:cod-ab` to clean, code, and package COD-AB administrative boundary polygons with topo-tools.

### Option 1: paste a prompt into Claude Code

```text
Run `claude plugin marketplace add
https://ocha-dap.github.io/topo-tools-py/marketplace.json`, then in
~/.claude/settings.json set "autoUpdate": true on the "topo-tools" entry
under "extraKnownMarketplaces" (add the entry if it's missing, keep all
other settings), then run `claude plugin install topo-tools@topo-tools`
and tell me to restart Claude Code.
```

### Option 2: run the install command

```bash
/plugin install topo-tools --marketplace https://ocha-dap.github.io/topo-tools-py/marketplace.json
```

### Option 3: install from VS Code

[Click here](vscode://anthropic.claude-code/install-plugin?plugin=topo-tools&marketplace=https%3A%2F%2Focha-dap.github.io%2Ftopo-tools-py%2Fmarketplace.json) to open the Manage plugins dialog at the install step. For more information, see [Install plugins in VS Code](https://code.claude.com/docs/en/vs-code#install-plugins).

### Turn on automatic updates

After option 2 or 3, paste this prompt into Claude Code (CLI or VS Code), then restart:

```text
In ~/.claude/settings.json, set "autoUpdate": true on the "topo-tools" entry
under "extraKnownMarketplaces". If the entry is missing, add it with
"source": {"source": "url", "url": "https://ocha-dap.github.io/topo-tools-py/marketplace.json"}.
Keep all other settings, then tell me to restart Claude Code.
```
