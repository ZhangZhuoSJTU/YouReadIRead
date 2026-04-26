---
description: Commit and (with confirmation) push the private data repo.
argument-hint: [init | status]
---

The user wants to: $ARGUMENTS

Use the `paper-data` skill.

- **`/sync init`**: run first-run setup. Copy `defaults/config.yaml` →
  `~/.you-read-i-read/config.yaml`, prompt for `data_repo.remote`, scaffold
  data dirs, optionally `gh repo create --private` if `gh` is on PATH.

- **`/sync status`**: show adapter health (last successful tier per source)
  and Apify month-to-date spend (read `tracking/apify-spend.yaml`).

- **`/sync` (no args)**: show `git status --short` + `git diff --stat` from
  `~/.you-read-i-read/data/`. If clean, tell the user; stop. Otherwise
  confirm "Commit and push? (yes / message / no)". Stage + commit with a
  descriptive message naming what changed, appending a
  `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
  trailer (the data repo's content is largely Claude-authored). Push only
  with confirmation OR if `data_repo.auto_push: true` in user config.
