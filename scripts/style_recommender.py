#!/usr/bin/env python3
"""List available styles and recommend styles by content and article type."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

from utils import read_text

TOKEN_SPLIT_RE = re.compile(r"[，。！？、；：,\s\-\|/]+")
CHINESE_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}")

TYPE_KEYWORDS = {
    "干货": {"方法", "步骤", "教程", "实操", "框架"},
    "观点": {"判断", "立场", "分析", "反驳", "论证"},
    "故事": {"人物", "冲突", "情节", "反转", "结局"},
    "清单": {"盘点", "推荐", "合集", "清单", "工具"},
    "热点": {"事件", "时事", "新闻", "舆论", "热搜"},
}


@dataclass
class StyleProfile:
    name: str
    path: Path
    summary: str = ""
    tone: str = ""
    structure: str = ""
    suitable_types: set[str] = field(default_factory=set)
    keywords: set[str] = field(default_factory=set)
def normalize_tokens(text: str) -> set[str]:
    tokens = set()
    for token in TOKEN_SPLIT_RE.split(text):
        t = token.strip().lower()
        if len(t) >= 2:
            tokens.add(t)
    for token in CHINESE_TOKEN_RE.findall(text):
        if len(token) >= 2:
            tokens.add(token)
    return tokens


def parse_style(path: Path) -> StyleProfile:
    content = read_text(path)
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    name = path.stem
    summary = ""
    tone = ""
    structure = ""
    suitable_types: set[str] = set()
    keywords: set[str] = set()

    if lines and lines[0].startswith("#"):
        name = re.sub(r"^#+\s*", "", lines[0]).strip() or name

    for line in lines:
        if line.startswith("语气") or line.startswith("文风"):
            tone = line.split("：", 1)[-1].strip() if "：" in line else line
        if line.startswith("结构"):
            structure = line.split("：", 1)[-1].strip() if "：" in line else line
        if line.startswith("适用") and "：" in line:
            raw = line.split("：", 1)[1]
            for t in re.split(r"[、,/，\s]+", raw):
                t = t.strip()
                if t:
                    suitable_types.add(t)
        if line.startswith("关键词") and "：" in line:
            raw = line.split("：", 1)[1]
            for k in re.split(r"[#、,/，\s]+", raw):
                k = k.strip()
                if len(k) >= 2:
                    keywords.add(k)

    if not summary:
        for line in lines[1:6]:
            if not line.startswith("#"):
                summary = line[:70]
                break

    if not keywords:
        keywords = normalize_tokens(" ".join(lines[:30]))

    return StyleProfile(
        name=name,
        path=path,
        summary=summary,
        tone=tone,
        structure=structure,
        suitable_types=suitable_types,
        keywords=keywords,
    )


def list_profiles(styles_dir: Path) -> list[StyleProfile]:
    if not styles_dir.exists():
        return []
    profiles = []
    for path in sorted(styles_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        profiles.append(parse_style(path))
    return profiles


def score_profile(profile: StyleProfile, content_tokens: set[str], article_type: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    overlap = profile.keywords & content_tokens
    if overlap:
        overlap_score = min(45, len(overlap) * 8)
        score += overlap_score
        reasons.append(f"关键词匹配: {', '.join(sorted(list(overlap))[:4])}")

    if article_type:
        if article_type in profile.suitable_types:
            score += 35
            reasons.append(f"适配类型: {article_type}")
        elif article_type in TYPE_KEYWORDS:
            hint_overlap = TYPE_KEYWORDS[article_type] & profile.keywords
            if hint_overlap:
                score += min(20, len(hint_overlap) * 6)
                reasons.append("风格特征与类型相近")

    has_match = bool(overlap) or (article_type and article_type in profile.suitable_types)
    if has_match:
        if profile.tone:
            score += 3
            reasons.append("语气定义完整")
        if profile.structure:
            score += 2
            reasons.append("结构定义完整")

    return score, reasons


def main() -> None:
    parser = argparse.ArgumentParser(description="List and recommend styles.")
    parser.add_argument("--styles-dir", type=Path, default=Path("styles"), help="Styles directory")
    parser.add_argument("--content", type=str, default="", help="User content for recommendation")
    parser.add_argument("--content-file", type=Path, help="Content file path")
    parser.add_argument("--article-type", type=str, default="", help="Article type: 干货/观点/故事/清单/热点")
    parser.add_argument("--top-k", type=int, default=3, help="Top K recommendations")
    parser.add_argument("--list-only", action="store_true", help="Only list available styles")
    args = parser.parse_args()

    content = args.content
    if args.content_file and args.content_file.exists():
        content = read_text(args.content_file)

    profiles = list_profiles(args.styles_dir)
    if not profiles:
        print("未发现可用风格文件（styles/*.md）。")
        return

    print("=== 可用风格 ===")
    for p in profiles:
        summary = p.summary or "（无摘要）"
        print(f"- {p.name}: {summary}")

    if args.list_only:
        return

    tokens = normalize_tokens(content)
    scored = []
    for p in profiles:
        s, reasons = score_profile(p, tokens, args.article_type.strip())
        scored.append((s, p, reasons))
    scored.sort(key=lambda x: x[0], reverse=True)

    print("\n=== 风格推荐 ===")
    for idx, (score, profile, reasons) in enumerate(scored[: max(1, args.top_k)], start=1):
        reason_text = "；".join(reasons) if reasons else "基础匹配"
        print(f"{idx}. {profile.name} (score={score})")
        print(f"   理由: {reason_text}")
        if profile.tone:
            print(f"   语气: {profile.tone}")
        if profile.structure:
            print(f"   结构: {profile.structure}")


if __name__ == "__main__":
    main()
