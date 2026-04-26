# YouReadIRead — design spec

**Date:** 2026-04-26  ·  **Author:** Zhuo + Claude (collaborative brainstorm)
**Status:** awaiting user approval

## Goal

A persistent agentic system (a Claude Code session living on this repo) that helps
the user read and track research artifacts (papers, blogs, talks, technical
reports). The system:

1. captures a single artifact from a URL with a structured summary (`/add`),
2. tracks research groups and topics over time (`/track-group`, `/track-topic`),
3. sweeps tracked sources for new work and triages with the user (`/update`),
4. supports interactive reading sessions (`/read`),
5. learns the user's taste and gradually transitions from "ask every time" toward
   automatic labeling.

Personal data lives in a **separate private git repo**; this repo holds only
agentic logic and is safe to make public.

## Non-goals

- Building a UI. The interface is the persistent Claude Code session.
- Recreating Anthropic's prompt-caching plumbing — this system runs *as* a Claude
  Code session, not a custom Anthropic-SDK app.
- Comprehensive citation graph / co-citation analysis. Out of scope.
- Hosting summaries publicly. Personal data stays in a private repo.

## Design philosophy

**Light + agent-driven.** The agent does the work in-context. We add deterministic
helpers only when an operation is **both** common **and** reliable — i.e. it
happens dozens of times and the contract doesn't depend on the open web.

Concretely:
- **Deterministic (Python):** schema-touching CRUD against the data repo, ID
  derivation, config resolution, atomic file ops.
- **Agent-driven:** fetching, summarizing, ranking, parsing arbitrary HTML.
- **Hybrid (skill + scripted bootstrap):** browser-mediated source adapters for
  Twitter and LinkedIn — the agent drives the session, but a small Python helper
  fingerprints/refreshes the platform queryIds once per session.

## Architecture

```
YouReadIRead/                       ← agent code (this repo)
├── README.md
├── CLAUDE.md                       ← invariants and routing rules
├── config.yaml                     ← paths, sources, thresholds
├── docs/
│   ├── data-schema.md
│   └── superpowers/specs/…         ← this file
├── scripts/
│   ├── _common.py                  ← config + IDs + atomic file ops
│   └── manage_data.py              ← single writer to the data repo
└── .claude/
    ├── settings.json               ← permissions
    ├── skills/
    │   ├── paper-curate/SKILL.md   ← /add, /track-*, /update
    │   ├── paper-read/SKILL.md     ← /read
    │   └── paper-data/SKILL.md     ← /todo, /sync, edits
    ├── agents/
    │   └── paper-summarizer.md     ← parallel fanout subagent
    └── commands/
        ├── add.md
        ├── track-group.md
        ├── track-topic.md
        ├── update.md
        ├── read.md
        ├── todo.md
        └── sync.md
```

```
~/.youreadiread/data/               ← private data repo (separate)
├── papers/index.json               ← master index
├── papers/summaries/<id>.md        ← structured summary
├── tracking/groups.yaml
├── tracking/topics.yaml
├── tracking/state.json             ← per-source last-checked watermarks
├── tracking/sessions/              ← cached cookies + queryIds for adapters
├── preferences/taxonomy.yaml       ← agent's working tag list (for consistency)
└── preferences/signals.jsonl       ← append-only event log of accept/reject/read
```

### Skill responsibilities

| Skill | Owns | Invariants |
| --- | --- | --- |
| `paper-curate` | Ingestion: `/add`, `/track-group`, `/track-topic`, `/update`. | Every add → exactly one entry in `papers/index.json` and one summary file. `/update` may not advance a watermark before the user has triaged that source's candidates. Every accept/reject logs a signal. Confirmation required before persisting tracked groups/topics. |
| `paper-read` | Interactive reading session via `/read`. | Always loads the structured summary first. Drills into raw text by quoting with section/page references. Marks status `reading` on entry, `read` on exit. Logs `read_started` / `read_finished`. |
| `paper-data` | Listing, editing, syncing. `/todo`, `/sync`, ad-hoc edits. | All edits go through `manage_data.py`. `/sync` never pushes without confirmation (unless `data_repo.auto_push: true`). User-driven label edits log signals. |

