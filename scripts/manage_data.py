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


def paper_set_raw(args):
    """Persist raw fetched content to papers/raw/<id>.<ext>.

    Body comes from --file (a path on disk) or stdin (binary-safe). Used by
    the paper-summarizer agent to keep an offline copy for grounding /read
    follow-up questions.
    """
    if args.file:
        body = Path(args.file).read_bytes()
    else:
        body = sys.stdin.buffer.read()
    repo = ensure_data_repo(create_dirs=True)
    out_path = repo / "papers" / "raw" / f"{args.id}.{args.ext}"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(body)
    _emit({
        "id": args.id,
        "raw_path": str(out_path.relative_to(data_repo_path())),
        "bytes": len(body),
    })


# ---------- tracking path helpers ----------

def _groups_path() -> Path:
    return ensure_data_repo(create_dirs=True) / "tracking" / "groups.yaml"


def _topics_path() -> Path:
    return ensure_data_repo(create_dirs=True) / "tracking" / "topics.yaml"


def _state_path() -> Path:
    return ensure_data_repo(create_dirs=True) / "tracking" / "state.json"


def _kv_list(items):
    out = {}
    for item in items or []:
        if "=" not in item:
            sys.stderr.write(f"Expected key=value, got {item!r}\n"); sys.exit(2)
        k, v = item.split("=", 1)
        out[k] = v
    return out


# ---------- group subcommands ----------

def group_add(args):
    groups = read_yaml(_groups_path(), default={"groups": []})
    gid = args.id or slugify(args.display_name)
    sources = [_kv_list(s.split(",")) for s in (args.source or [])]
    new = {"id": gid, "display_name": args.display_name,
           "sources": sources, "added_date": now_iso()}
    groups["groups"] = [g for g in groups.get("groups", []) if g.get("id") != gid] + [new]
    write_yaml(_groups_path(), groups)
    _emit(new)


def group_list(args):
    _emit(read_yaml(_groups_path(), default={"groups": []}))


# ---------- topic subcommands ----------

def topic_add(args):
    topics = read_yaml(_topics_path(), default={"topics": []})
    tid = args.id or slugify(args.display_name)
    queries = {}
    for q in args.query or []:
        kv = _kv_list(q.split(","))
        if "source" in kv and "q" in kv:
            queries[kv["source"]] = kv["q"]
    new = {"id": tid, "display_name": args.display_name,
           "queries": queries, "added_date": now_iso()}
    topics["topics"] = [t for t in topics.get("topics", []) if t.get("id") != tid] + [new]
    write_yaml(_topics_path(), topics)
    _emit(new)


def topic_list(args):
    _emit(read_yaml(_topics_path(), default={"topics": []}))


# ---------- state subcommands ----------

def state_get_last_checked(args):
    state = read_json(_state_path(), default={"groups": {}, "topics": {}})
    bucket = state.get(args.kind, {})
    _emit(bucket.get(args.id, {"last_checked": None}))


def state_set_last_checked(args):
    state = read_json(_state_path(), default={"groups": {}, "topics": {}})
    state.setdefault(args.kind, {})[args.id] = {"last_checked": now_iso()}
    write_json(_state_path(), state)
    _emit(state[args.kind][args.id])


# ---------- signals + preference state ----------

POSITIVE_EVENTS = {"update_accepted", "read_finished"}
NEGATIVE_EVENTS = {"update_rejected", "archived_without_reading"}


def _signals_path() -> Path:
    return ensure_data_repo(create_dirs=True) / "preferences" / "signals.jsonl"


def _preference_state_path() -> Path:
    return ensure_data_repo(create_dirs=True) / "preferences" / "preference-state.yaml"


def _recommend_mode(totals: dict) -> str:
    n = totals.get("signals", 0)
    if n >= 100:
        return "full-auto"
    if n >= 25:
        return "semi-auto"
    return "interactive"


def _recompute_preference_state():
    """Walk signals.jsonl, recompute totals + recommended_mode. Idempotent.

    Preference scoring is done LLM-prompt-driven by the agent (it reads the
    tail of signals.jsonl directly), so no tag-buckets or recent-rings live
    here — only what's needed for deterministic threshold decisions.
    """
    state = {
        "totals": {"signals": 0, "accepted": 0, "rejected": 0,
                   "read_finished": 0, "archived_without_reading": 0},
        "recommended_mode": "interactive",
        "last_recomputed": now_iso(),
    }
    sig_path = _signals_path()
    if not sig_path.exists():
        write_yaml(_preference_state_path(), state); return

    with sig_path.open() as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            evt = rec.get("event")
            state["totals"]["signals"] += 1
            if evt == "update_accepted":
                state["totals"]["accepted"] += 1
            elif evt == "update_rejected":
                state["totals"]["rejected"] += 1
            elif evt == "read_finished":
                state["totals"]["read_finished"] += 1
            elif evt == "archived_without_reading":
                state["totals"]["archived_without_reading"] += 1

    state["recommended_mode"] = _recommend_mode(state["totals"])
    write_yaml(_preference_state_path(), state)


def signal_log(args):
    record = {"ts": now_iso(), "event": args.event}
    if args.paper_id:
        record["paper_id"] = args.paper_id
    record.update(_kv_list(args.field))
    append_jsonl(_signals_path(), record)
    _recompute_preference_state()
    _emit(record)


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

    psr = sub.add_parser("paper-set-raw")
    psr.add_argument("id")
    psr.add_argument("--ext", required=True,
                     choices=["html", "txt", "pdf", "md"],
                     help="Extension for the raw file written under papers/raw/.")
    psr.add_argument("--file", help="Path to read body from. Otherwise stdin (binary).")
    psr.set_defaults(func=paper_set_raw)

    ga = sub.add_parser("group-add")
    ga.add_argument("--id"); ga.add_argument("--display-name", required=True)
    ga.add_argument("--source", action="append")
    ga.set_defaults(func=group_add)
    sub.add_parser("group-list").set_defaults(func=group_list)

    ta = sub.add_parser("topic-add")
    ta.add_argument("--id"); ta.add_argument("--display-name", required=True)
    ta.add_argument("--query", action="append")
    ta.set_defaults(func=topic_add)
    sub.add_parser("topic-list").set_defaults(func=topic_list)

    sg = sub.add_parser("state-get-last-checked")
    sg.add_argument("--kind", required=True, choices=["groups", "topics"])
    sg.add_argument("--id", required=True)
    sg.set_defaults(func=state_get_last_checked)

    ss = sub.add_parser("state-set-last-checked")
    ss.add_argument("--kind", required=True, choices=["groups", "topics"])
    ss.add_argument("--id", required=True)
    ss.set_defaults(func=state_set_last_checked)

    sl = sub.add_parser("signal-log")
    sl.add_argument("--event", required=True)
    sl.add_argument("--paper-id")
    sl.add_argument("--field", action="append", default=[])
    sl.set_defaults(func=signal_log)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
