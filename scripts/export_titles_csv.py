#!/usr/bin/env python3
"""Export memory/titles.md archive entries to CSV."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ENTRY_RE = re.compile(r"^###\s*\[(\d{4}-\d{2}-\d{2})\]\s*(.+?)\s*$")
FIELD_RE = re.compile(r"^\s*-\s*\*\*([^*]+)\*\*\s*[:：]\s*(.*)$")
SUB_FIELD_RE = re.compile(r"^\s*-\s*([^:：]+)\s*[:：]\s*(.*)$")

KEY_MAP = {
    "最终标题": "final_title",
    "备选标题": "candidate_titles",
    "用户修改": "user_change",
    "文章类型": "article_type",
    "使用的标题技巧": "title_technique",
    "使用的雷击要素": "hook_elements",
    "效果评级": "rating",
}

METRIC_KEY_MAP = {
    "阅读量": "reads",
    "打开率": "open_rate",
    "分享数": "shares",
}

CSV_COLUMNS = [
    "date",
    "topic",
    "final_title",
    "candidate_titles",
    "user_change",
    "article_type",
    "reads",
    "open_rate",
    "shares",
    "title_technique",
    "hook_elements",
    "rating",
]


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"Cannot decode file: {path}")


def parse_titles(markdown: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_comment = False
    in_fence = False
    parsing_metrics = False

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

        entry_match = ENTRY_RE.match(line)
        if entry_match:
            if current:
                rows.append(current)
            current = {column: "" for column in CSV_COLUMNS}
            current["date"] = entry_match.group(1).strip()
            current["topic"] = entry_match.group(2).strip()
            parsing_metrics = False
            continue

        if not current:
            continue

        field_match = FIELD_RE.match(line)
        if field_match:
            key = field_match.group(1).strip()
            value = field_match.group(2).strip()

            if key == "效果数据":
                parsing_metrics = True
                continue

            parsing_metrics = False
            mapped_key = KEY_MAP.get(key)
            if mapped_key:
                current[mapped_key] = value
            continue

        if parsing_metrics:
            sub_field_match = SUB_FIELD_RE.match(line)
            if sub_field_match:
                metric_key = sub_field_match.group(1).strip()
                metric_value = sub_field_match.group(2).strip()
                mapped_key = METRIC_KEY_MAP.get(metric_key)
                if mapped_key:
                    current[mapped_key] = metric_value

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
    parser = argparse.ArgumentParser(description="Export memory/titles.md to CSV.")
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path("memory/titles.md"),
        help="Input markdown file path",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("memory/titles.csv"),
        help="Output CSV path",
    )
    args = parser.parse_args()

    content = read_text(args.input)
    rows = parse_titles(content)
    write_csv(rows, args.output)
    print(f"Exported {len(rows)} title records to {args.output}")


if __name__ == "__main__":
    main()
