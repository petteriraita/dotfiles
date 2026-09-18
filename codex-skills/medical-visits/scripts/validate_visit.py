#!/usr/bin/env python3
"""Validate one Obsidian medical-visit record and optionally its live API row."""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.request import urlopen

VAULT = Path("/home/pt/dev/obsidian_vault")
VISITS = VAULT / "2 - Areas/medical/conditions/hamstring2025/Visits"
FIELDS = ("date", "type", "clinician", "clinic", "evidence")
TYPES = {"doctor", "physiotherapy", "surgery", "nursing"}
EVIDENCE = {"clinical_record", "patient_report", "mixed", "translation"}


def fail(message: str) -> None:
    raise ValueError(message)


def scalar(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    if raw.startswith('"'):
        return json.loads(raw)
    return raw


def section(markdown: str, name: str) -> str:
    match = re.search(rf"^## {re.escape(name)}\s*\n(.*?)(?=^## |\Z)", markdown, re.M | re.S)
    return match.group(1).strip() if match else ""


def validate(path: Path) -> str:
    path = path.resolve()
    if path.parent != VISITS:
        fail(f"file must be directly inside {VISITS}")
    markdown = path.read_text(encoding="utf-8")
    if not markdown.startswith("---\n"):
        fail("YAML frontmatter must start at byte zero; nothing may precede it")
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", markdown, re.S)
    if not match:
        fail("frontmatter is missing its closing ---")

    values = {}
    for line in match.group(1).splitlines():
        item = re.fullmatch(r"([A-Za-z_]+):\s*(.*)", line)
        if not item:
            fail(f"invalid frontmatter line: {line!r}")
        key, raw = item.groups()
        if key not in FIELDS:
            fail(f"unexpected frontmatter field: {key}")
        if key in values:
            fail(f"duplicate frontmatter field: {key}")
        values[key] = scalar(raw)
    if tuple(values) != FIELDS:
        fail(f"frontmatter fields must be exactly, in order: {', '.join(FIELDS)}")
    if values["type"] not in TYPES:
        fail(f"invalid type: {values['type']!r}")
    if values["evidence"] not in EVIDENCE:
        fail(f"invalid evidence: {values['evidence']!r}")

    visit_date = values["date"]
    if visit_date:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", visit_date):
            fail(f"date must use YYYY-MM-DD: {visit_date!r}")
        try:
            date.fromisoformat(visit_date)
        except ValueError as error:
            fail(f"invalid date: {visit_date!r} ({error})")
    expected_name = (
        f"{visit_date or 'Undated'} - {values['type']} - "
        f"{values['clinician'] or 'clinician unrecorded'}.md"
    )
    if path.name != expected_name:
        fail(f"filename must be {expected_name!r}")

    for name in ("Summary", "Date evidence", "Source"):
        if not section(markdown, name):
            fail(f"missing or empty ## {name} section")
    return path.relative_to(VAULT).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--dashboard", action="store_true")
    args = parser.parse_args()
    try:
        source_path = validate(args.path)
        if args.dashboard:
            with urlopen("http://127.0.0.1:4173/api/visits", timeout=5) as response:
                rows = json.load(response).get("rows", [])
            if not any(row.get("sourcePath") == source_path for row in rows):
                fail(f"dashboard API does not contain {source_path}")
        print(f"OK: {source_path}")
        return 0
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
