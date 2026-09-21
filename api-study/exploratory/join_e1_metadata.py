#!/usr/bin/env python3
"""Mechanically join frozen E1 semantics to original model/gap metadata.

This implementation performs no semantic coding or cluster modification. It
validates the complete frozen chain and writes normalized cluster-, card-, and
observation-level joined datasets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
E1 = ROOT / "api-study" / "exploratory"

STAGE1_ID = "AU-E1-S1-cad71b8ce8fe0866"
STAGE2_ID = "AU-E1-S2-b021f4b9caf73dad"
BLIND_ID = "AU-E1-BLIND-v1"
JOIN_ID = "AU-E1-J1-v1"

S1_DIR = E1 / "e1" / "generated" / STAGE1_ID
S1_PACKET = S1_DIR / "blinded" / "STAGE1_MASTER_PACKET.json"
S1_KEY = S1_DIR / "private" / "E1_STAGE1_PRIVATE_KEY.json"
S1_RECORD = S1_DIR / "E1_STAGE1_GENERATION_RECORD.json"

S2_DIR = E1 / "e1" / "stage2" / "generated" / STAGE2_ID
S2_INDEX = S2_DIR / "blinded" / "STAGE2_PACKET_INDEX.json"
S2_KEY = S2_DIR / "private" / "E1_STAGE2_PRIVATE_KEY.json"
S2_RECORD = S2_DIR / "STAGE2_GENERATION_RECORD.json"

P1D3_DIR = E1 / "e1" / "stage2" / "partitions" / STAGE2_ID / "P1D3"
PARTITIONS = P1D3_DIR / "PARTITIONS.jsonl"
PARTITION_MANIFEST = P1D3_DIR / "RUN_MANIFEST.json"

BLIND_DIR = E1 / "e1" / "blind_bundle" / BLIND_ID
LABELS = BLIND_DIR / "CLUSTER_LABELS.jsonl"
ANCHORS = BLIND_DIR / "FOCAL_ANCHORS.json"
BLIND_RECORD = BLIND_DIR / "BLIND_SEMANTIC_BUNDLE_RECORD.json"

PASSAGES = ROOT / "api-study" / "passages.json"
JOIN_PROTOCOL = E1 / "E1_METADATA_JOIN_J1.md"
OUT = E1 / "e1" / "metadata_join" / JOIN_ID

EXPECTED = {
    "accepted_records": 3600,
    "eligible_observations": 2919,
    "unique_cards": 1984,
    "representations": 2,
    "topics": 12,
    "partitions": 72,
    "clusters": 2026,
    "card_assignments": 11904,
    "observation_assignments": 17514,
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compact_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {rel(path)}:{line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Non-object JSONL row at {rel(path)}:{line_number}")
            rows.append(row)
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(compact_json(row) + "\n")
            count += 1
        handle.flush()
        os.fsync(handle.fileno())
    return count


def normalized_newlines(raw: bytes, newline: bytes) -> bytes:
    text = raw.decode("utf-8-sig")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.replace("\n", newline.decode("ascii")).encode("utf-8")


def verify_hash(path: Path, expected: str) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    raw = path.read_bytes()
    actual = sha256_bytes(raw)
    if actual == expected:
        mode = "exact_bytes"
    else:
        alternatives: dict[str, str] = {}
        try:
            alternatives = {
                "newline_equivalent_lf": sha256_bytes(normalized_newlines(raw, b"\n")),
                "newline_equivalent_crlf": sha256_bytes(
                    normalized_newlines(raw, b"\r\n")
                ),
            }
        except UnicodeDecodeError:
            alternatives = {}
        matching = [name for name, digest in alternatives.items() if digest == expected]
        if len(matching) != 1:
            raise ValueError(
                f"SHA-256 mismatch for {rel(path)}: expected {expected}, observed {actual}"
            )
        mode = matching[0]
    return {
        "path": rel(path),
        "expected_sha256": expected,
        "actual_sha256": actual,
        "verification": mode,
    }


def add_hash_check(
    checks: dict[str, dict[str, str]], path: Path, expected: str
) -> None:
    result = verify_hash(path, expected)
    prior = checks.get(result["path"])
    if prior and prior["expected_sha256"] != expected:
        raise ValueError(f"Conflicting recorded hashes for {result['path']}")
    checks[result["path"]] = result


def final_sentence(value: str) -> str:
    import re

    parts = [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+", value.strip())
        if part.strip()
    ]
    if not parts:
        raise ValueError("Cannot extract final sentence from empty passage")
    return parts[-1]


def eligible(row: dict[str, Any]) -> bool:
    return (
        row.get("status") == "success"
        and row.get("format_valid") is True
        and row.get("parsed_none") is not True
        and isinstance(row.get("parsed_question"), str)
        and bool(row["parsed_question"].strip())
    )


def verify_recorded_inputs() -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    checks: dict[str, dict[str, str]] = {}
    s1_record = load_json(S1_RECORD)
    s2_record = load_json(S2_RECORD)
    blind_record = load_json(BLIND_RECORD)
    partition_manifest = load_json(PARTITION_MANIFEST)

    if blind_record.get("status") != "complete_pre_metadata_join":
        raise ValueError("Blind semantic bundle is not complete_pre_metadata_join")
    if blind_record.get("original_model_gap_metadata_joined") is not False:
        raise ValueError("Blind bundle already claims joined model/gap metadata")
    if blind_record.get("private_e1_keys_read_by_f1") is not False:
        raise ValueError("F1 record does not preserve the private-key boundary")

    blind_paths = {
        "p1d3_partitions_sha256": PARTITIONS,
        "stage2_packet_index_sha256": S2_INDEX,
        "passages_sha256": PASSAGES,
        "cluster_label_attempts_sha256": BLIND_DIR / "CLUSTER_LABEL_ATTEMPTS.jsonl",
        "cluster_labels_sha256": LABELS,
        "focal_anchors_sha256": ANCHORS,
        "protocol_sha256": E1 / "E1_BLIND_BUNDLE_FINALIZATION_F1.md",
        "runner_sha256": E1 / "finalize_e1_blind_bundle.py",
    }
    for key, path in blind_paths.items():
        add_hash_check(checks, path, blind_record["hashes"][key])

    if partition_manifest.get("partitions_sha256") != blind_record["hashes"].get(
        "p1d3_partitions_sha256"
    ):
        raise ValueError("Partition manifest and blind record disagree")

    for accepted in s1_record["accepted_runs"]:
        add_hash_check(checks, ROOT / accepted["records_path"], accepted["records_sha256"])
        add_hash_check(checks, ROOT / accepted["manifest_path"], accepted["manifest_sha256"])
    for path_text, digest in s1_record["files_sha256"].items():
        add_hash_check(checks, ROOT / path_text, digest)
    add_hash_check(checks, ROOT / s1_record["e1_protocol_path"], s1_record["e1_protocol_sha256"])
    add_hash_check(checks, ROOT / s1_record["stage1_generator_path"], s1_record["stage1_generator_sha256"])

    for path_text, digest in s2_record["source_files_sha256"].items():
        add_hash_check(checks, ROOT / path_text, digest)
    add_hash_check(checks, ROOT / s2_record["packet_index_path"], s2_record["packet_index_sha256"])
    add_hash_check(checks, ROOT / s2_record["private_key_path"], s2_record["private_key_sha256"])
    add_hash_check(checks, ROOT / s2_record["generator_path"], s2_record["generator_sha256"])
    add_hash_check(
        checks,
        ROOT / s2_record["instructions_source_path"],
        s2_record["instructions_source_sha256"],
    )

    index = load_json(S2_INDEX)
    for packet in index["packets"]:
        add_hash_check(checks, ROOT / packet["path"], packet["sha256"])

    return {
        "s1_record": s1_record,
        "s2_record": s2_record,
        "blind_record": blind_record,
        "partition_manifest": partition_manifest,
        "stage2_index": index,
    }, checks


def load_raw_records(s1_record: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for accepted in s1_record["accepted_runs"]:
        path = ROOT / accepted["records_path"]
        rows = load_jsonl(path)
        if len(rows) != 900:
            raise ValueError(f"Expected 900 rows in {rel(path)}, found {len(rows)}")
        for line_number, row in enumerate(rows, start=1):
            record_id = row.get("record_id")
            if not isinstance(record_id, str) or not record_id:
                raise ValueError(f"Missing record_id in {rel(path)}:{line_number}")
            if record_id in seen:
                raise ValueError(f"Duplicate raw record_id: {record_id}")
            seen.add(record_id)
            if row.get("run_id") != accepted["run_id"]:
                raise ValueError(f"Raw run_id mismatch at {rel(path)}:{line_number}")
            if row.get("model_key") != accepted["model_key"]:
                raise ValueError(f"Raw model_key mismatch at {rel(path)}:{line_number}")
            copied = dict(row)
            copied["_line_number"] = line_number
            all_rows.append(copied)
    eligible_rows = [row for row in all_rows if eligible(row)]
    if len(all_rows) != EXPECTED["accepted_records"]:
        raise ValueError("Unexpected accepted-record count")
    if len(eligible_rows) != EXPECTED["eligible_observations"]:
        raise ValueError("Unexpected eligible-observation count")
    return all_rows, eligible_rows


def validate_stage1(
    s1_record: dict[str, Any], eligible_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    key = load_json(S1_KEY)
    packet = load_json(S1_PACKET)
    cards = key.get("cards")
    observations = key.get("observations")
    visible_cards = packet.get("cards")
    if not isinstance(cards, list) or len(cards) != EXPECTED["unique_cards"]:
        raise ValueError("Stage 1 private card count mismatch")
    if not isinstance(visible_cards, list) or len(visible_cards) != EXPECTED["unique_cards"]:
        raise ValueError("Stage 1 visible card count mismatch")
    if not isinstance(observations, list) or len(observations) != EXPECTED["eligible_observations"]:
        raise ValueError("Stage 1 observation count mismatch")

    card_map = {row["card_id"]: row for row in cards}
    visible_map = {row["card_id"]: row for row in visible_cards}
    if len(card_map) != len(cards) or len(visible_map) != len(visible_cards):
        raise ValueError("Duplicate Stage 1 card ID")
    if set(card_map) != set(visible_map):
        raise ValueError("Visible/private Stage 1 card coverage mismatch")

    raw_by_id = {row["record_id"]: row for row in eligible_rows}
    key_by_id = {row["record_id"]: row for row in observations}
    if len(raw_by_id) != len(eligible_rows) or len(key_by_id) != len(observations):
        raise ValueError("Duplicate eligible observation record ID")
    if set(raw_by_id) != set(key_by_id):
        raise ValueError("Raw/private-key eligible observation coverage mismatch")

    comparison_fields = (
        "model_key",
        "provider",
        "model_requested",
        "run_id",
        "gap_structure",
        "condition_id",
        "domain_class",
        "topic_id",
        "topic_label",
        "replicate",
        "sequence",
    )
    observations_by_card: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        raw = raw_by_id[row["record_id"]]
        for field in comparison_fields:
            if row.get(field) != raw.get(field):
                raise ValueError(f"Stage 1 metadata mismatch for {row['record_id']}: {field}")
        if row.get("source_line_number") != raw.get("_line_number"):
            raise ValueError(f"Source line mismatch for {row['record_id']}")
        if row["card_id"] not in card_map:
            raise ValueError(f"Unknown card ID for {row['record_id']}")
        observations_by_card[row["card_id"]].append(row)

    for card_id, private in card_map.items():
        visible = visible_map[card_id]
        members = observations_by_card.get(card_id, [])
        if len(members) != private["multiplicity"]:
            raise ValueError(f"Multiplicity mismatch for {card_id}")
        if sorted(row["record_id"] for row in members) != private["record_ids"]:
            raise ValueError(f"Record membership mismatch for {card_id}")
        material = compact_json(
            {"passage": visible["passage"], "question": visible["question"]}
        )
        if sha256_bytes(material.encode("utf-8")) != private["visible_sha256"]:
            raise ValueError(f"Visible card hash mismatch for {card_id}")
        for member in members:
            raw = raw_by_id[member["record_id"]]
            if raw.get("passage") != visible["passage"]:
                raise ValueError(f"Passage mismatch for {member['record_id']}")
            if raw.get("parsed_question") != visible["question"]:
                raise ValueError(f"Question mismatch for {member['record_id']}")
            if raw.get("topic_id") != private["topic_id"]:
                raise ValueError(f"Card topic mismatch for {member['record_id']}")

    topic_map = {row["topic_packet_id"]: row["topic_id"] for row in key["topic_packet_mapping"]}
    if len(topic_map) != EXPECTED["topics"]:
        raise ValueError("Stage 1 topic mapping mismatch")
    return {
        "key": key,
        "packet": packet,
        "card_map": card_map,
        "visible_map": visible_map,
        "observations": observations,
        "observations_by_card": observations_by_card,
        "topic_map": topic_map,
    }


def validate_anchors(topic_map: dict[str, str]) -> dict[str, dict[str, Any]]:
    anchor_obj = load_json(ANCHORS)
    anchors = anchor_obj.get("anchors")
    if not isinstance(anchors, list) or len(anchors) != EXPECTED["topics"]:
        raise ValueError("Focal-anchor count mismatch")
    anchor_map = {row["topic_id"]: row for row in anchors}
    if len(anchor_map) != len(anchors) or set(anchor_map) != set(topic_map.values()):
        raise ValueError("Focal-anchor topic coverage mismatch")

    passages = load_json(PASSAGES)
    passage_map = {row["topic_id"]: row for row in passages["topics"]}
    if set(passage_map) != set(anchor_map):
        raise ValueError("Passage/anchor topic coverage mismatch")
    for topic_id, anchor in anchor_map.items():
        source = passage_map[topic_id]["variants"]["explicit_gap"]
        if anchor.get("source_variant") != "explicit_gap":
            raise ValueError(f"Anchor source variant mismatch for {topic_id}")
        if anchor.get("source_passage") != source:
            raise ValueError(f"Anchor source passage mismatch for {topic_id}")
        if anchor.get("focal_unknown_anchor") != final_sentence(source):
            raise ValueError(f"Focal anchor mismatch for {topic_id}")
    return anchor_map


def validate_stage2(
    index: dict[str, Any], s1: dict[str, Any]
) -> dict[str, Any]:
    key = load_json(S2_KEY)
    topic_map = {row["topic_packet_id"]: row["topic_id"] for row in key["topic_packet_mapping"]}
    if topic_map != s1["topic_map"]:
        raise ValueError("Stage 1 and Stage 2 topic mappings differ")
    representation_map = {
        row["representation_set_id"]: row["representation"]
        for row in key["representation_mapping"]
    }
    if len(representation_map) != EXPECTED["representations"]:
        raise ValueError("Stage 2 representation mapping mismatch")

    packets: dict[str, dict[str, Any]] = {}
    packet_target_text: dict[tuple[str, str], str] = {}
    for item in index["packets"]:
        packet = load_json(ROOT / item["path"])
        packet_id = packet["packet_id"]
        if packet_id in packets:
            raise ValueError(f"Duplicate Stage 2 packet ID: {packet_id}")
        if packet["representation_set_id"] not in representation_map:
            raise ValueError(f"Unknown representation set in {packet_id}")
        if packet["topic_packet_id"] not in topic_map:
            raise ValueError(f"Unknown topic packet in {packet_id}")
        targets = packet.get("targets")
        if not isinstance(targets, list) or packet.get("target_count") != len(targets):
            raise ValueError(f"Target count mismatch in {packet_id}")
        seen_ids: set[str] = set()
        for target in targets:
            target_id = target["target_id"]
            if target_id in seen_ids:
                raise ValueError(f"Duplicate target ID in {packet_id}: {target_id}")
            seen_ids.add(target_id)
            packet_target_text[(packet_id, target_id)] = target["canonical_target"]
        packets[packet_id] = packet
    if len(packets) != EXPECTED["representations"] * EXPECTED["topics"]:
        raise ValueError("Unexpected Stage 2 packet count")

    target_map: dict[tuple[str, str], dict[str, Any]] = {}
    rep_card_seen: set[tuple[str, str]] = set()
    for target in key["targets"]:
        identity = (target["packet_id"], target["target_id"])
        if identity in target_map:
            raise ValueError(f"Duplicate Stage 2 target mapping: {identity}")
        packet = packets.get(target["packet_id"])
        if packet is None or identity not in packet_target_text:
            raise ValueError(f"Unknown Stage 2 target mapping: {identity}")
        if target["representation_set_id"] != packet["representation_set_id"]:
            raise ValueError(f"Representation mismatch for {identity}")
        if target["topic_packet_id"] != packet["topic_packet_id"]:
            raise ValueError(f"Topic packet mismatch for {identity}")
        if target["representation"] != representation_map[target["representation_set_id"]]:
            raise ValueError(f"Representation label mismatch for {identity}")
        card = s1["card_map"].get(target["card_id"])
        if card is None:
            raise ValueError(f"Unknown Stage 1 card for {identity}")
        if card["topic_packet_id"] != target["topic_packet_id"]:
            raise ValueError(f"Card topic packet mismatch for {identity}")
        if card["multiplicity"] != target["multiplicity"]:
            raise ValueError(f"Card multiplicity mismatch for {identity}")
        rep_card = (target["representation_set_id"], target["card_id"])
        if rep_card in rep_card_seen:
            raise ValueError(f"Duplicate representation/card mapping: {rep_card}")
        rep_card_seen.add(rep_card)
        enriched = dict(target)
        enriched["canonical_target"] = packet_target_text[identity]
        target_map[identity] = enriched

    expected_targets = EXPECTED["representations"] * EXPECTED["unique_cards"]
    if len(target_map) != expected_targets or len(rep_card_seen) != expected_targets:
        raise ValueError("Stage 2 target/card coverage mismatch")
    if set(target_map) != set(packet_target_text):
        raise ValueError("Stage 2 visible/private target coverage mismatch")
    return {
        "key": key,
        "topic_map": topic_map,
        "representation_map": representation_map,
        "packets": packets,
        "target_map": target_map,
    }


def validate_partitions_and_labels(s2: dict[str, Any]) -> list[dict[str, Any]]:
    partitions = load_jsonl(PARTITIONS)
    labels = load_jsonl(LABELS)
    if len(partitions) != EXPECTED["partitions"] or len(labels) != EXPECTED["partitions"]:
        raise ValueError("Partition/label row count mismatch")
    label_map = {row["task_id"]: row for row in labels}
    if len(label_map) != len(labels):
        raise ValueError("Duplicate cluster-label task ID")

    validated: list[dict[str, Any]] = []
    tasks: set[str] = set()
    packet_replicates: Counter[tuple[str, str]] = Counter()
    cluster_count = 0
    for row in partitions:
        task_id = row["task_id"]
        packet_id = row["packet_id"]
        replicate = row["partition_replicate"]
        if task_id in tasks:
            raise ValueError(f"Duplicate partition task ID: {task_id}")
        tasks.add(task_id)
        if replicate not in {"P1", "P2", "P3"}:
            raise ValueError(f"Unexpected partition replicate: {replicate}")
        packet = s2["packets"].get(packet_id)
        if packet is None:
            raise ValueError(f"Unknown partition packet: {packet_id}")
        if row["partition"].get("packet_id") != packet_id:
            raise ValueError(f"Nested packet identity mismatch for {task_id}")
        packet_replicates[(packet_id, replicate)] += 1

        visible_targets = {target["target_id"] for target in packet["targets"]}
        assigned: list[str] = []
        cluster_ids: set[str] = set()
        for cluster in row["partition"]["clusters"]:
            cluster_id = cluster["cluster_id"]
            if cluster_id in cluster_ids:
                raise ValueError(f"Duplicate cluster ID in {task_id}: {cluster_id}")
            cluster_ids.add(cluster_id)
            assigned.extend(cluster["target_ids"])
        if len(assigned) != len(set(assigned)) or set(assigned) != visible_targets:
            raise ValueError(f"Partition target coverage mismatch for {task_id}")

        label = label_map.get(task_id)
        if label is None:
            raise ValueError(f"Missing cluster labels for {task_id}")
        if label["packet_id"] != packet_id or label["partition_replicate"] != replicate:
            raise ValueError(f"Cluster-label identity mismatch for {task_id}")
        label_clusters = label.get("clusters")
        partition_clusters = row["partition"]["clusters"]
        if len(label_clusters) != len(partition_clusters):
            raise ValueError(f"Cluster-label coverage mismatch for {task_id}")
        for partition_cluster, label_cluster in zip(partition_clusters, label_clusters):
            if partition_cluster["cluster_id"] != label_cluster["cluster_id"]:
                raise ValueError(f"Cluster-label order mismatch for {task_id}")
            if len(partition_cluster["target_ids"]) != label_cluster["member_count"]:
                raise ValueError(f"Cluster-label member count mismatch for {task_id}")
            if not isinstance(label_cluster.get("descriptive_name"), str) or not label_cluster[
                "descriptive_name"
            ].strip():
                raise ValueError(f"Empty cluster name for {task_id}")
        cluster_count += len(partition_clusters)
        validated.append({**row, "label_record": label})

    if set(label_map) != tasks:
        raise ValueError("Partition/label task coverage mismatch")
    expected_packet_replicates = {
        (packet_id, replicate)
        for packet_id in s2["packets"]
        for replicate in ("P1", "P2", "P3")
    }
    if set(packet_replicates) != expected_packet_replicates or any(
        count != 1 for count in packet_replicates.values()
    ):
        raise ValueError("Packet/partition replicate coverage mismatch")
    if cluster_count != EXPECTED["clusters"]:
        raise ValueError(f"Expected {EXPECTED['clusters']} clusters, found {cluster_count}")
    return sorted(validated, key=lambda row: row["task_id"])


def build_state() -> dict[str, Any]:
    records, input_checks = verify_recorded_inputs()
    all_raw, eligible_raw = load_raw_records(records["s1_record"])
    s1 = validate_stage1(records["s1_record"], eligible_raw)
    s2 = validate_stage2(records["stage2_index"], s1)
    anchor_map = validate_anchors(s2["topic_map"])
    partitions = validate_partitions_and_labels(s2)
    return {
        "records": records,
        "input_checks": input_checks,
        "all_raw": all_raw,
        "eligible_raw": eligible_raw,
        "s1": s1,
        "s2": s2,
        "anchor_map": anchor_map,
        "partitions": partitions,
    }


def build_joined_rows(state: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    s1 = state["s1"]
    s2 = state["s2"]
    clusters_out: list[dict[str, Any]] = []
    cards_out: list[dict[str, Any]] = []
    assignment_by_card: dict[tuple[str, str, str], dict[str, Any]] = {}

    for row in state["partitions"]:
        task_id = row["task_id"]
        packet_id = row["packet_id"]
        replicate = row["partition_replicate"]
        packet = s2["packets"][packet_id]
        representation_set_id = packet["representation_set_id"]
        representation = s2["representation_map"][representation_set_id]
        topic_packet_id = packet["topic_packet_id"]
        topic_id = s2["topic_map"][topic_packet_id]
        anchor = state["anchor_map"][topic_id]["focal_unknown_anchor"]
        labels = {
            cluster["cluster_id"]: cluster
            for cluster in row["label_record"]["clusters"]
        }

        for cluster in row["partition"]["clusters"]:
            cluster_id = cluster["cluster_id"]
            cluster_uid = f"{task_id}:{cluster_id}"
            label = labels[cluster_id]["descriptive_name"].strip()
            members: list[dict[str, Any]] = []
            for target_id in cluster["target_ids"]:
                target = s2["target_map"][(packet_id, target_id)]
                card = s1["card_map"][target["card_id"]]
                member = {
                    "target_id": target_id,
                    "card_id": target["card_id"],
                    "canonical_target": target["canonical_target"],
                    "stage1_uncertain": target["stage1_uncertain"],
                    "multiplicity": target["multiplicity"],
                }
                members.append(member)
                card_row = {
                    "schema_version": "au-e1-joined-card-v1",
                    "task_id": task_id,
                    "packet_id": packet_id,
                    "representation_set_id": representation_set_id,
                    "representation": representation,
                    "topic_packet_id": topic_packet_id,
                    "topic_id": topic_id,
                    "partition_replicate": replicate,
                    "partitioner_model_key": row.get("model_key"),
                    "target_id": target_id,
                    "card_id": target["card_id"],
                    "canonical_target": target["canonical_target"],
                    "stage1_uncertain": target["stage1_uncertain"],
                    "card_multiplicity": target["multiplicity"],
                    "visible_sha256": card["visible_sha256"],
                    "cluster_id": cluster_id,
                    "cluster_uid": cluster_uid,
                    "cluster_name": label,
                    "focal_unknown_anchor": anchor,
                }
                cards_out.append(card_row)
                assignment_key = (target["card_id"], representation_set_id, replicate)
                if assignment_key in assignment_by_card:
                    raise ValueError(f"Duplicate joined card assignment: {assignment_key}")
                assignment_by_card[assignment_key] = card_row

            clusters_out.append(
                {
                    "schema_version": "au-e1-joined-cluster-v1",
                    "task_id": task_id,
                    "packet_id": packet_id,
                    "representation_set_id": representation_set_id,
                    "representation": representation,
                    "topic_packet_id": topic_packet_id,
                    "topic_id": topic_id,
                    "partition_replicate": replicate,
                    "partitioner_model_key": row.get("model_key"),
                    "cluster_id": cluster_id,
                    "cluster_uid": cluster_uid,
                    "cluster_name": label,
                    "focal_unknown_anchor": anchor,
                    "unique_card_count": len(members),
                    "observation_count": sum(member["multiplicity"] for member in members),
                    "members": members,
                }
            )

    expected_assignment_keys = {
        (card_id, representation_set_id, replicate)
        for card_id in s1["card_map"]
        for representation_set_id in s2["representation_map"]
        for replicate in ("P1", "P2", "P3")
    }
    if set(assignment_by_card) != expected_assignment_keys:
        raise ValueError("Joined card assignment key coverage mismatch")

    cards_out.sort(
        key=lambda row: (
            row["representation_set_id"],
            row["topic_packet_id"],
            row["partition_replicate"],
            row["target_id"],
        )
    )
    clusters_out.sort(key=lambda row: (row["task_id"], row["cluster_id"]))

    observations_out: list[dict[str, Any]] = []
    for observation_order, observation in enumerate(s1["observations"], start=1):
        card = s1["card_map"][observation["card_id"]]
        for representation_set_id in sorted(s2["representation_map"]):
            for replicate in ("P1", "P2", "P3"):
                assignment = assignment_by_card[
                    (observation["card_id"], representation_set_id, replicate)
                ]
                observations_out.append(
                    {
                        "schema_version": "au-e1-joined-observation-v1",
                        "observation_order": observation_order,
                        **observation,
                        "topic_packet_id": card["topic_packet_id"],
                        "card_multiplicity": card["multiplicity"],
                        "representation_set_id": representation_set_id,
                        "representation": assignment["representation"],
                        "partition_replicate": replicate,
                        "partitioner_model_key": assignment["partitioner_model_key"],
                        "packet_id": assignment["packet_id"],
                        "task_id": assignment["task_id"],
                        "target_id": assignment["target_id"],
                        "canonical_target": assignment["canonical_target"],
                        "stage1_uncertain": assignment["stage1_uncertain"],
                        "cluster_id": assignment["cluster_id"],
                        "cluster_uid": assignment["cluster_uid"],
                        "cluster_name": assignment["cluster_name"],
                        "focal_unknown_anchor": assignment["focal_unknown_anchor"],
                    }
                )

    if len(clusters_out) != EXPECTED["clusters"]:
        raise ValueError("Joined cluster count mismatch")
    if len(cards_out) != EXPECTED["card_assignments"]:
        raise ValueError("Joined card assignment count mismatch")
    if len(observations_out) != EXPECTED["observation_assignments"]:
        raise ValueError("Joined observation assignment count mismatch")
    if len({row["cluster_uid"] for row in clusters_out}) != len(clusters_out):
        raise ValueError("Joined cluster UID is not globally unique")
    if Counter(row["record_id"] for row in observations_out) != Counter(
        {row["record_id"]: 6 for row in s1["observations"]}
    ):
        raise ValueError("Each eligible observation must have exactly six joined assignments")

    return {
        "clusters": clusters_out,
        "cards": cards_out,
        "observations": observations_out,
    }


def preflight() -> dict[str, Any]:
    state = build_state()
    joined = build_joined_rows(state)
    passage_check = state["input_checks"][rel(PASSAGES)]
    return {
        "status": "e1_metadata_join_preflight_complete_no_files_written",
        "join_id": JOIN_ID,
        "private_e1_keys_read": True,
        "semantic_changes_performed": False,
        "input_files_verified": len(state["input_checks"]),
        "passages_hash_verification": passage_check["verification"],
        "accepted_records": len(state["all_raw"]),
        "eligible_observations": len(state["eligible_raw"]),
        "unique_cards": len(state["s1"]["card_map"]),
        "representations": len(state["s2"]["representation_map"]),
        "topics": len(state["s2"]["topic_map"]),
        "partitions": len(state["partitions"]),
        "clusters": len(joined["clusters"]),
        "joined_card_assignments": len(joined["cards"]),
        "joined_observation_assignments": len(joined["observations"]),
    }


def join(source_checkpoint: str, source_archive_sha256: str | None) -> dict[str, Any]:
    if OUT.exists():
        raise FileExistsError(f"Refusing to overwrite existing join output: {rel(OUT)}")
    state = build_state()
    joined = build_joined_rows(state)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f".{JOIN_ID}-", dir=OUT.parent) as temp_name:
        temp = Path(temp_name)
        paths = {
            "clusters": temp / "JOINED_CLUSTERS.jsonl",
            "cards": temp / "JOINED_CARDS.jsonl",
            "observations": temp / "JOINED_OBSERVATIONS.jsonl",
        }
        counts = {
            name: write_jsonl(paths[name], joined[name])
            for name in ("clusters", "cards", "observations")
        }
        output_files = {
            f"api-study/exploratory/e1/metadata_join/{JOIN_ID}/{path.name}": {
                "rows": counts[name],
                "sha256": sha256_file(path),
            }
            for name, path in paths.items()
        }
        record = {
            "schema_version": "au-e1-metadata-join-record-v1",
            "study": "Attainable Unknowns API Pilot 0.1",
            "protocol_id": "E1",
            "amendment_id": "E1A",
            "join_id": JOIN_ID,
            "status": "complete",
            "generated_at_utc": now(),
            "source_checkpoint_commit": source_checkpoint,
            "source_archive_sha256": source_archive_sha256,
            "blind_bundle_id": BLIND_ID,
            "blind_bundle_partition_freeze_commit": state["records"]["blind_record"][
                "partition_freeze_commit"
            ],
            "join_protocol_path": rel(JOIN_PROTOCOL),
            "join_protocol_sha256": sha256_file(JOIN_PROTOCOL),
            "implementation_path": rel(Path(__file__).resolve()),
            "implementation_sha256": sha256_file(Path(__file__).resolve()),
            "original_model_gap_metadata_joined": True,
            "private_e1_keys_read_by_j1": True,
            "semantic_changes_performed": False,
            "focal_alignment_coded": False,
            "e1_descriptive_metrics_computed": False,
            "counts": {
                "accepted_records": len(state["all_raw"]),
                "eligible_observations": len(state["eligible_raw"]),
                "unique_visible_cards": len(state["s1"]["card_map"]),
                "representations": len(state["s2"]["representation_map"]),
                "topics": len(state["s2"]["topic_map"]),
                "partitions": len(state["partitions"]),
                "cluster_instances": len(joined["clusters"]),
                "joined_card_assignments": len(joined["cards"]),
                "joined_observation_assignments": len(joined["observations"]),
                "assignments_per_eligible_observation": 6,
            },
            "input_files": [
                state["input_checks"][path]
                for path in sorted(state["input_checks"])
            ],
            "output_files": output_files,
            "validation": {
                "all_recorded_input_hashes_verified": True,
                "newline_only_hash_equivalence_explicitly_recorded": True,
                "raw_to_stage1_observation_metadata_exact": True,
                "raw_to_visible_card_text_exact": True,
                "stage1_card_multiplicities_exact": True,
                "stage1_to_stage2_target_mapping_complete": True,
                "partition_target_coverage_complete": True,
                "cluster_label_identity_and_member_counts_exact": True,
                "focal_anchors_exact_against_explicit_gap_passages": True,
                "two_representations_preserved_separately": True,
                "three_partition_replicates_preserved_separately": True,
                "no_semantic_fields_modified": True,
            },
            "scope_boundary": (
                "J1 joins fixed semantic assignments to original metadata. It does not "
                "compute E1 descriptive metrics or focal-gap alignment codes."
            ),
        }
        write_json(temp / "E1_METADATA_JOIN_RECORD.json", record)
        os.replace(temp, OUT)
    return record


def verify_existing() -> dict[str, Any]:
    if not OUT.is_dir():
        raise FileNotFoundError(OUT)
    record_path = OUT / "E1_METADATA_JOIN_RECORD.json"
    record = load_json(record_path)
    if record.get("status") != "complete" or record.get("join_id") != JOIN_ID:
        raise ValueError("Existing metadata join record is not complete")
    verified: list[dict[str, Any]] = []
    for path_text, expected in sorted(record["output_files"].items()):
        path = ROOT / path_text
        actual_rows = len(load_jsonl(path))
        actual_sha = sha256_file(path)
        if actual_rows != expected["rows"] or actual_sha != expected["sha256"]:
            raise ValueError(f"Existing joined output mismatch: {path_text}")
        verified.append({"path": path_text, "rows": actual_rows, "sha256": actual_sha})
    state = build_state()
    joined = build_joined_rows(state)
    rebuilt_counts = {name: len(rows) for name, rows in joined.items()}
    return {
        "status": "e1_metadata_join_verified",
        "join_id": JOIN_ID,
        "record_path": rel(record_path),
        "record_sha256": sha256_file(record_path),
        "outputs": verified,
        "rebuilt_counts": rebuilt_counts,
        "all_source_invariants_rechecked": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight", help="Validate and construct the join in memory; write nothing")
    join_parser = sub.add_parser("join", help="Write the complete metadata join atomically")
    join_parser.add_argument("--source-checkpoint", required=True)
    join_parser.add_argument("--source-archive-sha256")
    sub.add_parser("verify", help="Recheck sources and verify an existing join")
    args = parser.parse_args()

    if args.command == "preflight":
        result = preflight()
    elif args.command == "join":
        result = join(args.source_checkpoint, args.source_archive_sha256)
    elif args.command == "verify":
        result = verify_existing()
    else:
        raise AssertionError(args.command)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
