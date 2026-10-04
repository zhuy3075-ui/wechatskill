#!/usr/bin/env python3
"""Export memory/materials.md cards to a CSV file."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ENTRY_RE = re.compile(r"^\s*-\s*\[(M-\d{3})\]\s*(.+?)\s*$")
FIELD_RE = re.compile(r"^\s*([^:：]+)\s*[:：]\s*(.*)$")
HEADING_RE = re.compile(r"^##\s*(.+?)\s*$")

KEY_MAP = {
    "来源": "source",
    "赛道": "track",
    "适用类型": "use_type",
    "标签": "tags",
    "质量分": "quality",
    "添加日期": "added_date",
    "已用于": "used_in",
}

CSV_COLUMNS = [
    "id",
    "category",
    "summary",
    "source",
    "track",
    "use_type",
    "tags",
    "quality",
    "added_date",
    "used_in",
]


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"Cannot decode file: {path}")


def parse_materials(markdown: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    category = ""
    in_comment = False
    in_fence = False

    for raw_line in markdown.splitlines():
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
        if entry_match:
            if current:
                rows.append(current)
            current = {column: "" for column in CSV_COLUMNS}
            current["id"] = entry_match.group(1).strip()
            current["summary"] = entry_match.group(2).strip()
            current["category"] = category
            continue

        if not current:
            continue

        field_match = FIELD_RE.match(line)
        if field_match:
            key = field_match.group(1).strip()
            value = field_match.group(2).strip()
            mapped_key = KEY_MAP.get(key)
            if mapped_key:
                current[mapped_key] = value

    if current:
        rows.append(current)

    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export memory/materials.md to a CSV file."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path("memory/materials.md"),
        help="Input markdown file path",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("memory/materials.csv"),
        help="Output CSV path",
    )
    args = parser.parse_args()

    content = read_text(args.input)
    rows = parse_materials(content)
    write_csv(rows, args.output)
    print(f"Exported {len(rows)} materials to {args.output}")


if __name__ == "__main__":
    main()
