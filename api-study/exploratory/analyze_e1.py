#!/usr/bin/env python3
"""Generate the formal exploratory E1 / E1B descriptive outputs.

This script is intentionally standard-library only. It consumes the frozen J1
metadata join and finalized FA1 focal-alignment labels. It does not perform any
new semantic coding, consensus clustering, or inferential hypothesis testing.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[2]
E1_ROOT = ROOT / "api-study" / "exploratory" / "e1"
J1_DIR = E1_ROOT / "metadata_join" / "AU-E1-J1-v1"
FA1_DIR = (
    E1_ROOT
    / "focal_alignment"
    / "coding"
    / "AU-E1-FA1-8f2e24cb6f5baae6"
    / "final"
)
OUTPUT_DIR = E1_ROOT / "analysis" / "AU-E1-ANALYSIS-v1"
PROTOCOL_PATH = ROOT / "api-study" / "exploratory" / "E1_ANALYSIS_EXECUTION.md"
SCRIPT_PATH = ROOT / "api-study" / "exploratory" / "analyze_e1.py"

JOINED_OBSERVATIONS = J1_DIR / "JOINED_OBSERVATIONS.jsonl"
JOINED_CARDS = J1_DIR / "JOINED_CARDS.jsonl"
JOINED_CLUSTERS = J1_DIR / "JOINED_CLUSTERS.jsonl"
J1_RECORD = J1_DIR / "E1_METADATA_JOIN_RECORD.json"
FINAL_ALIGNMENT = FA1_DIR / "FINAL_ALIGNMENT.jsonl"
FA1_FINALIZATION = FA1_DIR / "FINALIZATION_RECORD.json"

REQUIRED_BASE_COMMIT = "9df9694bb9202f18f49fe453d84d3da9f9024756"
EXPECTED_INPUT_SHA256 = {
    JOINED_OBSERVATIONS: "b5bedb3799604bbacf8d966fc72e6cbc90b4af25df49a74790763fe54f257c10",
    JOINED_CARDS: "0391eae6abdbe636dabbcfb709e43e3989beebb275c13705580cf189c2a0e277",
    JOINED_CLUSTERS: "bcb82e3e7f78ed44651cb139a83ca8864a79c5da6d4ad62cc01b7b19b3b3f8ee",
    FINAL_ALIGNMENT: "cb4ef2f187c936fafd614c5b997a621ecaea286838812ffaea28a2963b0d12cc",
}
EXPECTED_COUNTS = {
    "joined_observations": 17514,
    "joined_cards": 11904,
    "joined_clusters": 2026,
    "final_alignment": 2026,
    "eligible_observations": 2919,
    "unique_cards": 1984,
    "representations": 2,
    "topics": 12,
    "partition_replicates": 3,
}
ALIGNMENTS = ("focal", "adjacent", "peripheral", "indeterminate")
GAP_ORDER = {"closed": 0, "seamed": 1, "explicit_gap": 2, "explicit-gap": 2}
RESIDUAL_MODES = {
    "all": frozenset(),
    "focal_excluded": frozenset({"focal"}),
    "focal_adjacent_excluded": frozenset({"focal", "adjacent"}),
}
CONCENTRATION_METRICS = (
    "top_target_share",
    "shannon_entropy_nats",
    "effective_target_count",
    "simpson_concentration",
    "observed_target_count",
    "singleton_unit_share",
    "rare_le2_unit_share",
)


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Non-object JSONL row at {path}:{line_number}")
            rows.append(row)
    return rows


def write_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(compact_json(row) + "\n")
            count += 1
    return count


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def verify_git_checkpoint() -> dict[str, Any]:
    if run_git("status", "--porcelain").stdout.strip():
        raise ValueError("Working tree is not clean. Commit the analysis implementation before running it.")
    head = run_git("rev-parse", "HEAD").stdout.strip()
    ancestor = run_git("merge-base", "--is-ancestor", REQUIRED_BASE_COMMIT, "HEAD", check=False)
    if ancestor.returncode != 0:
        raise ValueError(f"HEAD does not descend from required FA1 finalization commit {REQUIRED_BASE_COMMIT}")
    verification = run_git("verify-commit", "HEAD", check=False)
    if verification.returncode != 0:
        detail = (verification.stderr or verification.stdout).strip()
        raise ValueError(f"HEAD is not a locally verifiable signed commit: {detail}")
    return {
        "git_head": head,
        "required_base_commit": REQUIRED_BASE_COMMIT,
        "required_base_is_ancestor": True,
        "head_signature_verified": True,
    }


def require_fields(row: dict[str, Any], fields: Sequence[str], context: str) -> None:
    missing = [field for field in fields if field not in row]
    if missing:
        raise ValueError(f"Missing fields in {context}: {missing}")


def validate_inputs() -> dict[str, Any]:
    for path, expected in EXPECTED_INPUT_SHA256.items():
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"Frozen input hash mismatch for {path}: {actual} != {expected}")

    j1 = load_json(J1_RECORD)
    fa1 = load_json(FA1_FINALIZATION)
    if j1.get("status") != "complete" or j1.get("original_model_gap_metadata_joined") is not True:
        raise ValueError("J1 record is not complete")
    if j1.get("e1_descriptive_metrics_computed") is not False:
        raise ValueError("J1 record does not preserve the pre-analysis boundary")
    if fa1.get("final_alignment_rows") != EXPECTED_COUNTS["final_alignment"]:
        raise ValueError("FA1 finalization count mismatch")
    if fa1.get("final_alignment_sha256") != EXPECTED_INPUT_SHA256[FINAL_ALIGNMENT]:
        raise ValueError("FA1 finalization hash mismatch")

    observations = load_jsonl(JOINED_OBSERVATIONS)
    cards = load_jsonl(JOINED_CARDS)
    clusters = load_jsonl(JOINED_CLUSTERS)
    alignment_rows = load_jsonl(FINAL_ALIGNMENT)
    expected_lengths = {
        "joined_observations": observations,
        "joined_cards": cards,
        "joined_clusters": clusters,
        "final_alignment": alignment_rows,
    }
    for name, rows in expected_lengths.items():
        if len(rows) != EXPECTED_COUNTS[name]:
            raise ValueError(f"Unexpected {name} count: {len(rows)}")

    obs_fields = (
        "record_id", "card_id", "model_key", "gap_structure", "topic_id",
        "representation_set_id", "representation", "partition_replicate",
        "partitioner_model_key", "cluster_uid", "task_id",
    )
    card_fields = (
        "card_id", "topic_id", "representation_set_id", "representation",
        "partition_replicate", "partitioner_model_key", "cluster_uid", "task_id",
    )
    cluster_fields = (
        "cluster_uid", "topic_id", "representation_set_id", "representation",
        "partition_replicate", "partitioner_model_key", "task_id",
    )
    for idx, row in enumerate(observations, 1):
        require_fields(row, obs_fields, f"JOINED_OBSERVATIONS row {idx}")
    for idx, row in enumerate(cards, 1):
        require_fields(row, card_fields, f"JOINED_CARDS row {idx}")
    for idx, row in enumerate(clusters, 1):
        require_fields(row, cluster_fields, f"JOINED_CLUSTERS row {idx}")

    alignment_map: dict[str, str] = {}
    for idx, row in enumerate(alignment_rows, 1):
        require_fields(row, ("cluster_uid", "final_alignment"), f"FINAL_ALIGNMENT row {idx}")
        uid = row["cluster_uid"]
        label = row["final_alignment"]
        if label not in ALIGNMENTS:
            raise ValueError(f"Unknown alignment label {label!r} for {uid}")
        if uid in alignment_map:
            raise ValueError(f"Duplicate alignment cluster_uid: {uid}")
        alignment_map[uid] = label

    cluster_uids = {row["cluster_uid"] for row in clusters}
    if len(cluster_uids) != EXPECTED_COUNTS["joined_clusters"]:
        raise ValueError("JOINED_CLUSTERS cluster_uid is not unique")
    if cluster_uids != set(alignment_map):
        raise ValueError("FA1 alignment coverage does not exactly match J1 cluster coverage")

    record_assignments = Counter(row["record_id"] for row in observations)
    if len(record_assignments) != EXPECTED_COUNTS["eligible_observations"] or set(record_assignments.values()) != {6}:
        raise ValueError("Each eligible observation must have exactly six joined assignments")
    card_assignments = Counter(row["card_id"] for row in cards)
    if len(card_assignments) != EXPECTED_COUNTS["unique_cards"] or set(card_assignments.values()) != {6}:
        raise ValueError("Each unique card must have exactly six joined assignments")

    representations = sorted({row["representation"] for row in observations})
    topics = sorted({row["topic_id"] for row in observations})
    partitions = sorted({row["partition_replicate"] for row in observations})
    if len(representations) != EXPECTED_COUNTS["representations"]:
        raise ValueError("Unexpected representation count")
    if len(topics) != EXPECTED_COUNTS["topics"]:
        raise ValueError("Unexpected topic count")
    if len(partitions) != EXPECTED_COUNTS["partition_replicates"]:
        raise ValueError("Unexpected partition-replicate count")

    # A card is an exact passage + question pair, so its topic and gap structure
    # must be invariant across all observation instances represented by that card.
    card_meta: dict[str, tuple[str, str]] = {}
    for row in observations:
        meta = (row["topic_id"], row["gap_structure"])
        prior = card_meta.setdefault(row["card_id"], meta)
        if prior != meta:
            raise ValueError(f"Card crosses topic/gap cells: {row['card_id']}")

    card_rows_augmented: list[dict[str, Any]] = []
    for row in cards:
        topic_id, gap = card_meta[row["card_id"]]
        if topic_id != row["topic_id"]:
            raise ValueError(f"Joined card topic mismatch: {row['card_id']}")
        card_rows_augmented.append({**row, "gap_structure": gap})

    return {
        "observations": observations,
        "cards": card_rows_augmented,
        "clusters": clusters,
        "alignment_map": alignment_map,
        "representations": representations,
        "topics": topics,
        "partitions": partitions,
    }


def distribution_metrics(cluster_uids: Sequence[str]) -> dict[str, Any]:
    n = len(cluster_uids)
    if n == 0:
        return {
            "retained_unit_count": 0,
            "top_target_share": None,
            "shannon_entropy_nats": None,
            "effective_target_count": None,
            "simpson_concentration": None,
            "observed_target_count": 0,
            "singleton_unit_share": None,
            "rare_le2_unit_share": None,
        }
    counts = Counter(cluster_uids)
    probs = [count / n for count in counts.values()]
    entropy = -sum(p * math.log(p) for p in probs)
    singleton_units = sum(count for count in counts.values() if count == 1)
    rare_units = sum(count for count in counts.values() if count <= 2)
    return {
        "retained_unit_count": n,
        "top_target_share": max(counts.values()) / n,
        "shannon_entropy_nats": entropy,
        "effective_target_count": math.exp(entropy),
        "simpson_concentration": sum(p * p for p in probs),
        "observed_target_count": len(counts),
        "singleton_unit_share": singleton_units / n,
        "rare_le2_unit_share": rare_units / n,
    }


def gap_sort(value: str) -> tuple[int, str]:
    return (GAP_ORDER.get(value, 99), value)


def make_concentration_rows(
    rows: Sequence[dict[str, Any]],
    alignment_map: dict[str, str],
    sample_unit: str,
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["representation"], row["partition_replicate"], row["topic_id"], row["gap_structure"])].append(row)

    out: list[dict[str, Any]] = []
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2], gap_sort(k[3]))):
        representation, partition, topic, gap = key
        base = groups[key]
        for mode, excluded in RESIDUAL_MODES.items():
            retained = [row for row in base if alignment_map[row["cluster_uid"]] not in excluded]
            metrics = distribution_metrics([row["cluster_uid"] for row in retained])
            indeterminate_count = sum(alignment_map[row["cluster_uid"]] == "indeterminate" for row in retained)
            out.append({
                "schema_version": "au-e1-concentration-cell-v1",
                "sample_unit": sample_unit,
                "residual_mode": mode,
                "representation": representation,
                "partition_replicate": partition,
                "partitioner_model_key": base[0]["partitioner_model_key"],
                "topic_id": topic,
                "gap_structure": gap,
                "original_unit_count": len(base),
                "retained_proportion": (len(retained) / len(base)) if base else None,
                "retained_indeterminate_count": indeterminate_count,
                "retained_indeterminate_share": (indeterminate_count / len(retained)) if retained else None,
                **metrics,
            })
    return out


def make_model_concentration_rows(
    observations: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        groups[(row["representation"], row["partition_replicate"], row["topic_id"], row["model_key"], row["gap_structure"])].append(row)
    out: list[dict[str, Any]] = []
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2], k[3], gap_sort(k[4]))):
        representation, partition, topic, model, gap = key
        base = groups[key]
        out.append({
            "schema_version": "au-e1-model-concentration-cell-v1",
            "sample_unit": "observation",
            "residual_mode": "all",
            "representation": representation,
            "partition_replicate": partition,
            "partitioner_model_key": base[0]["partitioner_model_key"],
            "topic_id": topic,
            "model_key": model,
            "gap_structure": gap,
            "original_unit_count": len(base),
            **distribution_metrics([row["cluster_uid"] for row in base]),
        })
    return out


def make_alignment_rows(
    rows: Sequence[dict[str, Any]], alignment_map: dict[str, str], sample_unit: str
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["representation"], row["partition_replicate"], row["topic_id"], row["gap_structure"])].append(row)
    out: list[dict[str, Any]] = []
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2], gap_sort(k[3]))):
        representation, partition, topic, gap = key
        base = groups[key]
        counts = Counter(alignment_map[row["cluster_uid"]] for row in base)
        n = len(base)
        result = {
            "schema_version": "au-e1-alignment-cell-v1",
            "sample_unit": sample_unit,
            "representation": representation,
            "partition_replicate": partition,
            "partitioner_model_key": base[0]["partitioner_model_key"],
            "topic_id": topic,
            "gap_structure": gap,
            "unit_count": n,
        }
        for label in ALIGNMENTS:
            result[f"{label}_count"] = counts[label]
            result[f"{label}_share"] = counts[label] / n if n else None
        out.append(result)
    return out


def comb2(n: int) -> float:
    return n * (n - 1) / 2.0


def adjusted_rand_index(labels_a: Sequence[str], labels_b: Sequence[str]) -> float:
    if len(labels_a) != len(labels_b):
        raise ValueError("ARI label vectors differ in length")
    n = len(labels_a)
    if n < 2:
        return 1.0
    contingency = Counter(zip(labels_a, labels_b))
    rows = Counter(labels_a)
    cols = Counter(labels_b)
    index = sum(comb2(v) for v in contingency.values())
    row_sum = sum(comb2(v) for v in rows.values())
    col_sum = sum(comb2(v) for v in cols.values())
    total = comb2(n)
    expected = (row_sum * col_sum / total) if total else 0.0
    maximum = 0.5 * (row_sum + col_sum)
    denom = maximum - expected
    if abs(denom) < 1e-15:
        return 1.0 if labels_a == labels_b else 0.0
    return (index - expected) / denom


def entropy_from_counts(counts: Counter[str], n: int) -> float:
    return -sum((count / n) * math.log(count / n) for count in counts.values() if count)


def variation_of_information(labels_a: Sequence[str], labels_b: Sequence[str]) -> float:
    if len(labels_a) != len(labels_b):
        raise ValueError("VI label vectors differ in length")
    n = len(labels_a)
    if n == 0:
        return 0.0
    rows = Counter(labels_a)
    cols = Counter(labels_b)
    contingency = Counter(zip(labels_a, labels_b))
    h_a = entropy_from_counts(rows, n)
    h_b = entropy_from_counts(cols, n)
    mutual_information = 0.0
    for (a, b), count in contingency.items():
        p_ab = count / n
        mutual_information += p_ab * math.log((count * n) / (rows[a] * cols[b]))
    return h_a + h_b - 2.0 * mutual_information


def make_partition_stability_rows(cards: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, str]] = defaultdict(dict)
    partitioner: dict[tuple[str, str, str], str] = {}
    for row in cards:
        key = (row["representation"], row["topic_id"], row["partition_replicate"])
        if row["card_id"] in grouped[key]:
            raise ValueError(f"Duplicate card in partition stability group: {key} {row['card_id']}")
        grouped[key][row["card_id"]] = row["cluster_uid"]
        partitioner[key] = row["partitioner_model_key"]

    out: list[dict[str, Any]] = []
    rep_topics = sorted({(row["representation"], row["topic_id"]) for row in cards})
    for representation, topic in rep_topics:
        parts = sorted(part for rep, top, part in grouped if rep == representation and top == topic)
        if len(parts) != 3:
            raise ValueError(f"Expected three partitions for {representation}/{topic}, found {parts}")
        for part_a, part_b in itertools.combinations(parts, 2):
            map_a = grouped[(representation, topic, part_a)]
            map_b = grouped[(representation, topic, part_b)]
            if set(map_a) != set(map_b):
                raise ValueError(f"Partition card coverage differs for {representation}/{topic}")
            card_ids = sorted(map_a)
            labels_a = [map_a[c] for c in card_ids]
            labels_b = [map_b[c] for c in card_ids]
            out.append({
                "schema_version": "au-e1-partition-stability-v1",
                "representation": representation,
                "topic_id": topic,
                "partition_a": part_a,
                "partition_b": part_b,
                "partitioner_model_key_a": partitioner[(representation, topic, part_a)],
                "partitioner_model_key_b": partitioner[(representation, topic, part_b)],
                "unique_card_count": len(card_ids),
                "adjusted_rand_index": adjusted_rand_index(labels_a, labels_b),
                "variation_of_information_nats": variation_of_information(labels_a, labels_b),
            })
    return out


def js_divergence(counts_a: Counter[str], counts_b: Counter[str]) -> float:
    total_a = sum(counts_a.values())
    total_b = sum(counts_b.values())
    if total_a <= 0 or total_b <= 0:
        raise ValueError("JSD requires nonempty distributions")
    keys = set(counts_a) | set(counts_b)
    result = 0.0
    for key in keys:
        p = counts_a.get(key, 0) / total_a
        q = counts_b.get(key, 0) / total_b
        m = 0.5 * (p + q)
        if p > 0:
            result += 0.5 * p * math.log(p / m)
        if q > 0:
            result += 0.5 * q * math.log(q / m)
    return result


def make_jsd_rows(observations: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str, str], Counter[str]] = defaultdict(Counter)
    partitioner: dict[tuple[str, str, str], str] = {}
    for row in observations:
        key = (row["representation"], row["partition_replicate"], row["topic_id"], row["gap_structure"], row["model_key"])
        groups[key][row["cluster_uid"]] += 1
        partitioner[(row["representation"], row["partition_replicate"], row["topic_id"])] = row["partitioner_model_key"]

    out: list[dict[str, Any]] = []
    cells = sorted({key[:4] for key in groups}, key=lambda k: (k[0], k[1], k[2], gap_sort(k[3])))
    for representation, partition, topic, gap in cells:
        models = sorted(key[4] for key in groups if key[:4] == (representation, partition, topic, gap))
        for model_a, model_b in itertools.combinations(models, 2):
            counts_a = groups[(representation, partition, topic, gap, model_a)]
            counts_b = groups[(representation, partition, topic, gap, model_b)]
            out.append({
                "schema_version": "au-e1-model-jsd-v1",
                "representation": representation,
                "partition_replicate": partition,
                "partitioner_model_key": partitioner[(representation, partition, topic)],
                "topic_id": topic,
                "gap_structure": gap,
                "model_a": model_a,
                "model_b": model_b,
                "model_a_observation_count": sum(counts_a.values()),
                "model_b_observation_count": sum(counts_b.values()),
                "jensen_shannon_divergence_nats": js_divergence(counts_a, counts_b),
            })
    return out


def median_or_none(values: Sequence[float | int | None]) -> float | None:
    clean = [float(v) for v in values if v is not None]
    return statistics.median(clean) if clean else None


def min_or_none(values: Sequence[float | int | None]) -> float | None:
    clean = [float(v) for v in values if v is not None]
    return min(clean) if clean else None


def max_or_none(values: Sequence[float | int | None]) -> float | None:
    clean = [float(v) for v in values if v is not None]
    return max(clean) if clean else None


def make_topic_partition_summary(concentration_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in concentration_rows:
        key = (row["sample_unit"], row["residual_mode"], row["representation"], row["topic_id"], row["gap_structure"])
        groups[key].append(row)
    out: list[dict[str, Any]] = []
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2], k[3], gap_sort(k[4]))):
        sample_unit, residual_mode, representation, topic, gap = key
        rows = groups[key]
        if len(rows) != 3:
            raise ValueError(f"Expected three partition rows for topic summary: {key}")
        result: dict[str, Any] = {
            "schema_version": "au-e1-topic-partition-summary-v1",
            "sample_unit": sample_unit,
            "residual_mode": residual_mode,
            "representation": representation,
            "topic_id": topic,
            "gap_structure": gap,
            "partition_count": 3,
            "original_unit_count": rows[0]["original_unit_count"],
            "retained_unit_count_median": median_or_none([r["retained_unit_count"] for r in rows]),
            "retained_unit_count_min": min_or_none([r["retained_unit_count"] for r in rows]),
            "retained_unit_count_max": max_or_none([r["retained_unit_count"] for r in rows]),
            "retained_proportion_median": median_or_none([r["retained_proportion"] for r in rows]),
            "retained_proportion_min": min_or_none([r["retained_proportion"] for r in rows]),
            "retained_proportion_max": max_or_none([r["retained_proportion"] for r in rows]),
        }
        for metric in CONCENTRATION_METRICS:
            values = [r[metric] for r in rows]
            result[f"{metric}_median"] = median_or_none(values)
            result[f"{metric}_min"] = min_or_none(values)
            result[f"{metric}_max"] = max_or_none(values)
        out.append(result)
    return out


def make_alignment_topic_summary(alignment_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in alignment_rows:
        groups[(row["sample_unit"], row["representation"], row["topic_id"], row["gap_structure"])].append(row)
    out: list[dict[str, Any]] = []
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2], gap_sort(k[3]))):
        sample_unit, representation, topic, gap = key
        rows = groups[key]
        if len(rows) != 3:
            raise ValueError(f"Expected three partition rows for alignment summary: {key}")
        result: dict[str, Any] = {
            "schema_version": "au-e1-alignment-topic-summary-v1",
            "sample_unit": sample_unit,
            "representation": representation,
            "topic_id": topic,
            "gap_structure": gap,
            "partition_count": 3,
            "unit_count": rows[0]["unit_count"],
        }
        for label in ALIGNMENTS:
            values = [r[f"{label}_share"] for r in rows]
            result[f"{label}_share_median"] = median_or_none(values)
            result[f"{label}_share_min"] = min_or_none(values)
            result[f"{label}_share_max"] = max_or_none(values)
        out.append(result)
    return out


def weighted_mean(pairs: Sequence[tuple[float, float]]) -> float | None:
    total_weight = sum(weight for _, weight in pairs if weight > 0)
    if total_weight <= 0:
        return None
    return sum(value * weight for value, weight in pairs if weight > 0) / total_weight


def make_cross_topic_summary(topic_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in topic_rows:
        groups[(row["sample_unit"], row["residual_mode"], row["representation"], row["gap_structure"])].append(row)
    out: list[dict[str, Any]] = []
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2], gap_sort(k[3]))):
        sample_unit, residual_mode, representation, gap = key
        rows = groups[key]
        if len(rows) != EXPECTED_COUNTS["topics"]:
            raise ValueError(f"Cross-topic summary does not contain 12 topics: {key}")
        for metric in CONCENTRATION_METRICS:
            metric_key = f"{metric}_median"
            available = [r for r in rows if r[metric_key] is not None]
            equal_topic = statistics.mean(float(r[metric_key]) for r in available) if available else None
            if residual_mode == "all":
                weight_key = "original_unit_count"
                weight_basis = "original_unit_count"
            else:
                weight_key = "retained_unit_count_median"
                weight_basis = "retained_unit_count_median"
            weighted_pairs = [
                (float(r[metric_key]), float(r[weight_key]))
                for r in available
                if r[weight_key] is not None and float(r[weight_key]) > 0
            ]
            out.append({
                "schema_version": "au-e1-cross-topic-summary-v1",
                "sample_unit": sample_unit,
                "residual_mode": residual_mode,
                "representation": representation,
                "gap_structure": gap,
                "metric": metric,
                "topic_count_total": len(rows),
                "topic_count_nonempty": len(available),
                "equal_topic_mean_of_partition_medians": equal_topic,
                "weighted_mean_of_partition_medians": weighted_mean(weighted_pairs),
                "weight_basis": weight_basis,
            })
    return out


def analysis_outputs(state: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    obs = state["observations"]
    cards = state["cards"]
    alignment_map = state["alignment_map"]

    concentration = make_concentration_rows(obs, alignment_map, "observation")
    concentration += make_concentration_rows(cards, alignment_map, "unique_card")
    concentration.sort(key=lambda r: (
        r["sample_unit"], r["residual_mode"], r["representation"],
        r["partition_replicate"], r["topic_id"], gap_sort(r["gap_structure"]),
    ))

    alignment = make_alignment_rows(obs, alignment_map, "observation")
    alignment += make_alignment_rows(cards, alignment_map, "unique_card")
    alignment.sort(key=lambda r: (
        r["sample_unit"], r["representation"], r["partition_replicate"],
        r["topic_id"], gap_sort(r["gap_structure"]),
    ))

    topic_summary = make_topic_partition_summary(concentration)
    alignment_summary = make_alignment_topic_summary(alignment)

    return {
        "PARTITION_STABILITY.jsonl": make_partition_stability_rows(cards),
        "CONCENTRATION_CELLS.jsonl": concentration,
        "CONCENTRATION_MODEL_CELLS.jsonl": make_model_concentration_rows(obs),
        "ALIGNMENT_CELLS.jsonl": alignment,
        "MODEL_JSD.jsonl": make_jsd_rows(obs),
        "TOPIC_PARTITION_SUMMARY.jsonl": topic_summary,
        "ALIGNMENT_TOPIC_SUMMARY.jsonl": alignment_summary,
        "CROSS_TOPIC_SUMMARY.jsonl": make_cross_topic_summary(topic_summary),
    }


def write_outputs(outputs: dict[str, list[dict[str, Any]]], git_info: dict[str, Any]) -> Path:
    if OUTPUT_DIR.exists():
        raise ValueError(f"Output directory already exists; refusing to overwrite: {OUTPUT_DIR}")
    OUTPUT_DIR.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=".AU-E1-ANALYSIS-v1-", dir=OUTPUT_DIR.parent))
    try:
        file_records: dict[str, dict[str, Any]] = {}
        for filename, rows in outputs.items():
            path = temp_dir / filename
            count = write_jsonl(path, rows)
            file_records[filename] = {"rows": count, "sha256": sha256_file(path)}

        record = {
            "schema_version": "au-e1-analysis-record-v1",
            "analysis_id": "AU-E1-ANALYSIS-v1",
            "study": "Attainable Unknowns API Pilot 0.1",
            "status": "complete",
            "evidentiary_status": "post_hoc_exploratory",
            "protocol_id": "E1_with_E1B",
            "git": git_info,
            "implementation": {
                "path": str(SCRIPT_PATH.relative_to(ROOT)).replace(os.sep, "/"),
                "sha256": sha256_file(SCRIPT_PATH),
                "protocol_path": str(PROTOCOL_PATH.relative_to(ROOT)).replace(os.sep, "/"),
                "protocol_sha256": sha256_file(PROTOCOL_PATH),
            },
            "inputs": {
                str(path.relative_to(ROOT)).replace(os.sep, "/"): {
                    "sha256": sha256_file(path),
                    "expected_sha256": expected,
                }
                for path, expected in EXPECTED_INPUT_SHA256.items()
            },
            "analysis_rules": {
                "entropy_log_base": "natural",
                "jsd_log_base": "natural",
                "variation_of_information_log_base": "natural",
                "rare_target_definition": "within-cell cluster count <= 2",
                "partition_summary": "median and full observed range across P1/P2/P3",
                "cross_topic_equal_topic": "mean of per-topic partition medians",
                "cross_topic_weighted_all": "original unit count",
                "cross_topic_weighted_residual": "median retained unit count across partitions",
                "e1b_focal_excluded": ["focal"],
                "e1b_focal_adjacent_excluded": ["focal", "adjacent"],
                "indeterminate_retained_in_e1b": True,
                "consensus_partition_created": False,
                "inferential_tests_run": False,
            },
            "fixed_counts": EXPECTED_COUNTS,
            "output_files": file_records,
        }
        record_path = temp_dir / "E1_ANALYSIS_RECORD.json"
        write_json(record_path, record)
        os.replace(temp_dir, OUTPUT_DIR)
        return OUTPUT_DIR
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Verify frozen inputs and structural coverage, but do not compute or write E1 results.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    git_info = verify_git_checkpoint()
    state = validate_inputs()
    if args.validate_only:
        print(compact_json({
            "status": "validated",
            "git_head": git_info["git_head"],
            "joined_observations": len(state["observations"]),
            "joined_cards": len(state["cards"]),
            "joined_clusters": len(state["clusters"]),
            "alignment_rows": len(state["alignment_map"]),
        }))
        return 0
    outputs = analysis_outputs(state)
    out_dir = write_outputs(outputs, git_info)
    print(f"E1 analysis complete: {out_dir}")
    for filename in sorted(outputs):
        print(f"  {filename}: {len(outputs[filename])} rows")
    print("  E1_ANALYSIS_RECORD.json: 1 record")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
