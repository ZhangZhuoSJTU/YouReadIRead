---
description: Mark a paper read (when finished outside a /read session).
argument-hint: [<id> | <keywords>]
---

The user has finished reading: $ARGUMENTS

Use the `paper-data` skill. If `$ARGUMENTS` matches an id pattern
(`^(arxiv|s2|doi|url)-`), run
`python3 scripts/manage_data.py paper-update <id> --status read` and
`python3 scripts/manage_data.py signal-log --event read_finished --paper-id <id>`.
Otherwise treat it as a keyword query: search across `to-read` and
`reading` papers via
`python3 scripts/manage_data.py paper-list --query "$ARGUMENTS"`,
present matches, **confirm the right one with the user** before flipping
status.
