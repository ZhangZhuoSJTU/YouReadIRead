#!/usr/bin/env python3
"""CRUD over the You Read, I Read private data repo. Single writer.

Subcommands documented in `scripts/manage_data.py --help`. Output is JSON on
stdout for easy consumption by the agent.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make _common importable.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    append_jsonl,
    data_repo_path,
    ensure_data_repo,
    now_iso,
    paper_id_for,
    read_json,
    read_yaml,
    slugify,
    write_json,
    write_yaml,
)


# ---------- path helpers ----------

def _papers_index_path() -> Path:
    return ensure_data_repo(create_dirs=True) / "papers" / "index.json"


def _summary_path(paper_id: str) -> Path:
    return ensure_data_repo() / "papers" / "summaries" / f"{paper_id}.md"


def _emit(value):
    json.dump(value, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


# ---------- paper subcommands ----------

def paper_add(args):
    index = read_json(_papers_index_path(), default={})
    pid = args.id or paper_id_for(args.url)
    entry = index.get(pid, {})
    entry.update({
        "id": pid,
        "title": args.title or entry.get("title", ""),
        "authors": args.authors if args.authors is not None else entry.get("authors", []),
        "venue": args.venue or entry.get("venue", ""),
        "year": args.year if args.year is not None else entry.get("year"),
        "source_url": args.url,
        "added_date": entry.get("added_date") or now_iso(),
        "added_via": args.via or entry.get("added_via", "url"),
        "labels": sorted(set((entry.get("labels") or []) + (args.labels or []))),
        "auto_tags": entry.get("auto_tags", []),
        "status": args.status or entry.get("status", "to-read"),
        "one_liner": args.one_liner if args.one_liner is not None else entry.get("one_liner", ""),
        "summary_path": entry.get("summary_path", f"papers/summaries/{pid}.md"),
        "preference_score": entry.get("preference_score"),
        "read_log": entry.get("read_log", []),
    })
    index[pid] = entry
    write_json(_papers_index_path(), index)
    _emit(entry)


def paper_get(args):
    index = read_json(_papers_index_path(), default={})
    entry = index.get(args.id)
    if entry is None:
        sys.stderr.write(f"No such paper: {args.id}\n")
        sys.exit(1)
    _emit(entry)


def paper_list(args):
    index = read_json(_papers_index_path(), default={})
    items = list(index.values())

    if args.status and args.status != "any":
        items = [p for p in items if p.get("status") == args.status]
    for tag in args.tag or []:
        items = [p for p in items if tag in (p.get("labels") or []) + (p.get("auto_tags") or [])]
    if args.author:
        a = args.author.lower()
        items = [p for p in items
                 if any(a in (au or "").lower() for au in p.get("authors") or [])]
    if args.since:
        items = [p for p in items if (p.get("added_date") or "") >= args.since]
    if args.query:
        q = args.query.lower()
        def hay(p):
            return " ".join([
                (p.get("title") or "").lower(),
                (p.get("one_liner") or "").lower(),
                " ".join((p.get("labels") or []) + (p.get("auto_tags") or [])).lower(),
            ])
        items = [p for p in items if q in hay(p)]

    sort_key = args.sort or "added"
    if sort_key == "added":
        items.sort(key=lambda p: p.get("added_date", ""), reverse=True)
    elif sort_key == "relevance":
        items.sort(key=lambda p: p.get("preference_score") or 0.0, reverse=True)
    elif sort_key == "read_at":
        def last_read(p):
            log = p.get("read_log") or []
            return log[-1].get("finished_at", "") if log else ""
        items.sort(key=last_read, reverse=True)

    if args.limit:
        items = items[: args.limit]
    _emit(items)


def paper_update(args):
    index = read_json(_papers_index_path(), default={})
    entry = index.get(args.id)
    if entry is None:
        sys.stderr.write(f"No such paper: {args.id}\n")
        sys.exit(1)
    if args.status:
        entry["status"] = args.status
    if args.title is not None:
        entry["title"] = args.title
    if args.one_liner is not None:
        entry["one_liner"] = args.one_liner
    if args.add_label:
        entry["labels"] = sorted(set((entry.get("labels") or []) + args.add_label))
    if args.remove_label:
        entry["labels"] = [l for l in entry.get("labels", []) if l not in args.remove_label]
    if args.preference_score is not None:
        entry["preference_score"] = args.preference_score
    index[args.id] = entry
    write_json(_papers_index_path(), index)
    _emit(entry)


def paper_set_summary(args):
    body = sys.stdin.read()
    path = _summary_path(args.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    _emit({"id": args.id, "summary_path": str(path.relative_to(data_repo_path()))})


# ---------- argparse ----------

def main():
    p = argparse.ArgumentParser(prog="manage_data.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("paper-add")
    pa.add_argument("--url", required=True)
    pa.add_argument("--id")
    pa.add_argument("--title")
    pa.add_argument("--authors", nargs="*")
    pa.add_argument("--venue")
    pa.add_argument("--year", type=int)
    pa.add_argument("--label", dest="labels", action="append")
    pa.add_argument("--status", choices=["to-read", "reading", "read", "archived"])
    pa.add_argument("--via")
    pa.add_argument("--one-liner", dest="one_liner")
    pa.set_defaults(func=paper_add)

    pg = sub.add_parser("paper-get"); pg.add_argument("id"); pg.set_defaults(func=paper_get)

    pl = sub.add_parser("paper-list")
    pl.add_argument("--status", default="any",
                    choices=["to-read", "reading", "read", "archived", "any"])
    pl.add_argument("--tag", action="append")
    pl.add_argument("--author")
    pl.add_argument("--since")
    pl.add_argument("--query")
    pl.add_argument("--sort", choices=["added", "relevance", "read_at"], default="added")
    pl.add_argument("--limit", type=int)
    pl.set_defaults(func=paper_list)

    pu = sub.add_parser("paper-update")
    pu.add_argument("id")
    pu.add_argument("--status", choices=["to-read", "reading", "read", "archived"])
    pu.add_argument("--title")
    pu.add_argument("--one-liner", dest="one_liner")
    pu.add_argument("--add-label", action="append")
    pu.add_argument("--remove-label", action="append")
    pu.add_argument("--preference-score", type=float)
    pu.set_defaults(func=paper_update)

    ps = sub.add_parser("paper-set-summary")
    ps.add_argument("id")
    ps.set_defaults(func=paper_set_summary)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
