#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def load_records(paths: list[Path]) -> list[dict]:
    records: list[dict] = []
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(json.loads(line))
    return records


def rate(num: int, den: int) -> str:
    return "" if den == 0 else f"{num / den:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()

    records = load_records(args.files)
    groups: dict[tuple[str, str, str], dict[str, int]] = defaultdict(
        lambda: {
            "n": 0,
            "success": 0,
            "valid_success": 0,
            "activated": 0,
            "none": 0,
            "format_invalid": 0,
            "sensitivity_activated": 0,
        }
    )

    for record in records:
        key = (
            record.get("model_key", ""),
            record.get("domain_class", ""),
            record.get("gap_structure", ""),
        )
        g = groups[key]
        g["n"] += 1
        if record.get("status") == "success":
            g["success"] += 1
            if record.get("format_valid") is True:
                g["valid_success"] += 1
                if record.get("parsed_none") is True:
                    g["none"] += 1
                elif record.get("parsed_question"):
                    g["activated"] += 1
            else:
                g["format_invalid"] += 1
            if record.get("sensitivity_activation") is True:
                g["sensitivity_activated"] += 1

    rows = []
    for key in sorted(groups):
        model, domain_class, gap = key
        g = groups[key]
        rows.append({
            "model": model,
            "domain_class": domain_class,
            "gap_structure": gap,
            **g,
            "activation_rate_valid": rate(g["activated"], g["valid_success"]),
            "sensitivity_activation_rate_successes": rate(g["sensitivity_activated"], g["success"]),
        })

    headers = [
        "model", "domain_class", "gap_structure", "n", "success", "valid_success",
        "activated", "none", "format_invalid", "sensitivity_activated",
        "activation_rate_valid", "sensitivity_activation_rate_successes",
    ]

    writer = csv.DictWriter(__import__("sys").stdout, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as handle:
            out = csv.DictWriter(handle, fieldnames=headers)
            out.writeheader()
            out.writerows(rows)


if __name__ == "__main__":
    main()
