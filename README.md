# You Read, I Read

A persistent agentic Claude Code plugin that helps you read and track research
papers, blogs, and reports. You talk to it; it captures, tracks, learns your
taste, and runs interactive reading sessions.

## Capabilities

| Slash | What it does | Plain-English |
| --- | --- | --- |
| `/add <url>` | Fetch and deep-summarize a paper / blog / PDF; file in to-read. | "add this paper https://…" |
| `/track-group <name or url>` | Watch a research group's publications over time. | "track Stanford NLP" |
| `/track-topic <topic>` | Watch a topic across arXiv, Semantic Scholar, HN, optionally Twitter/LinkedIn. | "follow papers on LLM agents" |
| `/update` | Sweep tracked sources for new candidates and triage them with you per-card. | "any new papers since last week?" |
| `/read [<id> \| <keywords>]` | Interactive reading session. Search by keyword or pick by id. | "let's read something" / "I want to read about tool use" |
| `/todo [<keywords>]` | List the to-read queue, ranked. | "what's on my to-read list?" |
| `/list [filters]` | Browse all papers (status / tag / author / since / query). | "show me everything I read this month" |
| `/done [<id> \| <keywords>]` | Mark a paper read (when finished outside a session). | "I finished reading the tool-use paper" |
| `/archive [<id> \| <keywords>]` | Mark a paper archived (decision: not going to read). | "skip this one, I'm not going to read it" |
| `/sync` | Commit and push the private data repo (with confirmation). | "push my data" |

## Install

```
/plugin marketplace add ZhangZhuoSJTU/YouReadIRead
/plugin install you-read-i-read
/reload-plugins
```

For local development:

```
/plugin marketplace add ~/Code/YouReadIRead   # local file path
/plugin install you-read-i-read
/reload-plugins
```

## First run

After install, in any Claude Code session, say `/sync init` (or "set up You Read, I Read"). The agent will:

1. Copy `defaults/config.yaml` → `~/.you-read-i-read/config.yaml`.
2. Ask for a **data-repo remote URL** (e.g. `git@github.com:ZhangZhuoSJTU/you-read-i-read-data.git`). This is a *separate, private* git repo for your personal state (papers, summaries, preferences). It's never bundled into this plugin.
3. Optionally `gh repo create --private` if the remote doesn't yet exist.
4. Scaffold the data dir.

It will **not** ask for an Apify token here — that's deferred until you actually want Twitter/LinkedIn discovery.

## Optional: Twitter and LinkedIn discovery (Apify)

These social sources are off by default. To enable, say "enable twitter" (or `/list-sources`, `/track-source twitter`, etc.) and provide an Apify API token when prompted.

Apify offers a **free tier of $5/month** in usage credits. At default sweep rates:

- Twitter (apidojo/tweet-scraper, $0.40 / 1k tweets) → ~$0.60/month — fits free tier.
- LinkedIn (curious_coder/linkedin-post-search, $5 / 1k posts) → ~$7.50/month — overshoots; tighten via `tracking_sources.linkedin.max_per_sweep` or sweep less often.

The plugin **caps spend per source per month** (default `$5`); calls are skipped when the cap is approached.

## Without Apify

Twitter falls back to public Nitter mirrors (free, very flaky). LinkedIn requires Apify or a logged-in browser-skill session — without those, it's skipped silently with a one-line note. **arXiv, Semantic Scholar, and Hacker News work fully zero-cost regardless** and cover the bulk of CS / ML signal.

## Architecture (quick)

- **3 skills**: `paper-curate` (ingest + sweep), `paper-read` (interactive reading), `paper-data` (list + edit + sync + first-run).
- **1 subagent**: `paper-summarizer` (parallel summarization).
- **2 Python helpers**: `scripts/_common.py` (config + IDs + atomic file ops), `scripts/manage_data.py` (single writer to the data repo).
- **MCP server**: Apify (auto-spawned via `scripts/apify-mcp-launch.sh`; idle when no token, real otherwise).

User personal state lives in a **separate private git repo** at `~/.you-read-i-read/data/`. The plugin tree (this repo) contains zero personal data.

See `docs/data-schema.md` for the data-repo layout and `CLAUDE.md` for the agent's operating invariants.

## License

MIT. See `LICENSE`.

## Repo

`https://github.com/ZhangZhuoSJTU/YouReadIRead` (placeholder if not yet pushed).
