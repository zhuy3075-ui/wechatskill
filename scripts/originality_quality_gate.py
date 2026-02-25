#!/usr/bin/env python3
"""Originality + AI-tone + humanity quality gate for article output."""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path


SOURCE_TRACE_PATTERNS = [
    r"引用原文",
    r"原文如下",
    r"据原文",
    r"来源[:：]",
    r"摘录如下",
]

AI_FILLER_PATTERNS = [
    r"首先[，,]",
    r"其次[，,]",
    r"再次[，,]",
    r"最后[，,]",
    r"值得注意的是",
    r"需要指出的是",
    r"总的来说",
    r"综上所述",
    r"在当今社会",
    r"在这个时代",
    r"不可否认",
    r"毋庸置疑",
    r"由此可见",
    r"从某种意义上说",
    r"在一定程度上",
    r"赋能",
    r"助力",
    r"深耕",
]

SCENE_TOKENS = [
    "今天",
    "昨天",
    "凌晨",
    "早上",
    "中午",
    "晚上",
    "周一",
    "周末",
    "地铁",
    "办公室",
    "会议室",
    "出租屋",
    "厨房",
    "手机",
    "消息",
    "走进",
    "坐下",
    "抬头",
    "看见",
    "听到",
]

COLLOQUIAL_TOKENS = [
    "你可能",
    "你会发现",
    "说白了",
    "讲真",
    "先别急",
    "这事儿",
    "你想想",
    "换句话说",
    "我更倾向于",
    "我的判断是",
]

STANCE_TOKENS = [
    "我认为",
    "我更倾向于",
    "我的判断是",
    "我不认同",
    "我支持",
    "我反对",
    "在我看来",
]


@dataclass
class Metrics:
    originality_score: float
    ai_tone_score: float
    humanity_score: float
    ngram_overlap: float
    sentence_reuse_ratio: float
    structure_similarity: float
    novelty_ratio: float
    source_trace_hits: int
    ai_filler_hits: int
    scene_density: float
    colloquial_ratio: float
    sentence_variation: float
    stance_hits: int
    passed: bool


def read_text(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"Cannot decode file: {path}")


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text)


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"[。！？；\n]", text)
    return [p.strip() for p in parts if len(p.strip()) >= 10]


def split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text)
    return [p.strip() for p in parts if p.strip()]


def char_ngrams(text: str, n: int = 5) -> set[str]:
    text = normalize(text)
    if len(text) < n:
        return {text} if text else set()
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def sentence_reuse(article_sentences: list[str], source_sentences: list[str]) -> tuple[float, float]:
    if not article_sentences or not source_sentences:
        return 0.0, 1.0
    reused = 0
    novel = 0
    for s in article_sentences:
        best = 0.0
        for t in source_sentences:
            ratio = SequenceMatcher(None, s, t).ratio()
            if ratio > best:
                best = ratio
        if best >= 0.85:
            reused += 1
        if best < 0.60:
            novel += 1
    return reused / len(article_sentences), novel / len(article_sentences)


def heading_signature(text: str) -> str:
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            lines.append(re.sub(r"^#+\s*", "", s))
        elif re.match(r"^[一二三四五六七八九十0-9]+[、.．)]", s):
            lines.append(s)
    return " | ".join(lines)


def stddev(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var)


def count_matches(patterns: list[str], text: str) -> int:
    total = 0
    for p in patterns:
        total += len(re.findall(p, text))
    return total


def token_density(text: str, tokens: list[str]) -> float:
    norm = normalize(text)
    if not norm:
        return 0.0
    hits = sum(norm.count(token) for token in tokens)
    return hits / max(1, len(norm) / 100)


def sentence_token_ratio(sentences: list[str], tokens: list[str]) -> float:
    if not sentences:
        return 0.0
    hit = 0
    for s in sentences:
        if any(token in s for token in tokens):
            hit += 1
    return hit / len(sentences)