Skills are written in **intent + invariants** style — they describe what must
remain true and link to the helpers that enforce it. They do not prescribe
step-by-step procedures; the agent composes the steps.

### Subagent

`paper-summarizer` — given a URL (and optional pre-fetched text), returns a
markdown summary in the canonical 7-section format. Used by `paper-curate` for
parallel fanout when `/update` returns ≥ 5 candidates. Capped at 8 concurrent.

Discovery (finding the candidates themselves) stays in-context — no
`paper-finder` subagent. Source adapters are short and the agent benefits from
seeing what was returned.

### Slash commands

Thin entry points; each one names the skill that owns it. They exist so the user
has a small explicit surface and the agent has unambiguous routing.

## Source-adapter layer

`/track-topic` and `/update` consult source adapters. Each adapter is a documented
contract — not a Python class — that the agent implements ad hoc. Common shape:

```
discover(query, since) → [
  { id, title, authors, source_url, published_at, snippet, signal }
]
```

`signal` carries source-specific context (HN points, Twitter-mention count in
follow graph, S2 citation velocity).

| Adapter | Mechanism | Stability | Notes |
| --- | --- | --- | --- |
| `arxiv` | `WebFetch` against `export.arxiv.org/api/query?search_query=<q>&sortBy=submittedDate` (Atom XML). | High. | Filter `<entry>` by `<published>` ≥ since. The agent assigns 1–3 tags from `preferences/taxonomy.yaml` to each candidate. |
| `semantic_scholar` | `WebFetch` against `api.semanticscholar.org/graph/v1/paper/search` (JSON). | High, with quota. | Use for group resolution (`/author/search`) and topic queries. |
| `hackernews` | `WebFetch` against `hn.algolia.com/api/v1/search_by_date?query=...&tags=story`. | High. | Filter by `points ≥ config.tracking_sources.hackernews.min_points`. |
| `twitter` | `browsing` skill drives logged-in Chrome; reads internal GraphQL endpoints (`UserTweets`, `SearchTimeline`). | Medium — queryIds rotate every 6–12 weeks. | At session bootstrap, fetch queryIds from `main.*.js` once and cache to `tracking/sessions/twitter.json`. Extract paper links by regexing `arxiv\.org/(abs|pdf)/\d{4}\.\d{4,5}` against `legacy.full_text` and `entities.urls[].expanded_url`. Trending heuristic per Smerity/trending_arxiv: count mentions inside the user's follow graph over the lookback window. Throttle ≥ 2 s between requests; back off on 429 with `x-rate-limit-reset`. Never hit notifications endpoints. |
| `linkedin` | `browsing` skill drives logged-in Chrome; reads Voyager endpoints under `/voyager/api/`. | Medium — Voyager rotates every 4–8 weeks; DOM rotates every 2–4 weeks, so prefer Voyager. | Use `li_at` + `JSESSIONID` cookies + `csrf-token` header (decode from `JSESSIONID`). Endpoint: `/voyager/api/feed/updates` and topic-search variants. Cap 50 posts per run. On Voyager rotation, fall back to `article` + `[data-id]` DOM selectors. |

**Fallbacks and graceful degradation.** When an adapter fails (rate limit, layout
change), the agent surfaces the failure to the user, skips that adapter for the
current sweep, and continues on others. The watermark for that source is
**not** advanced.

**Session bootstrap helper (Twitter only, optional).** A tiny script
`scripts/twitter_session.py` that, given an open Chrome session, scrapes the
current GraphQL queryIds from `main.*.js` and caches them. Justified because (a)
it runs every session and (b) regex-finding 6 IDs in a JS bundle is mechanical.
LinkedIn's cookie capture stays in-skill — it's one-time per session and varies
enough not to standardize.

## `/update` triage UX

Per-paper interactive card, sequential:

```
[12/40]  arxiv-2604.01234   relevance 0.82  (pref 0.71 · recency 0.93 · trend 0.85)
Foo: Tool-Augmented Agents via Retrieval
Alice A., Bob B., Carol C.   ·   via topic: LLM agents

One-liner: Adds a retrieval-then-act loop to a 7B base, gaining +14% on …

[a]dd   [s]kip   [r]ead-now   [?] more info   [q]uit  →
```

