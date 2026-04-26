---
description: Start an interactive reading session. With no args, agent recommends. With <id>, that paper. With keywords, search.
argument-hint: [<id> | <keywords>]
---

Run a reading session over: $ARGUMENTS

Use the `paper-read` skill. If `$ARGUMENTS` is empty, recommend the top of
the ranked to-read list and confirm with the user. If it matches an id
pattern (`^(arxiv|s2|doi|url)-`), open that paper. Otherwise treat it as a
keyword query: run
`python3 scripts/manage_data.py paper-list --status to-read --query "$ARGUMENTS"`,
present the top matches, let the user pick. Always honor the
no-silent-status-flip rule and the explicit end-of-session prompt.
