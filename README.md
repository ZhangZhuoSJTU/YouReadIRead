<p align="center">
  <img src="assets/logo.svg" alt="You Read, I Read" width="540">
</p>

> **Talk to a persistent agent. It captures papers, tracks groups and topics, learns your taste, and reads with you.**

```
You: add this https://arxiv.org/abs/2401.12345
You: track Stanford NLP
You: any new papers since last week?
You: I want to read about tool use
You: I finished the tool-use paper
You: push my data
```

A Claude Code plugin. Install once, talk to it forever.

---

## What you can ask it

| You say | It does |
| --- | --- |
| "add this paper `<url>`" / `/add <url>` | Fetches, writes a 7-section structured summary, files it in your to-read list. |
| "track Stanford NLP" / `/track-group <name>` | Watches a group's publications over time. |
| "follow papers on LLM agents" / `/track-topic <topic>` | Watches a topic across arXiv + Semantic Scholar + HN (+ optional Twitter / LinkedIn). |
| "any new papers since last week?" / `/update` | Sweeps every tracked source, ranks, and triages with you per-card. |
| "let's read something" / `/read` | Recommends from the top of your queue, runs an interactive session. |
| "I want to read about tool use" / `/read tool use` | Searches your queue by keyword and picks a paper. |
| "what's on my to-read list?" / `/todo` | Shows the queue, ranked. |
| "show me everything I read this month" / `/list --status read --since …` | Browses any subset. |
| "I finished reading X" / `/done` | Marks read, logs the signal. |
| "skip this one" / `/archive` | Archives without reading. |
| "push my data" / `/sync` | Commits and pushes your private data repo. |

The agent learns from every accept / reject / read so the queue gradually self-curates. You stay in control — it never auto-adds in default mode, and it never marks a paper read without your explicit yes.

## Install

```
/plugin marketplace add ZhangZhuoSJTU/YouReadIRead
/plugin install you-read-i-read
/reload-plugins
```

The repo is a self-marketplace (`.claude-plugin/marketplace.json` at the root), so the two-step install works directly from GitHub. Local-dev variant: `marketplace add ~/Code/YouReadIRead`.

## First run

In any Claude Code session, say `/sync init` (or "set up You Read, I Read"). The agent will:

1. Copy `defaults/config.yaml` → `~/.you-read-i-read/config.yaml`.
2. Ask for a **data-repo remote URL** — a separate private git repo for your personal state (papers, summaries, preferences). Plugin tree never holds any of it.
3. Optionally `gh repo create --private` if the remote doesn't exist yet.
4. Scaffold the data dir (with its own `.gitignore` so auth caches stay local).

It will **not** ask for an Apify token here — that's deferred until you opt into Twitter or LinkedIn.

## Optional: Twitter / LinkedIn discovery (Apify)

Off by default. To enable, say "enable twitter" / "enable linkedin" and provide an [Apify](https://apify.com) API token when asked. Apify ships a $5/month free tier:

- Twitter (`apidojo/tweet-scraper`, $0.40 / 1k tweets) → ~$0.60/month — fits free tier.
- LinkedIn (`curious_coder/linkedin-post-search`, $5 / 1k posts) → ~$7.50/month — overshoots; tighten `tracking_sources.linkedin.max_per_sweep` or sweep less often.

The plugin caps spend per source per month (default `$5`) and skips calls when approached.

**Without Apify**, Twitter degrades to public Nitter mirrors (free, very flaky); LinkedIn skips silently. arXiv + Semantic Scholar + Hacker News cover the bulk of CS / ML signal regardless.

## How it's built

| Component | What it owns |
| --- | --- |
| `skills/paper-curate` | `/add`, `/track-group`, `/track-topic`, `/update` (ingest + sweep). |
| `skills/paper-read` | `/read` (interactive session, end-of-session prompt before any read flip). |
| `skills/paper-data` | `/todo`, `/list`, `/done`, `/archive`, `/sync`, first-run setup. |
| `agents/paper-summarizer` | Parallel summarization fanout. |
| `scripts/_common.py` | Config + paper IDs + atomic file ops. |
| `scripts/manage_data.py` | Single writer to the data repo (12 subcommands, 17 unit tests). |
| `scripts/apify-mcp-launch.sh` | Spawns the Apify MCP server when `APIFY_TOKEN` is set; no-op otherwise. |

Personal state lives in a separate private git repo at `~/.you-read-i-read/data/`. The plugin tree contains zero personal data.

For the data layout: `docs/data-schema.md`. For the agent's operating invariants: `CLAUDE.md`.

## License

MIT — see `LICENSE`.
