# You Read, I Read — Agent Invariants and Routing

## 1. What this is

**You Read, I Read** (slug: `you-read-i-read`) is a Claude Code plugin that helps the user read and track research papers, blogs, and technical reports. It runs as a persistent agentic workspace: the user talks to Claude in a running session; the agent fetches, summarizes, triages, and reads alongside them. No separate UI exists — the Claude Code session *is* the interface.

## 2. Where things live

- **Plugin tree** (`~/Code/YouReadIRead`, this repo) — read-only logic: skills, agents, commands, helper scripts, defaults. Safe to make public.
- **User state** at `~/.you-read-i-read/`:
  - `config.yaml` — copied from `defaults/config.yaml` on first run, then user-edited.
  - `data/` — a separate private git repo containing `papers/index.json`, `papers/summaries/`, `tracking/`, and `preferences/`.
- **Personal data never leaks into the plugin tree.** This rule is hard.
- Full data layout: `docs/data-schema.md`.

## 3. Hard rules

- Never write personal state (papers, tracking config, signals, summaries) into the plugin tree. Always write to `~/.you-read-i-read/data/` via `scripts/manage_data.py`.
- Never `git push` the user's data repo without explicit confirmation, unless `data_repo.auto_push: true`.
- Never auto-add candidates during `/update` in `interactive` mode (the default). The user's per-card decision is the primary signal.
- Never silently transition a paper from `reading` → `read`. Always require an explicit user choice: the in-session "Done" menu, the end-of-session prompt, or `/done`.
- Never advance a tracked source's watermark when that source's adapter errored on this sweep.
- Never ask the user for an Apify token unless they are enabling Twitter or LinkedIn.
- Cite section/page references when quoting numbers from a paper (`§4.2, Table 3`). Hedge ("authors report") when you can't verify.
- The user is the senior decision-maker. When in doubt, ask.

## 4. Routing — natural language vs slash commands

Slash commands are sugar; the primary interface is plain English to the running session. Each skill's description lists the NL phrasings that trigger it.

| Phrasing | Skill | Slash |
|---|---|---|
| "add this paper `<url>`" / "summarize and save this" | paper-curate | `/add` |
| "track Stanford NLP" / "follow this group" | paper-curate | `/track-group` |
| "follow papers on LLM agents" / "watch this topic" | paper-curate | `/track-topic` |
| "what's new since last week?" / "check for new papers" | paper-curate | `/update` |
| "let's read something" | paper-read | `/read` |
| "I want to read about tool use" | paper-read | `/read tool use` |
| "what's on my to-read list?" | paper-data | `/todo` |
| "show me everything I read this month" | paper-data | `/list --status read --since …` |
| "I finished reading X" / "mark X read" / "I read this" | paper-data | `/done` |
| "skip this one" / "not going to read it" | paper-data | `/archive` |
| "push my data" / "sync" | paper-data | `/sync` |

## 5. Skill responsibilities

**paper-curate** owns `/add`, `/track-group`, `/track-topic`, `/update`. Two-tier summarization is the core invariant: never deep-summarize during `/update` triage (abstract-only quick summaries only). Deep summarization happens on `/add` or when the user picks `[r]ead-now` on a triage card. Every accept/reject during triage logs a preference signal. Watermarks advance only after the user has fully triaged a source's candidates.

**paper-read** owns `/read`. Always loads the structured summary first; drills into raw text by quoting with section/page references; menu-driven interaction. Marks status `reading` on entry. Explicit end-of-session prompt before any status flip: `Did you finish reading <title>? [y]es / [n]ot yet / [a]rchive without finishing`. If the user dismisses without answering, status remains `reading`. When `/read` receives free-form text, it searches across to-read papers by title + one-liner + tags and lets the user pick.

**paper-data** owns `/todo`, `/list`, `/done`, `/archive`, `/sync`, ad-hoc edits, and first-run setup. Every edit goes through `manage_data.py`. `/done` is for "I read this outside a session" — it logs `read_finished`. `/archive` logs `archived_without_reading`. `/sync` never pushes without confirmation unless `data_repo.auto_push: true`.

## 6. Source-tier selection rule

Per source, on each sweep, pick the highest tier whose prerequisites are met:

