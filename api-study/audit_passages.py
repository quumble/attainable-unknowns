#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--passages",
        type=Path,
        default=Path(__file__).resolve().parent / "passages.json",
    )
    parser.add_argument(
        "--max-within-topic-word-spread",
        type=int,
        default=5,
    )
    args = parser.parse_args()

    bank = json.loads(args.passages.read_text(encoding="utf-8"))
    print("topic_id,closed_words,seamed_words,explicit_gap_words,spread")
    failures = []
    for topic in bank["topics"]:
        counts = {
            key: len(text.split())
            for key, text in topic["variants"].items()
        }
        spread = max(counts.values()) - min(counts.values())
        print(
            f"{topic['topic_id']},{counts['closed']},{counts['seamed']},"
            f"{counts['explicit_gap']},{spread}"
        )
        if spread > args.max_within_topic_word_spread:
            failures.append((topic["topic_id"], spread))

    if failures:
        raise SystemExit(
            "Within-topic word-count spread exceeded threshold: "
            + ", ".join(f"{topic}={spread}" for topic, spread in failures)
        )


if __name__ == "__main__":
    main()
