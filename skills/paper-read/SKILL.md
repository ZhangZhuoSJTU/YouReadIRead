---
name: paper-read
description: Use when starting an interactive reading session over a paper. Triggers include "/read", "/read <id>", "/read <keywords>", "let's read something", "I want to read about <topic>", "let's read X", "show me a paper to read". The agent picks from the to-read queue, loads the structured summary, walks through it menu-driven, drills into raw text on request.
---

# paper-read

## Overview

Interactive reading skill. Owns `/read [<id> | <keywords>]`. Loads the
structured summary, hooks the user with motivation + insight, lets them
choose how deep to go, grounds custom questions in the raw text. Marks
status correctly only when the user explicitly says they're done.

## Hard rules

- **Always load the structured summary first.** Read
  `~/.you-read-i-read/data/papers/summaries/<id>.md`. If absent, run a deep
  summary first via the `paper-summarizer` subagent and persist before
  proceeding.
- **Never transition `reading → read` silently.** Status flips only via:
  - the in-session `[5] Done — mark read` menu choice, OR
  - the **end-of-session prompt** below.
  If the user dismisses without answering, status stays `reading`.
- **Ground custom questions in the raw text.** Open
  `~/.you-read-i-read/data/papers/raw/<id>.txt` (or `.html` / `.pdf`) and
  quote with `(§4.2, Table 3)`-style references. If the answer isn't in
  the source, say so plainly.
- **Log session boundaries.** `signal-log --event read_started` on entry,
  `--event read_finished` on confirmed read.

## Workflow

1. **Pick the paper.**
   - `/read <id>` → that paper.
   - `/read <keywords>` → search via
     `manage_data.py paper-list --status to-read --query "<keywords>"`,
     present top matches, let user choose.
   - `/read` (no args) → recommend the top of the ranked queue from
     `manage_data.py rank --status to-read --limit 5`. Briefly justify
     ("highest accept_likelihood + trending"). Confirm.

2. **Mark `reading`** and log `read_started`:
   ```bash
   manage_data.py paper-update <id> --status reading
   manage_data.py signal-log --event read_started --paper-id <id>
   ```

3. **Hook.** One paragraph synthesizing the summary's `Motivation` +
   `Insight`. End with the source URL.

4. **Menu.** Offer:
   ```
   [1] Tech details (the method)
   [2] Evaluation (numbers + ablations)
   [3] Open the paper in browser  → <source_url>
   [4] Ask my own question
   [5] Done — mark read
   [q] Pause for now (status stays `reading`)
   ```

5. **Drill.** On `[1]` / `[2]`, render the relevant summary section, then
   offer to go deeper from raw text. On `[4]`, ground in raw text and
   answer with section/page references.

6. **Finish.** When the user picks `[5]` (or signals they're done):
   ```bash
   manage_data.py paper-update <id> --status read
   manage_data.py signal-log --event read_finished --paper-id <id> --field duration_seconds=<approx>
   ```
   Optionally accept a free-form note for `read_log`.

7. **End-of-session prompt.** If the user picks `[q]` or otherwise exits
   without `[5]`, **explicitly ask** before closing:
   `Did you finish reading <title>? [y]es / [n]ot yet / [a]rchive without finishing`.
   - `y` → mark `read`, log `read_finished`.
   - `n` → status stays `reading`, no signal logged.
   - `a` → mark `archived`, log `archived_without_reading` (optional reason).

## Recommendation rationale

When `/read` has no argument, justify the pick in one line:
*"highest accept_likelihood (0.82); trending +0.45 on HN today"* or
*"added 6 days ago — going stale"*. The user can override with
`/read <other-id>`.

## Common mistakes

- Auto-marking `read` because the user said "thanks" — wait for explicit
  yes / `[5]`.
- Answering custom questions from the summary alone when raw text exists
  — always go to raw text for non-trivial questions.
- Skipping the end-of-session prompt when the user says "later" — that
  leaves the paper at `reading` forever.
- Forgetting to log signals.
