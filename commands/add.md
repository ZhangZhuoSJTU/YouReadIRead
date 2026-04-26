---
description: Add a paper or blog from a URL. Fetches, deep-summarizes, files to to-read.
argument-hint: <url>
---

The user wants to add the following URL to their to-read list with a deep
structured summary: $ARGUMENTS

Use the `paper-curate` skill. Workflow: fetch + deep-summarize via the
`paper-summarizer` subagent → persist via
`python3 scripts/manage_data.py paper-add --url ... --title ... --authors ...`
→ pipe summary body via `... paper-set-summary <id>` → confirm with the user
(id, title, one-liner, agent-suggested tags) → log
`signal-log --event add_via_url --paper-id <id>`. Detect first-run conditions
and run setup before any of this if `~/.you-read-i-read/config.yaml` is
missing.
