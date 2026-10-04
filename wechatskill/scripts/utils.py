#!/usr/bin/env python3
"""Shared helpers for scripts."""

from __future__ import annotations

from pathlib import Path


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"Cannot decode file: {path}")
