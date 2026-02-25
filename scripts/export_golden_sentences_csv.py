#!/usr/bin/env python3
"""Export memory/golden-sentences.md to CSV."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
ENTRY_RE = re.compile(
    r'^\s*-\s*[「"](.*?)[」"]\s*[-—–]+\s*出自[《<](.*?)[》>]\s*\((\d{4}-\d{2}-\d{2})\)\s*(?:\[已用\s*(\d+)\s*次\])?\s*$'
)

CSV_COLUMNS = [
    "category",
    "sentence",
    "source_title",
    "date",
    "used_count",
]


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"Cannot decode file: {path}")


def parse_markdown(content: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    category = ""
    in_comment = False
    in_fence = False

    for raw_line in content.splitlines():
        line = raw_line.rstrip()

        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if "<!--" in line:
            in_comment = True
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            category = heading_match.group(1).strip()
            continue

        entry_match = ENTRY_RE.match(line)
        if not entry_match:
            continue

        rows.append(
            {
                "category": category,
                "sentence": entry_match.group(1).strip(),
                "source_title": entry_match.group(2).strip(),
                "date": entry_match.group(3).strip(),
                "used_count": (entry_match.group(4) or "0").strip(),
            }
        )

    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export memory/golden-sentences.md to a CSV file."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path("memory/golden-sentences.md"),
        help="Input markdown file path",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("memory/golden-sentences.csv"),
        help="Output CSV path",
    )
    args = parser.parse_args()

    content = read_text(args.input)
    rows = parse_markdown(content)
    write_csv(rows, args.output)
    print(f"Exported {len(rows)} golden sentences to {args.output}")


if __name__ == "__main__":
    main()