```
if APIFY_TOKEN present and within budget cap:    Tier 1 (Apify MCP tool)
elif superpowers-chrome:browsing skill loaded:   Tier 2 (logged-in Chrome)
elif Tier 3 defined (Twitter only — Nitter):     Tier 3 (WebFetch via Nitter mirror)
else:                                            skip with plain message
```

Tell the user which tier ran on each source in `/sync status`. Never silently scrape — surface the tier choice. Watermarks do not advance for sources that errored.

## 7. Two-tier summarization

| Tier | When | Source | Where stored |
|---|---|---|---|
| `quick_summary` | During `/track-*` discovery and every `/update` sweep | Abstract / metadata only | `papers/index.json:one_liner` |
| `deep_summary` | On `/add` or `[r]ead-now` | Full text (PDF body, HTML body) | `papers/summaries/<id>.md` (7-section template) |

Hard rule: `/update` runs entirely on abstracts. Token cost stays proportional to the user's decisions, not the crawler's output.

## 8. Summary template

Seven sections with word budgets from `summary.max_words_per_section` in config:

1. **Motivation** (≤120 w) — what real-world problem makes this matter?
2. **Problem statement** (≤120 w) — formally / precisely.
3. **Challenge** (≤120 w) — why is it hard? what did prior work fail at?
4. **Insight** (≤80 w) — the key idea in 1–2 sentences.
5. **Tech details** (≤250 w) — the method, distilled.
6. **Evaluation** (≤150 w) — datasets, baselines, headline numbers.
7. **Important takeaways** (≤120 w) — 2–4 bullets.

Additional rules: hedge if only the abstract is available ("abstract only — full evaluation not available"); cite `(§4.2, Table 3)` when quoting numbers; the `one_liner` describes *novelty*, not topic.

## 9. Preference-learning rule (LLM-prompt-driven)

The agent does preference scoring **in-context** during `/update`. It reads the tail of `~/.you-read-i-read/data/preferences/signals.jsonl` (last ~100 entries) directly into the ranking prompt. It optionally includes `preferences/preference-prompt.md` (a free-form user note, e.g. "prefer methods over benchmarks") verbatim. The LLM produces `accept_likelihood ∈ [0, 1]` per candidate with a one-line **rationale**; the rationale shows up in each triage card.

There are no tag buckets or similarity rings. The LLM judges everything in one pass from raw signal history.

`relevance` is a weighted blend:
```
relevance = w_p · accept_likelihood + w_r · recency + w_t · trending
```
Default weights: `(0.5, 0.2, 0.3)` from `config.preferences.ranking_weights`.

The **digested** `preferences/preference-state.yaml` is read only for deterministic threshold decisions — e.g. "suggest semi-auto mode?" (yes when `totals.accepted + totals.rejected >= 25`; full-auto at `>= 100`). The agent never edits this file directly; `manage_data.py signal-log` recomputes it atomically on every signal write.

## 10. First-run detection

When any data-touching command runs and `~/.you-read-i-read/config.yaml` is missing OR `data_repo.path` doesn't exist OR `papers/index.json` is missing:

1. Copy `defaults/config.yaml` → `~/.you-read-i-read/config.yaml` if absent.
2. Prompt for the data-repo remote URL (e.g. `git@github.com:ZhangZhuoSJTU/you-read-i-read-data.git`). Validate basic shape. Write to `data_repo.remote`.
3. Offer `gh repo create --private` if the remote doesn't yet exist.
4. Scaffold the data dir: `papers/index.json: {}`, `tracking/groups.yaml: {groups: []}`, `tracking/topics.yaml: {topics: []}`, `tracking/state.json: {groups: {}, topics: {}}`, empty `preferences/signals.jsonl`, `preferences/taxonomy.yaml`.
5. Copy the plugin's `defaults/data-repo-gitignore` to `~/.you-read-i-read/data/.gitignore` so `tracking/sessions/` (auth state) never enters git.
6. `git init` the data repo if needed; make the seed commit; ask before pushing.
7. Do not ask for an Apify token at first run. Ask only when the user later enables Twitter or LinkedIn.

## 11. When you don't know what to do

Ask. The user prefers a clarifying question over a wrong inference.
