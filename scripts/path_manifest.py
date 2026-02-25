#!/usr/bin/env python3
"""Scan a directory and generate file-id mapping for path-safe processing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate file manifest with stable IDs (Chinese path friendly)."
    )
    parser.add_argument("--dir", type=Path, required=True, help="Target directory")
    parser.add_argument("--pattern", type=str, default="*.txt", help="Glob pattern")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("memory/file-manifest.json"),
        help="Manifest output path",
    )
    args = parser.parse_args()

    target = args.dir
    if not target.exists() or not target.is_dir():
        raise SystemExit(f"目录无效: {target}")

    files = sorted(target.glob(args.pattern))
    manifest = []
    for idx, path in enumerate(files, start=1):
        file_id = f"F{idx:03d}"
        manifest.append(
            {
                "file_id": file_id,
                "name": path.name,
                "path": str(path.resolve()),
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "directory": str(target.resolve()),
                "pattern": args.pattern,
                "count": len(manifest),
                "files": manifest,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"wrote: {args.output} (count={len(manifest)})")


if __name__ == "__main__":
    main()
