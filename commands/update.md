---
description: Sweep tracked sources for new papers since last check; triage with the user.
---

Run a `/update` sweep. Use the `paper-curate` skill. For every tracked
group + topic in `~/.you-read-i-read/data/tracking/`: read the watermark,
discover candidates via the highest available source-tier (Apify → browsing
→ Nitter → skip), dedupe against `papers/index.json`, then **rank in-context**
by reading the tail of `~/.you-read-i-read/data/preferences/signals.jsonl`
(last ~100 entries) plus optional `preferences/preference-prompt.md`,
producing `accept_likelihood` + rationale per candidate.

Triage with the user **per-card, sequentially** with the `[a]/[s]/[r]/[?]/[q]`
menu. Log signals on every accept / reject. Advance watermarks only for
sources fully triaged. **Never deep-summarize during this sweep** — quick
summary (abstract-only) only. Tell the user which tier ran on each source.
