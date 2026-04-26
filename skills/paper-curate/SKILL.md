---
name: paper-curate
description: Use when adding a paper, blog, or report by URL, tracking a research group or topic, or sweeping tracked sources for new candidates. Triggers include "/add <url>", "/track-group", "/track-topic", "/update", "add this paper", "follow this group", "watch this topic", "any new papers since last week", "summarize and save this".
---

# paper-curate

## Overview

Ingestion skill. Flows: `/add`, `/track-group`, `/track-topic`, `/update` (sweep). State: `~/.you-read-i-read/data/`; never write to the plugin tree.

## Hard rules

- **Two-tier summarization.** Deep (7-section) only on `/add` and `[r]ead-now`. `/update` uses abstracts — never fetch PDFs in a sweep.
- **Confirm before persist.** Show resolved sources (S2 IDs, arXiv queries) before saving any tracked group/topic.
- **Watermarks don't advance for failing sources.** On error, `last_checked` stays put; retried next sweep.
- **Log every accept/reject.** `manage_data.py signal-log --event update_accepted|update_rejected`.

## Source-tier selection

Pick the highest tier available; tell the user which ran.

| Source | Tier 1 | Tier 2 | Tier 3 |
| --- | --- | --- | --- |
| arXiv | WebFetch Atom XML | — | — |
| Semantic Scholar | `semanticscholar` lib | WebFetch S2 API | — |
| Hacker News | WebFetch Algolia API | — | — |
| Twitter | Apify `apidojo/tweet-scraper`* | `superpowers-chrome:browsing` | Nitter WebFetch |
| LinkedIn | Apify `curious_coder/linkedin-post-search`* | `superpowers-chrome:browsing` | skip + message |

*Requires `APIFY_TOKEN` + budget.

## Per-flow playbooks

### `/add <url>`

1. Deep-summarize via **paper-summarizer** subagent. The subagent persists
   raw fetched content via `manage_data.py paper-set-raw <id> --ext ...`
   (txt for grounding, plus pdf when arXiv). Skipped if
   `summary.store_raw_content` is false.
2. `manage_data.py paper-add --url ... --title ... --authors ...`
3. `echo "$summary" | manage_data.py paper-set-summary <id>`
4. Confirm (id, title, one-liner, tags). Log `signal-log --event add_via_url`.

### `/track-group <name>`

Resolve to S2 author IDs. Confirm. `manage_data.py group-add`. `state-set-last-checked --kind groups --id <id>`.

### `/track-topic <topic>`

Distill to per-source queries. Confirm. `manage_data.py topic-add`. Init watermark.

### `/update`

Per source: (1) get watermark; (2) discover via highest tier; (3) dedupe against `papers/index.json`; (4) rank from `signals.jsonl` tail (~100) + `preference-prompt.md` — score `accept_likelihood ∈ [0,1]`, blend recency + trending weights; (5) triage:

```
[k/N] <id> rel=0.82 like=0.74 rec=0.93 trend=0.85
<Title> · <authors> · via: <topic>
One-liner: …  Why: <rationale>
[a]dd [s]kip [r]ead-now [?]info [q]uit →
```

Log on `a`/`s`. `?` fetches context, no persist. `r` → `/add` then `/read`. Advance watermark after full triage; `q` advances finished sources only.

## Subagent dispatch

The **paper-summarizer** subagent always produces a deep 7-section summary AND persists raw content. Dispatch only when that's the desired output:

- **`/add`**: dispatch one summarizer per URL.
- **`/update` `[r]ead-now`**: dispatch one summarizer for the chosen candidate, then drop into `/read`.
- **`/update` sweeps themselves**: do NOT dispatch the summarizer for one-liners. Source adapters return abstracts; derive the per-card one-liner in-context from the abstract. The `/update` sweep is two-tier-quick by definition.

When dispatching for parallel `/add` (rare in v1), cap at 8 concurrent.

## Common mistakes

- Deep-summarizing during `/update` (token-bombs sweep).
- Auto-adding candidates in interactive mode.
- Advancing a watermark for a failing source.
- Ranking from `preference-state.yaml` not `signals.jsonl` (digest lacks tag/exemplar data).
- Resolving an ambiguous group name without confirming.
