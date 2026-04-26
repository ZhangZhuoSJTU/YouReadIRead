---
name: paper-data
description: Use when listing the to-read queue or any paper subset, editing paper metadata (status, labels, one-liner), changing read/archive status outside a /read session, viewing tracked groups/topics, syncing the data repo to git, or running first-run setup. Triggers include "/todo", "/list", "/done", "/archive", "/sync", "show my queue", "what am I tracking?", "remove this paper", "I finished reading X", "mark X read", "archive that paper", "push my data", "skip this one not going to read it".
---

# paper-data

## Overview

Listing, editing, status changes, syncing, and first-run setup for You Read,
I Read. All edits go through `scripts/manage_data.py`. Personal state lives
at `~/.you-read-i-read/data/`.

## Hard rules

- **Single writer.** Every change to the data repo goes through
  `manage_data.py`. Never edit `papers/index.json` / `tracking/*.yaml` /
  `preferences/*` by hand.
- **`/sync` never pushes without confirmation** unless
  `data_repo.auto_push: true` in `~/.you-read-i-read/config.yaml`.
- **`/done` and `/archive` always confirm the matched paper before flipping
  status when invoked with a query.** Id form may flip immediately;
  user must see the title first.
- **First run never asks for an Apify token** unless the user is enabling
  Twitter or LinkedIn.

## First-run flow

Triggered by `/sync init` or auto-detected when any data-touching command
runs and user state is missing.

1. **Detect.** `~/.you-read-i-read/config.yaml` missing OR `data_repo.path`
   doesn't exist OR `papers/index.json` missing.
2. **Copy** `defaults/config.yaml` → `~/.you-read-i-read/config.yaml` if
   absent.
3. **Prompt for `data_repo.remote`** (e.g.
   `git@github.com:ZhangZhuoSJTU/you-read-i-read-data.git`). Validate basic
   shape. Write back to user config.
4. **Offer `gh repo create --private`** if the remote doesn't yet exist
   (skip if `gh` not on PATH).
5. **Scaffold** the data dir — bootstrap touches:
   `papers/index.json: {}`, `tracking/groups.yaml: {groups: []}`,
   `tracking/topics.yaml: {topics: []}`,
   `tracking/state.json: {groups: {}, topics: {}}`,
   `preferences/signals.jsonl: ""`, `preferences/taxonomy.yaml: ""`.
6. **Commit and offer initial push.** `git -C ~/.you-read-i-read/data init`
   if needed; first commit; ask before pushing.

## Listing playbook

- **`/todo [<query>]`** — to-read queue, ranked.
  ```
  manage_data.py paper-list --status to-read --sort relevance --limit 25
  ```
  Append `--query "<query>"` if non-empty. Render as compact table:
  `id | title | one-liner | tags | added`.

- **`/list [filters]`** — general browser. Pass user's flags through to
  `paper-list`. Supported: `--status`, `--tag` (repeatable), `--author`,
  `--since YYYY-MM-DD`, `--query`, `--sort {added,relevance,read_at}`,
  `--limit`. Default `--status any --sort added --limit 50`.

## Status-change playbook

### `/done [<id> | <query>]`

- **Id form** (matches `^(arxiv|s2|doi|url)-`):
  ```
  manage_data.py paper-update <id> --status read
  manage_data.py signal-log --event read_finished --paper-id <id>
  ```
- **Query form**: search across `to-read` + `reading`:
  ```
  manage_data.py paper-list --query "<q>"  # filter to to-read|reading client-side
  ```
  Show top matches, **confirm**, then run the id form.

### `/archive [<id> | <query>]`

Same shape, but `--status archived` and
`signal-log --event archived_without_reading`. Optionally ask for a reason;
pass `--field reason="..."` so the preference model learns *why*.

## Sync playbook (`/sync`)

1. `git -C ~/.you-read-i-read/data status --short`. If clean, tell user; stop.
2. `git -C ... diff --stat`. Show.
3. **Confirm:** "Commit and push? (yes / message / no)".
4. **Stage + commit** with a descriptive message naming what changed
   (`update: <N> new papers, <M> summaries, <K> tracking changes`).
5. **Push** only with confirmation OR `data_repo.auto_push: true`.

`/sync status` shows adapter health + Apify spend (read
`tracking/apify-spend.yaml` + last-success per source from recent signals).

## Common mistakes

- Editing `papers/index.json` by hand — schema drifts. Always
  `manage_data.py`.
- Pushing the data repo without confirmation.
- Auto-flipping status from a query match without showing the user the
  matched paper.
- Asking for an Apify token at first run.
- Forgetting to log a `read_finished` / `archived_without_reading` signal
  on `/done` / `/archive`.
