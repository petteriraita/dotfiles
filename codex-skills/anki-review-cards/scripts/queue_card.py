#!/usr/bin/env python3
"""Queue fields for the local Anki review bridge without saving a note."""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--field",
        action="append",
        required=True,
        help="A field value, in the order of the selected Anki note type. Repeat for each field.",
    )
    args = parser.parse_args()
    request = Request(
        "http://127.0.0.1:8766/populate",
        data=json.dumps({"fields": args.field}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=3) as response:
            print(response.read().decode())
    except URLError as exc:
        print(f"Anki review bridge unavailable: {exc.reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
