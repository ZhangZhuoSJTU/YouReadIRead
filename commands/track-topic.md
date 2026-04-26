---
description: Track a topic across arXiv, Semantic Scholar, HN, and (opt-in) Twitter/LinkedIn.
argument-hint: <topic>
---

The user wants to track this topic: $ARGUMENTS

Use the `paper-curate` skill. Distill the topic into per-source queries —
one per **enabled** source in `~/.you-read-i-read/config.yaml`. Show the
queries to the user and **confirm before saving**. Persist via
`python3 scripts/manage_data.py topic-add --display-name "..." --query source=arxiv,q=... --query source=semantic_scholar,q=...`.
Initialize the watermark.
Optionally offer a seed pull of the top ~5 recent matches to bootstrap the
to-read list.