`relevance` is the blended score from `preferences.ranking_weights`. The
component subscores are shown so the user understands *why* a paper ranked
where it did.

- `a` → persist via `paper-add`, log `update_accepted`.
- `s` → log `update_rejected` (optional reason prompt).
- `r` → run `paper-add`, then immediately drop into `paper-read`.
- `?` → run a one-off summary (cache only, no persistence) and re-show the card.
- `q` → exit; advance watermarks only for sources fully triaged so far.

Triage modes (`config.yaml > update.mode`):

- `interactive` (default) — every candidate prompted.
- `semi-auto` — items with `relevance ≥ auto_add_relevance` (0.9) auto-added,
  items below `min_relevance_for_silent_add` (0.2) silently dropped, middle band
  prompted.
- `full-auto` — only high-relevance items auto-added; the rest dropped silently.
  Discouraged until ≥ 50 confirmed signals exist.

`relevance` is computed as a weighted blend of (a) `accept_likelihood` from the
preference model, (b) recency, (c) trending score from the source. See the
**Preference learning** section.

## Preference learning — accept-likelihood, not labels

What the system learns: **"would the user add this paper to their to-read
list?"** A single binary signal per candidate, sourced from `/update` triage
and reinforced by `read_finished` (paper actually read) and `archived` (added
but never read) events.

Labels/tags on individual papers are **agent-assigned** — the agent picks 1–3
short tags per paper from a working taxonomy it maintains in
`preferences/taxonomy.yaml` (free to add new tags; old tags are reused for
consistency). Labels exist for filtering and ranking, not for preference
learning.

**Scoring (in-context, light).** When `/update` produces N candidates, the
agent computes `accept_likelihood ∈ [0, 1]` per candidate by comparing each
to:

- the user's recent **accepted** papers (positive examples),
- the user's recent **rejected** papers (negative examples),
- the user's recent **read-and-finished** papers (strong positive examples),
- the **archived without reading** papers (mild negative — they were accepted
  but never opened).

Comparison is over `title + one_liner + agent-assigned tags + topic-of-origin`.
The agent does this directly; no embedding model in v1.

**`accept_likelihood` feeds `relevance`.** The blended ranking score becomes:

```
relevance = w_p · accept_likelihood
          + w_r · recency
          + w_t · trending
```

with weights from `config.preferences.ranking_weights`. Default
`(w_p, w_r, w_t) = (0.5, 0.2, 0.3)`.

**Gradual automation.** `/update.mode` controls how aggressively the system
acts on `accept_likelihood`:

| Mode | Below `min_relevance_for_silent_add` | Middle band | Above `auto_add_relevance` |
| --- | --- | --- | --- |
| `interactive` (default) | prompt | prompt | prompt |
| `semi-auto` | drop silently | prompt | auto-add silently |
| `full-auto` | drop silently | drop silently | auto-add silently |

`semi-auto` becomes useful once the user has ≥ 25 confirmed accept/reject
signals; `full-auto` once ≥ 100. The agent recommends a mode bump to the user
once thresholds are crossed; it never auto-flips the mode.

**Cold start.** With no signals, every candidate gets
`accept_likelihood = 0.5`. The user's first ~10 sweeps are doing pure ranking
by recency + trending, with the system silently accumulating signal.

## First-run setup

When any data-touching command runs and the data repo is uninitialized:

1. Detect: `data_repo.path` doesn't exist, OR `papers/index.json` missing.
2. Agent says: "Looks like first run. I'll create the data repo at
   `~/.youreadiread/data` and need a remote git URL to push to. What is it?"
3. User provides a URL (e.g. `git@github.com:ZhangZhuoSJTU/youreadiread-data.git`).
4. Agent validates basic shape, writes back to `config.yaml >
   data_repo.remote`, scaffolds the directory layout, and offers to
   `gh repo create --private` if the remote doesn't exist.

`config.yaml` ships with `data_repo.remote: null` — no GitHub handle is
hardcoded.

## Configuration

`config.yaml` — single source of truth, committed to git. Schema:

