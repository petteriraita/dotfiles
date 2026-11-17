#!/usr/bin/env python3
"""Search saved Codex conversations, ordered by their last user message."""

import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

VERSION = 2
UUID = re.compile(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}")
IGNORE = (
    re.compile(r"^# AGENTS\.md instructions for "),
    re.compile(r"^</?INSTRUCTIONS>$"),
    re.compile(r"^</?environment_context>$"),
    re.compile(r"^  <(?:cwd|shell|current_date|timezone)>.*</(?:cwd|shell|current_date|timezone)>$"),
)


def usage():
    print("""Usage: cs [OPTIONS] SEARCH...

Search user/assistant text in saved Codex sessions, newest last user message first.
Separate terms must all occur in the same discussion.

  cs 'exact words'          literal phrase
  cs carle doctor           both terms
  cs -r 'words? [0-9]+'     regular expression
  cs '/words? [0-9]+/'      regular expression, Obsidian-style

Options:
  -r, --regex   treat terms as regular expressions
  -F, --fixed   treat terms as literal strings (default)
  -h, --help    show this help""")


def parse_args(argv):
    if not argv or argv[0] in ("-h", "--help"):
        usage()
        return None
    mode = "fixed"
    slash_regex = True
    if argv[0] in ("-r", "--regex"):
        mode, argv = "regex", argv[1:]
    elif argv[0] in ("-F", "--fixed"):
        slash_regex, argv = False, argv[1:]
    elif argv[0] == "--":
        argv = argv[1:]
    elif argv[0].startswith("-"):
        raise ValueError(f"unknown option: {argv[0]}")
    if not argv:
        raise ValueError("missing search term")
    if mode == "fixed" and slash_regex and len(argv) == 1 and len(argv[0]) >= 2 and argv[0].startswith("/") and argv[0].endswith("/"):
        mode, argv = "regex", [argv[0][1:-1]]
    return [re.compile(term if mode == "regex" else re.escape(term), re.IGNORECASE) for term in argv]


