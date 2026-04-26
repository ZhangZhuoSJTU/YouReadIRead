---
description: Browse all papers with filters (status, tag, author, since, query).
argument-hint: [--status read|to-read|reading|archived|any] [--tag X] [--author X] [--since YYYY-MM-DD] [--query "..."] [--sort added|relevance|read_at] [--limit N]
---

Show papers per the user's filters: $ARGUMENTS

Use the `paper-data` skill. Pass arguments straight through to
`python3 scripts/manage_data.py paper-list ...`. Default behavior (when no
flags are given): `--status any --sort added --limit 50`. Render as a table.
