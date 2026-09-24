---
name: review-cod-ab-validation
description: Use when the user asks to see or review a cod-ab skill validation run (its session text, transcript, or workspace files) in a separate workspace directory.
---

# Review a cod-ab validation run

Get the workspace path from the user if they haven't given it. Claude Code stores that workspace's transcripts in `~/.claude/projects/<path with every non-alphanumeric character replaced by ->/`, one `.jsonl` per session. The newest by mtime is the current run. Requires `jq`.

Print the conversation text (user and assistant messages, no tool calls or results):

```bash
ws=<workspace path>
dir=~/.claude/projects/$(printf %s "$ws" | sed 's|[^A-Za-z0-9]|-|g')
f=$(ls -t "$dir"/*.jsonl | head -1)
jq -r 'select(.type=="user" or .type=="assistant") | .type as $r
  | .message.content
  | if type=="string" then "[\($r)] \(.)"
    else (.[] | select(.type=="text") | "[\($r)] \(.text)") end' "$f"
```

To see which tools ran, drop the `select(.type=="text")` filter.

Workspace files: `ls -la "$ws"`.

The workspace and transcripts are read-only. Never add a CLAUDE.md or other context files to the workspace.