def timestamp(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return 0.0


def cached_database(home):
    path = home / "cache" / "cs.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=2)
    if db.execute("PRAGMA user_version").fetchone()[0] != VERSION:
        db.execute("DROP TABLE IF EXISTS files")
        db.execute(f"PRAGMA user_version = {VERSION}")
    db.execute("""CREATE TABLE IF NOT EXISTS files (
        path TEXT PRIMARY KEY, inode INTEGER NOT NULL, offset INTEGER NOT NULL,
        mtime_ns INTEGER NOT NULL, session_id TEXT, started_at REAL NOT NULL,
        last_user_at REAL NOT NULL, text TEXT NOT NULL
    )""")
    return db


def scan_file(path, previous):
    stat = path.stat()
    if previous and stat.st_ino == previous[1] and stat.st_size == previous[2] and stat.st_mtime_ns == previous[3]:
        return None
    incremental = bool(previous and stat.st_ino == previous[1] and stat.st_size > previous[2])
    offset = previous[2] if incremental else 0
    sid = previous[4] if incremental else None
    started_at = previous[5] if incremental else 0.0
    last_user_at = previous[6] if incremental else 0.0
    chunks = [previous[7]] if incremental and previous[7] else []
    with path.open("rb") as stream:
        stream.seek(offset)
        while True:
            start = stream.tell()
            line = stream.readline()
            if not line:
                break
            if not line.endswith(b"\n"):
                stream.seek(start)
                break
            offset = stream.tell()
            try:
                row = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            kind = row.get("type")
            payload = row.get("payload") or {}
            if kind == "session_meta":
                sid = payload.get("id") or sid
                started_at = started_at or timestamp(payload.get("timestamp") or row.get("timestamp"))
            elif kind == "response_item" and payload.get("type") == "message":
                role = payload.get("role")
                if role not in ("user", "assistant"):
                    continue
                parts = [item.get("text", "") for item in payload.get("content", [])
                         if item.get("type") in ("input_text", "output_text", "text") and isinstance(item.get("text"), str)]
                for part in parts:
                    if role == "user" and part.lstrip().startswith((
                        "# AGENTS.md instructions", "<environment_context>", "<skill>"
                    )):
                        continue
                    if role == "user":
                        last_user_at = max(last_user_at, timestamp(row.get("timestamp")))
                    lines = [s for s in part.splitlines() if not any(p.match(s) for p in IGNORE)]
                    if lines:
                        chunks.append("\n".join(lines))
    if not sid:
        found = UUID.search(path.name)
        sid = found.group() if found else path.stem
    return (str(path), stat.st_ino, offset, stat.st_mtime_ns, sid, started_at,
            last_user_at, "\n".join(chunks))


def refresh(db, home):
    root = home / "sessions"
    if not root.is_dir():
        raise FileNotFoundError(f"sessions dir not found: {root}")
    previous = {row[0]: row for row in db.execute("SELECT * FROM files")}
    seen = set()
    for path in root.rglob("*.jsonl"):
        key = str(path)
        seen.add(key)
        try:
            result = scan_file(path, previous.get(key))
        except FileNotFoundError:
            continue
        if result:
            db.execute("INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?)", result)
    for key in previous.keys() - seen:
        db.execute("DELETE FROM files WHERE path=?", (key,))
    db.commit()


def last_user_history(home):
    latest = {}
    path = home / "history.jsonl"
    if not path.exists():
        return latest
    with path.open() as stream:
        for line in stream:
            try:
                row = json.loads(line)
                sid, ts = row.get("session_id"), row.get("ts")
                if sid and isinstance(ts, (int, float)):
                    latest[sid] = max(latest.get(sid, 0), ts)
            except ValueError:
                continue
    return latest


def highlight(line, patterns):
    spans = []
    for pattern in patterns:
        spans.extend((m.start(), m.end()) for m in pattern.finditer(line) if m.end() > m.start())
    if not spans:
        return line
    spans.sort()
    merged = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    out, pos = [], 0
    for start, end in merged:
        out.extend((line[pos:start], "\033[1;31m", line[start:end], "\033[0m"))
        pos = end
    out.append(line[pos:])
    return "".join(out)


def context_lines(text, patterns):
    lines = text.splitlines()
    selected = set()
    for pattern in patterns:
        count = 0
        for i, line in enumerate(lines):
            if pattern.search(line):
                selected.update(range(max(0, i - 2), min(len(lines), i + 3)))
                count += 1
                if count >= 2:
                    break
    output = []
    previous = -2
    for i in sorted(selected):
        if i > previous + 1:
            output.append("--")
        output.append(f"{i + 1}-" + highlight(lines[i], patterns))
        previous = i
    return "\n".join(output)


def search(db, home, patterns):
    groups = defaultdict(lambda: {"parts": [], "paths": [], "last": 0, "started": 0})
    for path, _, _, _, sid, started, last, text in db.execute("SELECT * FROM files"):
        group = groups[sid]
        group["parts"].append((started, path, text))
        group["paths"].append(path)
        group["last"] = max(group["last"], last)
        group["started"] = group["started"] or started
    history = last_user_history(home)
    matches = []
    for sid, group in groups.items():
        text = "\n".join(part[2] for part in sorted(group["parts"]))
        if not text or not all(p.search(text) for p in patterns):
            continue
        ts = max(group["last"], history.get(sid, 0)) or group["started"]
        matches.append((ts, sid, group, text))
    for ts, sid, group, text in sorted(matches, key=lambda row: (-row[0], row[1])):
        date = datetime.fromtimestamp(ts).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z") if ts else "unknown"
        print(f"\n\033[1;36mcodexa {sid}\033[0m")
        print(f"\033[2mlast user message: {date}\033[0m")
        print(f"\033[2mfile: {group['paths'][0]}\033[0m")
        print(context_lines(text, patterns))


def main():
    try:
        patterns = parse_args(sys.argv[1:])
        if patterns is None:
            return 0
    except (ValueError, re.error) as error:
        print(f"cs: {error}\nTry cs --help for usage.", file=sys.stderr)
        return 2
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    try:
        os.umask(0o077)
        with cached_database(home) as db:
            refresh(db, home)
            search(db, home, patterns)
    except (OSError, sqlite3.Error) as error:
        print(f"cs: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
