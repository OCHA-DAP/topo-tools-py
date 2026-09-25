---
title: For agents
description: Ways to start a topo-tools session with an agent, plugin install or pasted prompt.
---

## Claude Code plugin

Install the [`topo-tools`](https://github.com/OCHA-DAP/topo-tools-py/blob/main/plugins/topo-tools) plugin to clean, code, and package COD-AB administrative boundary polygons. Follow the tab for where you use Claude Code.

=== "VS Code (Claude Code panel)"

    1. [Click here](vscode://anthropic.claude-code/install-plugin?plugin=topo-tools&marketplace=https%3A%2F%2Focha-dap.github.io%2Ftopo-tools-py%2Fmarketplace.json), allow the browser to open VS Code, confirm adding the marketplace, then select **Install for you**.
    2. Turn on automatic updates. In VS Code, select **File > Open File** and open your settings file:

        - **Windows:** `%USERPROFILE%\.claude\settings.json`
        - **macOS:** `~/.claude/settings.json`

        Add `"autoUpdate": true` to the `topo-tools` entry, with a comma on the line before:

        ```json hl_lines="6-7"
        "extraKnownMarketplaces": {
          "topo-tools": {
            "source": {
              "source": "url",
              "url": "https://ocha-dap.github.io/topo-tools-py/marketplace.json"
            },
            "autoUpdate": true
          }
        }
        ```

    3. Start a new Claude Code session with the new-session button.
    4. Open an empty folder and run `/topo-tools:cod-ab`.

=== "Terminal (`claude` command)"

    1. In a Claude Code session, run:

        ```text
        /plugin install topo-tools --marketplace https://ocha-dap.github.io/topo-tools-py/marketplace.json
        ```

        Confirm adding the marketplace, then select **Install for you**. If Claude Code shows `Run /reload-plugins to activate`, run it.

    2. Turn on automatic updates: run `/plugin`, open the **Marketplaces** tab, select **topo-tools**, then select **Enable auto-update**.
    3. Open an empty folder and run `/topo-tools:cod-ab`.

## Other agents

Paste this into the agent's prompt:

```text
Read https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/plugins/topo-tools/skills/cod-ab/SKILL.md,
then follow it to clean and reconcile a COD-AB administrative boundary layer.
```