def evaluate(
    article: str,
    sources: list[str],
    min_originality: float,
    max_ai: float,
    min_humanity: float,
    strict_trace: bool,
) -> Metrics:
    article_ngrams = char_ngrams(article)
    source_text = "\n".join(sources)
    source_ngrams = char_ngrams(source_text)
    overlap = jaccard(article_ngrams, source_ngrams)

    article_sentences = split_sentences(article)
    source_sentences = split_sentences(source_text)
    reuse_ratio, novelty_ratio = sentence_reuse(article_sentences, source_sentences)

    structure_sim = 0.0
    if sources:
        sig = heading_signature(article)
        structure_sim = max(
            SequenceMatcher(None, sig, heading_signature(src)).ratio() for src in sources
        )

    trace_hits = count_matches(SOURCE_TRACE_PATTERNS, article)
    filler_hits = count_matches(AI_FILLER_PATTERNS, article)

    penalty_overlap = overlap * 40
    penalty_reuse = reuse_ratio * 25
    penalty_structure = structure_sim * 15
    penalty_trace = 10 if trace_hits > 0 else 0
    bonus_novel = novelty_ratio * 10

    originality = 100 - penalty_overlap - penalty_reuse - penalty_structure - penalty_trace + bonus_novel
    originality = max(0.0, min(100.0, originality))
    if strict_trace and trace_hits > 0:
        originality = 0.0

    para_lengths = [len(re.sub(r"\s+", "", p)) for p in split_paragraphs(article)]
    sent_lengths = [len(re.sub(r"\s+", "", s)) for s in article_sentences]
    sent_std = stddev(sent_lengths)
    para_std = stddev(para_lengths)

    ai_score = 0.0
    ai_score += min(35.0, filler_hits * 3.5)
    if sent_std < 6:
        ai_score += 20
    elif sent_std < 9:
        ai_score += 10
    if para_std < 25:
        ai_score += 15
    elif para_std < 40:
        ai_score += 8
    if re.search(r"首先[，,].*其次[，,].*最后[，,]", article, flags=re.S):
        ai_score += 20
    ai_score = max(0.0, min(100.0, ai_score))

    scene_density = token_density(article, SCENE_TOKENS)
    colloquial_ratio = sentence_token_ratio(article_sentences, COLLOQUIAL_TOKENS)
    stance_hits = count_matches(STANCE_TOKENS, article)
    sentence_variation = sent_std

    humanity = 50.0
    humanity += min(20.0, scene_density * 8.0)
    humanity += min(20.0, colloquial_ratio * 80.0)
    humanity += min(15.0, stance_hits * 4.0)
    if sentence_variation < 6:
        humanity -= 20
    elif sentence_variation < 9:
        humanity -= 10
    if ai_score > 40:
        humanity -= 10
    humanity = max(0.0, min(100.0, humanity))

    passed = originality >= min_originality and ai_score <= max_ai and humanity >= min_humanity
    return Metrics(
        originality_score=round(originality, 2),
        ai_tone_score=round(ai_score, 2),
        humanity_score=round(humanity, 2),
        ngram_overlap=round(overlap, 4),
        sentence_reuse_ratio=round(reuse_ratio, 4),
        structure_similarity=round(structure_sim, 4),
        novelty_ratio=round(novelty_ratio, 4),
        source_trace_hits=trace_hits,
        ai_filler_hits=filler_hits,
        scene_density=round(scene_density, 4),
        colloquial_ratio=round(colloquial_ratio, 4),
        sentence_variation=round(sentence_variation, 4),
        stance_hits=stance_hits,
        passed=passed,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Originality, AI-tone and humanity quality gate.")
    parser.add_argument("-a", "--article", type=Path, required=True, help="Article text file path")
    parser.add_argument("-s", "--sources", type=Path, nargs="*", default=[], help="Source file paths")
    parser.add_argument("--min-originality", type=float, default=70.0, help="Minimum originality score")
    parser.add_argument("--max-ai-tone", type=float, default=30.0, help="Maximum AI-tone score")
    parser.add_argument("--min-humanity", type=float, default=60.0, help="Minimum humanity score")
    parser.add_argument("--strict-source-trace", action="store_true", help="Set originality=0 if source-trace phrase appears")
    args = parser.parse_args()

    article = read_text(args.article)
    sources = [read_text(p) for p in args.sources if p.exists()]
    metrics = evaluate(
        article,
        sources,
        min_originality=args.min_originality,
        max_ai=args.max_ai_tone,
        min_humanity=args.min_humanity,
        strict_trace=args.strict_source_trace,
    )

    print("=== Originality Quality Gate ===")
    print(f"originality_score: {metrics.originality_score}")
    print(f"ai_tone_score: {metrics.ai_tone_score}")
    print(f"humanity_score: {metrics.humanity_score}")
    print(f"ngram_overlap: {metrics.ngram_overlap}")
    print(f"sentence_reuse_ratio: {metrics.sentence_reuse_ratio}")
    print(f"structure_similarity: {metrics.structure_similarity}")
    print(f"novelty_ratio: {metrics.novelty_ratio}")
    print(f"source_trace_hits: {metrics.source_trace_hits}")
    print(f"ai_filler_hits: {metrics.ai_filler_hits}")
    print(f"scene_density: {metrics.scene_density}")
    print(f"colloquial_ratio: {metrics.colloquial_ratio}")
    print(f"sentence_variation: {metrics.sentence_variation}")
    print(f"stance_hits: {metrics.stance_hits}")
    print(f"passed: {metrics.passed}")


if __name__ == "__main__":
    main()
