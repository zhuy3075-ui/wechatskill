#!/usr/bin/env python3
"""Format article output as markdown/json/both/wechat."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from utils import read_text


def detect_title(lines: list[str]) -> str:
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            return re.sub(r"^#+\s*", "", s).strip()
    for line in lines:
        s = line.strip()
        if s:
            return s[:80]
    return ""


def detect_summary(text: str) -> str:
    m = re.search(r"(?:摘要|summary)[：:]\s*(.+)", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    for p in paragraphs:
        if p.startswith("#"):
            continue
        if re.match(r"^(标题|文章标题|备选标题)[：:]", p, flags=re.IGNORECASE):
            continue
        clean = re.sub(r"^#+\s*", "", p).strip()
        if clean:
            return clean[:60]
    return ""


def detect_tags(text: str) -> list[str]:
    m = re.search(r"(?:关键词标签|标签|tags?)[：:]\s*(.+)", text, flags=re.IGNORECASE)
    if not m:
        return []
    raw = m.group(1)
    tags = []
    for t in re.split(r"[，,\s#]+", raw):
        t = t.strip()
        if t:
            tags.append(t)
    return tags[:8]


def extract_sections(lines: list[str]) -> list[dict]:
    sections: list[dict] = []
    current = {"heading": "", "content": []}
    for line in lines:
        s = line.rstrip()
        if s.strip().startswith("##"):
            if current["heading"] or current["content"]:
                sections.append(
                    {
                        "heading": current["heading"],
                        "content": "\n".join(current["content"]).strip(),
                    }
                )
            current = {"heading": re.sub(r"^##+\s*", "", s.strip()), "content": []}
        else:
            current["content"].append(s)
    if current["heading"] or current["content"]:
        sections.append(
            {
                "heading": current["heading"],
                "content": "\n".join(current["content"]).strip(),
            }
        )
    return [s for s in sections if s["heading"] or s["content"]]


def to_wechat_plain(text: str) -> str:
    """Convert markdown-ish article to WeChat editor friendly plain text."""
    out: list[str] = []
    in_code = False
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code = not in_code
            continue

        if in_code:
            out.append(line)
            continue

        if not stripped:
            out.append("")
            continue

        cleaned = re.sub(r"^#{1,6}\s*", "", line).strip()
        cleaned = re.sub(r"^>\s*", "", cleaned)
        cleaned = re.sub(r"^\s*[-*]\s+", "• ", cleaned)
        cleaned = cleaned.replace("**", "").replace("__", "")
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
        out.append(cleaned)

    return "\n".join(out).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Format article output into md/json/both/wechat.")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Input article markdown")
    parser.add_argument("-o", "--output", type=Path, default=Path("outputs"), help="Output directory")
    parser.add_argument(
        "--mode",
        choices=["md", "json", "both", "wechat"],
        default="both",
        help="Output mode",
    )
    parser.add_argument("--style", type=str, default="", help="Style used")
    parser.add_argument("--article-type", type=str, default="", help="Article type")
    parser.add_argument("--originality", type=float, default=None, help="Originality score")
    parser.add_argument("--ai-tone", type=float, default=None, help="AI tone score")
    parser.add_argument("--humanity", type=float, default=None, help="Humanity score")
    args = parser.parse_args()

    content = read_text(args.input)
    lines = content.splitlines()
    title = detect_title(lines)
    summary = detect_summary(content)
    tags = detect_tags(content)
    sections = extract_sections(lines)

    base_name = args.input.stem
    args.output.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []

    if args.mode in ("md", "both"):
        md_path = args.output / f"{base_name}.md"
        md_path.write_text(content, encoding="utf-8")
        print(f"wrote: {md_path}")
        written_paths.append(md_path)

    if args.mode in ("json", "both"):
        payload = {
            "title": title,
            "summary": summary,
            "tags": tags,
            "article_type": args.article_type,
            "style_used": args.style,
            "quality_gate": {
                "originality_score": args.originality,
                "ai_tone_score": args.ai_tone,
                "humanity_score": args.humanity,
            },
            "sections": sections,
            "raw_markdown": content,
        }
        json_path = args.output / f"{base_name}.json"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote: {json_path}")
        written_paths.append(json_path)

    if args.mode == "wechat":
        txt_path = args.output / f"{base_name}.txt"
        txt_path.write_text(to_wechat_plain(content), encoding="utf-8")
        print(f"wrote: {txt_path}")
        written_paths.append(txt_path)

    print("=== receipt ===")
    print(f"mode: {args.mode}")
    print("saved_to:")
    for path in written_paths:
        print(f"- {path.resolve()}")
    print("copy_hint: 公众号编辑器直贴建议使用 --mode wechat")


if __name__ == "__main__":
    main()
