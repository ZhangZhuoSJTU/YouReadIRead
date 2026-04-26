---
description: List the to-read queue, ranked. Optional query filters.
argument-hint: [<keywords>]
---

Show the to-read queue. Use the `paper-data` skill. Run
`python3 scripts/manage_data.py paper-list --status to-read --sort relevance --limit 25`,
appending `--query "$ARGUMENTS"` if non-empty. Render as a compact table:
`id | title | one-liner | tags | added`.
