"""Shared helpers: config loading, path resolution, ID generation, atomic file ops.

Single source of truth for path/ID conventions. Imported by manage_data.py
and any future script.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML required: pip install pyyaml (or `uv pip install pyyaml`)\n")
    raise

# Plugin root = parent of this scripts/ directory.
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
USER_CONFIG_DIR = Path.home() / ".you-read-i-read"
USER_CONFIG_PATH = USER_CONFIG_DIR / "config.yaml"
DEFAULT_CONFIG_PATH = PLUGIN_ROOT / "defaults" / "config.yaml"


def _read_yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def load_config() -> dict:
    """Load the user's config, falling back to the plugin default if absent.

    Note: the first-run flow (in paper-data) is responsible for *copying*
    the default to the user path on first invocation. This function silently
    falls back so unit tests don't require ~/.you-read-i-read/.
    """
    if USER_CONFIG_PATH.exists():
        return _read_yaml(USER_CONFIG_PATH)
    return _read_yaml(DEFAULT_CONFIG_PATH)


def data_repo_path() -> Path:
    cfg = load_config()
    raw = cfg.get("data_repo", {}).get("path", "~/.you-read-i-read/data")
    return Path(os.path.expanduser(raw)).resolve()


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return text[:64] or "item"


def paper_id_for(url: str) -> str:
    """Stable slug ID for a paper given its source URL."""
    url = url.strip()
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})(?:v\d+)?", url)
    if m:
        return f"arxiv-{m.group(1)}"
    m = re.search(r"semanticscholar\.org/paper/([0-9a-f]{40})", url)
    if m:
        return f"s2-{m.group(1)[:16]}"
    m = re.search(r"doi\.org/([^\s?#]+)", url)
    if m:
        sanitized = re.sub(r"[^a-zA-Z0-9.\-]+", "-", m.group(1)).strip("-")
        return f"doi-{sanitized}"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return f"url-{digest}"


def ensure_data_repo(create_dirs: bool = False) -> Path:
    path = data_repo_path()
    if not path.exists():
        if not create_dirs:
            sys.stderr.write(
                f"Data repo not found at {path}. Run first-run setup or change "
                f"`data_repo.path` in {USER_CONFIG_PATH}.\n"
            )
            sys.exit(2)
        path.mkdir(parents=True, exist_ok=True)
    if create_dirs:
        for sub in ("papers", "papers/summaries", "papers/raw",
                    "tracking", "tracking/sessions", "preferences"):
            (path / sub).mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path, default):
    if not path.exists():
        return default
    with path.open() as f:
        return json.load(f)


def write_json(path: Path, value) -> None:
    """Atomic JSON write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def read_yaml(path: Path, default):
    if not path.exists():
        return default
    with path.open() as f:
        return yaml.safe_load(f) or default


def write_yaml(path: Path, value) -> None:
    """Atomic YAML write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        yaml.safe_dump(value, f, sort_keys=False, allow_unicode=True)
    os.replace(tmp, path)


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record, sort_keys=True))
        f.write("\n")
