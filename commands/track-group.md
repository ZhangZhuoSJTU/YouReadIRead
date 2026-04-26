---
description: Track a research group's publications.
argument-hint: <name or url>
---

The user wants to track this research group: $ARGUMENTS

Use the `paper-curate` skill. Resolve to concrete sources (prefer Semantic
Scholar author IDs; fall back to arXiv author query; last resort an HTML
publications page). **Confirm the resolved sources with the user before
persisting** — names like "Wei Wei" can match dozens of authors. Persist via
`python3 scripts/manage_data.py group-add --display-name "..." --source kind=...,id=...`.
Initialize the watermark with
`state-set-last-checked --kind groups --id <id>` so the first `/update`
doesn't flood. Optionally offer to seed the user's to-read list with the
group's most recent N papers.
