---
description: Mark a paper archived (decision: not going to read).
argument-hint: [<id> | <keywords>]
---

The user wants to archive: $ARGUMENTS

Use the `paper-data` skill. With an id (`^(arxiv|s2|doi|url)-`):
`paper-update <id> --status archived` and
`signal-log --event archived_without_reading --paper-id <id>`. With a query:
search across `to-read` and `reading`, present matches, **confirm before
flipping**. Optionally ask the user for a one-line reason and pass it
through `signal-log --field reason="..."` so the preference model learns
*why*.
