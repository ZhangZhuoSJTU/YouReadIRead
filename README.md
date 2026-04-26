<table align="center" border="0" cellpadding="0" cellspacing="0">
  <tr>
    <td valign="middle" width="200" align="center">
      <img src="assets/icon.svg" alt="" width="160">
    </td>
    <td valign="middle" width="540">
      <h1>You Read, I Read</h1>
      <p>A persistent reading agent for <a href="https://claude.com/claude-code">Claude Code</a>.<br>
      You talk; it captures, tracks, learns your taste, and reads with you.</p>
      <pre><code>/plugin marketplace add ZhangZhuoSJTU/YouReadIRead
/plugin install you-read-i-read</code></pre>
    </td>
  </tr>
</table>

<p align="center">
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/license-MIT-1A2332?style=flat-square"></a>
  &nbsp;
  <img alt="version 0.1.0" src="https://img.shields.io/badge/version-0.1.0-5A6373?style=flat-square">
  &nbsp;
  <a href="https://docs.claude.com/en/docs/claude-code/plugins"><img alt="Claude Code plugin" src="https://img.shields.io/badge/Claude_Code-plugin-C97863?style=flat-square"></a>
  &nbsp;
  <img alt="Tracking sources: arXiv, Semantic Scholar, HN, Twitter, LinkedIn" src="https://img.shields.io/badge/tracks-arXiv_%C2%B7_S2_%C2%B7_HN_%C2%B7_X_%C2%B7_LinkedIn-4A6B9D?style=flat-square">
</p>

<hr>

```text
> add this https://arxiv.org/abs/2401.12345
✓ Filed: "Foo: Tool-Augmented Agents via Retrieval"  [tool-use, retrieval]

> track Stanford NLP
✓ Resolved 3 author IDs on Semantic Scholar; watching.

> any new papers since last week?
✓ 12 candidates across 2 topics. Triaging...

> I want to read about tool use
✓ 3 matches. Top: arxiv-2401.12345. Open?

> I finished the tool-use paper
✓ Marked read.

> push my data
✓ Committed 4 changes; pushed.
```

Install once, talk to it forever.

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

The agent learns from every accept, reject, and read, so the queue gradually self-curates. You stay in control: it never auto-adds in default mode, and it never marks a paper read without your explicit yes.

## First run

In any Claude Code session, say `/sync init` (or "set up You Read, I Read"). The agent will:

1. Copy `defaults/config.yaml` to `~/.you-read-i-read/config.yaml`.
2. Ask for a **data-repo remote URL**. This is a separate private git repo for your personal state (papers, summaries, preferences). The plugin tree never holds any of it.
3. Optionally `gh repo create --private` if the remote doesn't exist yet.
4. Scaffold the data dir (with its own `.gitignore` so auth caches stay local).

It will **not** ask for an Apify token here. That's deferred until you opt into Twitter or LinkedIn.

## Optional: Twitter / LinkedIn discovery (Apify)

Off by default. To enable, say "enable twitter" or "enable linkedin" and provide an [Apify](https://apify.com) API token when asked. Apify ships a $5/month free tier:

- Twitter (`apidojo/tweet-scraper`, $0.40 / 1k tweets) costs roughly $0.60/month at default sweep rates, which fits the free tier.
- LinkedIn (`curious_coder/linkedin-post-search`, $5 / 1k posts) costs roughly $7.50/month at default sweep rates, which overshoots. Tighten `tracking_sources.linkedin.max_per_sweep` or sweep less often.

The plugin caps spend per source per month (default `$5`) and skips calls when the cap is approached.

**Without Apify**, Twitter degrades to public Nitter mirrors (free, very flaky); LinkedIn skips silently. arXiv, Semantic Scholar, and Hacker News cover the bulk of CS / ML signal regardless.

## How it's built

<table>
  <tr>
    <td><b>Skills</b></td>
    <td>
      <code>paper-curate</code> (ingest + sweep) ·
      <code>paper-read</code> (interactive session, end-of-session prompt) ·
      <code>paper-data</code> (list / edit / sync / first-run)
    </td>
  </tr>
  <tr>
    <td><b>Subagent</b></td>
    <td><code>paper-summarizer</code> for parallel summarization fanout</td>
  </tr>
  <tr>
    <td><b>Helpers</b></td>
    <td>
      <code>scripts/_common.py</code> (config + paper IDs + atomic file ops) ·
      <code>scripts/manage_data.py</code> (single writer, 12 subcommands, 17 unit tests)
    </td>
  </tr>
  <tr>
    <td><b>MCP</b></td>
    <td><code>scripts/apify-mcp-launch.sh</code> spawns the Apify MCP server when <code>APIFY_TOKEN</code> is set; no-op otherwise</td>
  </tr>
  <tr>
    <td><b>State</b></td>
    <td>Personal data lives in a separate private git repo at <code>~/.you-read-i-read/data/</code>. Plugin tree contains zero personal data.</td>
  </tr>
</table>

For the data layout, see [`docs/data-schema.md`](docs/data-schema.md). For the agent's operating invariants, see [`CLAUDE.md`](CLAUDE.md).

## License

[MIT](LICENSE).