```yaml
data_repo:
  path: ~/.youreadiread/data
  remote: null                       # set on first run
  auto_push: false

tracking_sources:
  arxiv:           { enabled: true,  lookback_days: 14 }
  semantic_scholar:{ enabled: true,  lookback_days: 30 }
  hackernews:      { enabled: true,  min_points: 50 }
  twitter:         { enabled: false, seed_accounts: [] }   # opt-in; user says "enable twitter"
  linkedin:        { enabled: false }                       # opt-in; user says "enable linkedin"

summary:
  store_raw_content: true
  max_words_per_section:
    motivation: 120  problem_statement: 120  challenge: 120
    insight: 80      tech_details: 250       evaluation: 150
    takeaways: 120

preferences:
  ranking_weights: { accept_likelihood: 0.5, recency: 0.2, trending: 0.3 }

update:
  mode: interactive                  # interactive | semi-auto | full-auto
  auto_add_relevance: 0.9
  min_relevance_for_silent_add: 0.2
```

## Helpers (Python)

`scripts/_common.py` — config load, path resolve, stable paper-IDs, JSON/YAML/JSONL
atomic R/W. ~80 LOC.

`scripts/manage_data.py` — the **single** writer to the data repo. Subcommands:
`paper-add/get/list/update/set-summary`, `group-add/list`, `topic-add/list`,
`state-get/set-last-checked`, `signal-log`, `rank`, `auto-label-status`. ~150 LOC.

`scripts/twitter_session.py` (optional, lazy) — scrapes the current Twitter
GraphQL queryIds from `main.*.js` and writes
`tracking/sessions/twitter.json`. Only created when the user enables the
twitter source. ~50 LOC.

Total target Python LOC: **~280**.

## What gets removed from the current draft

- `scripts/fetch_paper.py` — agent uses `WebFetch` + `browsing` skill.
- `scripts/arxiv_search.py` — agent uses `WebFetch` against the arXiv API.
- `scripts/init_data_repo.py` — replaced by an inline first-run flow in
  `paper-data`.
- The 7 fine-grained skills under `.claude/skills/paper-*` — collapsed into 3.
- `scripts/manage_data.py` keeps its public interface but the file shrinks
  modestly (no behavior change for the 11 subcommands listed above).

## Risks and known limitations

- **Twitter/LinkedIn breakage.** Both rotate internals on the order of weeks.
  Mitigations: prefer GraphQL/Voyager over DOM, fingerprint queryIds at session
  start, fall back to DOM, surface failures to the user instead of failing
  silently. Accept that v1 will need occasional adapter touch-ups.
- **arXiv abstract-only summaries.** When `pdftotext` isn't available and the
  PDF body can't be read, summaries hedge in the `Evaluation` section. Acceptable.
- **Preference cold start.** With < 10 accept/reject signals, ranking is mostly
  recency + trending. Acceptable; matches user's "gradually" wording. The system
  recommends `semi-auto` once ≥ 25 signals exist.
- **In-context summarization is not cached.** Each summary costs full input
  tokens for the artifact. Could move to the Claude API with prompt caching
  later if cost matters; out of scope for v1.
- **Accept-likelihood scoring is in-context.** Each `/update` sweep compares
  every candidate against the user's recent accept/reject/read history. v1
  budgets ~50 candidates × the most recent ~100 signals. Beyond that, swap in a
  small embedding-based classifier or windowed history. Out of scope for v1.

## Acceptance criteria

The system is "v1-done" when:

1. `/add <arxiv-url>` produces a structured summary file and an index entry,
   end-to-end, in one command.
2. `/track-group "Stanford NLP"` resolves to ≥ 1 source and sets a watermark.
3. `/track-topic "LLM agents"` writes pluggable queries for each enabled source.
4. `/update` walks every tracked source, dedupes, and triages interactively.
5. `/read` runs an interactive session against an existing summary, with at
   least one menu drill-in.
6. `/todo` lists the to-read queue ranked by preference.
7. `/sync` commits and (with confirmation) pushes the data repo.
8. First-run prompt asks for `data_repo.remote` and persists it to `config.yaml`.
9. At least one Twitter-driven trending paper surfaces during a `/update` sweep
   on the user's logged-in session (manual verification).

## Open question for user

Approve this spec, or tell me what to change. After approval I'll invoke
`writing-plans` to generate a detailed implementation plan, then drive execution
off it.
