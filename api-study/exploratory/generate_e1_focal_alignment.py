#!/usr/bin/env python3
"""Generate blinded E1/FA1 focal-alignment packets from frozen semantic inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
E1_DIR = ROOT / "api-study" / "exploratory"

PROTOCOL = E1_DIR / "E1_FOCAL_ALIGNMENT_EXECUTION_FA1.md"
INSTRUCTIONS = E1_DIR / "E1_FOCAL_ALIGNMENT_INSTRUCTIONS.md"
RUNNER = E1_DIR / "run_e1_focal_alignment.py"
GENERATOR = Path(__file__).resolve()

E1B_COMMIT = "8e8911f0a10a29908b46b9486fb5cbd3d6860164"
BLIND_BUNDLE_COMMIT = "bdc20e6926d029a59c58b2e9189bb6ff581c88a8"
PARTITION_FREEZE_COMMIT = "fb54cd0c37841e880372694e056d985ac3272b40"

BLIND_BUNDLE_ID = "AU-E1-BLIND-v1"
BLIND_BUNDLE_DIR = E1_DIR / "e1" / "blind_bundle" / BLIND_BUNDLE_ID
BLIND_BUNDLE_RECORD = BLIND_BUNDLE_DIR / "BLIND_SEMANTIC_BUNDLE_RECORD.json"
FOCAL_ANCHORS = BLIND_BUNDLE_DIR / "FOCAL_ANCHORS.json"

STAGE2_BUNDLE_ID = "AU-E1-S2-b021f4b9caf73dad"
STAGE2_DIR = E1_DIR / "e1" / "stage2" / "generated" / STAGE2_BUNDLE_ID
STAGE2_INDEX = STAGE2_DIR / "blinded" / "STAGE2_PACKET_INDEX.json"
STAGE2_PRIVATE_KEY = STAGE2_DIR / "private" / "E1_STAGE2_PRIVATE_KEY.json"
STAGE2_GENERATION_RECORD = STAGE2_DIR / "STAGE2_GENERATION_RECORD.json"
P1D3_PARTITIONS = (
    E1_DIR
    / "e1"
    / "stage2"
    / "partitions"
    / STAGE2_BUNDLE_ID
    / "P1D3"
    / "PARTITIONS.jsonl"
)

GENERATED_ROOT = E1_DIR / "e1" / "focal_alignment" / "generated"

EXPECTED_ANCHORS = 12
EXPECTED_STAGE2_PACKETS = 24
EXPECTED_PARTITIONS = 72
EXPECTED_CLUSTERS = 2026

PACKET_ORDER_SALT = "AU-E1-FA1-packet-order-v1|"
CLUSTER_ORDER_SALT = "AU-E1-FA1-cluster-order-v1|"
MEMBER_ORDER_SALT = "AU-E1-FA1-member-order-v1|"
BUNDLE_SALT = "AU-E1-FA1-bundle-v1|"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def resolve_commit(ref: str) -> str:
    proc = git("rev-parse", "--verify", f"{ref}^{{commit}}")
    if proc.returncode != 0:
        raise ValueError(f"Cannot resolve commit {ref}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def verify_signed_commit(ref: str, label: str) -> str:
    commit = resolve_commit(ref)
    proc = git("verify-commit", commit)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise ValueError(f"{label} signature verification failed for {commit}: {detail}")
    if git("merge-base", "--is-ancestor", commit, "HEAD").returncode != 0:
        raise ValueError(f"{label} {commit} is not an ancestor of HEAD")
    return commit


def committed_blob_matches_worktree(commit: str, path: Path) -> bool:
    p = rel(path)
    committed = git("rev-parse", f"{commit}:{p}")
    current = git("hash-object", f"--path={p}", p)
    return (
        committed.returncode == 0
        and current.returncode == 0
        and committed.stdout.strip() == current.stdout.strip()
    )


def verify_implementation(ref: str) -> str:
    commit = verify_signed_commit(ref, "FA1 implementation")
    for ancestor, label in (
        (E1B_COMMIT, "E1B adoption"),
        (BLIND_BUNDLE_COMMIT, "E1 blind semantic bundle"),
        (PARTITION_FREEZE_COMMIT, "P1D3 partition freeze"),
    ):
        resolved = verify_signed_commit(ancestor, label)
        if resolved != ancestor:
            raise ValueError(f"Resolved {label} commit differs from frozen SHA")
        if git("merge-base", "--is-ancestor", ancestor, commit).returncode != 0:
            raise ValueError(f"{label} is not an ancestor of FA1 implementation")

    for path in (PROTOCOL, INSTRUCTIONS, GENERATOR, RUNNER):
        if not path.is_file():
            raise FileNotFoundError(path)
        if not committed_blob_matches_worktree(commit, path):
            raise ValueError(
                f"Working FA1 implementation file differs from signed commit: {rel(path)}"
            )
    return commit


def verify_frozen_sources() -> dict[str, Any]:
    blind_commit = verify_signed_commit(BLIND_BUNDLE_COMMIT, "E1 blind semantic bundle")
    if blind_commit != BLIND_BUNDLE_COMMIT:
        raise ValueError("Resolved blind-bundle commit differs from frozen SHA")

    source_paths = [
        BLIND_BUNDLE_RECORD,
        FOCAL_ANCHORS,
        STAGE2_INDEX,
        STAGE2_PRIVATE_KEY,
        STAGE2_GENERATION_RECORD,
        P1D3_PARTITIONS,
    ]
    for path in source_paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        if not committed_blob_matches_worktree(blind_commit, path):
            raise ValueError(f"Frozen source differs from blind-bundle commit: {rel(path)}")

    record = load_json(BLIND_BUNDLE_RECORD)
    hashes = record.get("hashes") or {}
    expected_hashes = {
        FOCAL_ANCHORS: hashes.get("focal_anchors_sha256"),
        STAGE2_INDEX: hashes.get("stage2_packet_index_sha256"),
        P1D3_PARTITIONS: hashes.get("p1d3_partitions_sha256"),
    }
    for path, expected in expected_hashes.items():
        if not isinstance(expected, str) or sha256_file(path) != expected:
            raise ValueError(f"Blind-bundle recorded hash mismatch: {rel(path)}")

    generation = load_json(STAGE2_GENERATION_RECORD)
    private_hash = generation.get("private_key_sha256")
    if isinstance(private_hash, str) and sha256_file(STAGE2_PRIVATE_KEY) != private_hash:
        raise ValueError("Stage 2 private-key SHA-256 mismatch")

    return record


def load_stage2_packets() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    index = load_json(STAGE2_INDEX)
    rows = index.get("packets")
    if not isinstance(rows, list) or len(rows) != EXPECTED_STAGE2_PACKETS:
        raise ValueError("Unexpected Stage 2 packet-index coverage")

    packets: dict[str, dict[str, Any]] = {}
    for row in rows:
        packet_id = row.get("packet_id")
        path_text = row.get("path")
        expected_hash = row.get("sha256")
        if not isinstance(packet_id, str) or not isinstance(path_text, str):
            raise ValueError("Invalid Stage 2 packet-index row")
        path = ROOT / path_text
        if not path.is_file():
            raise FileNotFoundError(path)
        if sha256_file(path) != expected_hash:
            raise ValueError(f"Stage 2 packet hash mismatch: {packet_id}")
        packet = load_json(path)
        if packet.get("packet_id") != packet_id:
            raise ValueError(f"Stage 2 packet identity mismatch: {packet_id}")
        targets = packet.get("targets")
        if not isinstance(targets, list) or len(targets) != int(row.get("target_count", -1)):
            raise ValueError(f"Stage 2 target count mismatch: {packet_id}")
        target_ids: set[str] = set()
        for target in targets:
            if set(target) != {"target_id", "canonical_target"}:
                raise ValueError(f"Unexpected target fields in {packet_id}")
            tid = target["target_id"]
            text = target["canonical_target"]
            if not isinstance(tid, str) or not isinstance(text, str) or not text.strip():
                raise ValueError(f"Invalid target in {packet_id}")
            if tid in target_ids:
                raise ValueError(f"Duplicate target ID {tid} in {packet_id}")
            target_ids.add(tid)
        packets[packet_id] = packet
    return packets, index


def load_topic_mapping() -> dict[str, str]:
    key = load_json(STAGE2_PRIVATE_KEY)
    rows = key.get("topic_packet_mapping")
    if not isinstance(rows, list) or len(rows) != EXPECTED_ANCHORS:
        raise ValueError("Stage 2 private topic mapping is missing or incomplete")
    mapping: dict[str, str] = {}
    for row in rows:
        opaque = row.get("topic_packet_id")
        topic_id = row.get("topic_id")
        if not isinstance(opaque, str) or not isinstance(topic_id, str):
            raise ValueError("Invalid topic mapping row")
        if opaque in mapping:
            raise ValueError(f"Duplicate topic packet mapping: {opaque}")
        mapping[opaque] = topic_id
    return mapping


def load_anchors() -> dict[str, str]:
    value = load_json(FOCAL_ANCHORS)
    rows = value.get("anchors")
    if not isinstance(rows, list) or len(rows) != EXPECTED_ANCHORS:
        raise ValueError("Unexpected focal-anchor count")
    anchors: dict[str, str] = {}
    for row in rows:
        topic_id = row.get("topic_id")
        anchor = row.get("focal_unknown_anchor")
        if not isinstance(topic_id, str) or not isinstance(anchor, str) or not anchor.strip():
            raise ValueError("Invalid focal-anchor row")
        if topic_id in anchors:
            raise ValueError(f"Duplicate focal anchor for {topic_id}")
        anchors[topic_id] = anchor.strip()
    return anchors


def load_partitions(packets: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = read_jsonl(P1D3_PARTITIONS)
    if len(rows) != EXPECTED_PARTITIONS:
        raise ValueError(f"Expected {EXPECTED_PARTITIONS} partitions, found {len(rows)}")

    seen_tasks: set[str] = set()
    total_clusters = 0
    per_packet: dict[str, int] = {}
    for row in rows:
        task_id = row.get("task_id")
        packet_id = row.get("packet_id")
        partition = row.get("partition")
        if not isinstance(task_id, str) or not isinstance(packet_id, str) or not isinstance(partition, dict):
            raise ValueError("Invalid P1D3 partition row")
        if task_id in seen_tasks:
            raise ValueError(f"Duplicate partition task: {task_id}")
        seen_tasks.add(task_id)
        if packet_id not in packets or partition.get("packet_id") != packet_id:
            raise ValueError(f"Partition packet mismatch: {task_id}")

        input_ids = {t["target_id"] for t in packets[packet_id]["targets"]}
        assigned: list[str] = []
        cluster_ids: set[str] = set()
        clusters = partition.get("clusters")
        if not isinstance(clusters, list) or not clusters:
            raise ValueError(f"Missing clusters: {task_id}")
        for cluster in clusters:
            cid = cluster.get("cluster_id")
            tids = cluster.get("target_ids")
            if not isinstance(cid, str) or cid in cluster_ids:
                raise ValueError(f"Invalid/duplicate cluster ID: {task_id}")
            if not isinstance(tids, list) or not tids or not all(isinstance(x, str) for x in tids):
                raise ValueError(f"Invalid cluster membership: {task_id}:{cid}")
            cluster_ids.add(cid)
            assigned.extend(tids)
        if len(assigned) != len(set(assigned)) or set(assigned) != input_ids:
            raise ValueError(f"Partition target coverage mismatch: {task_id}")
        total_clusters += len(clusters)
        per_packet[packet_id] = per_packet.get(packet_id, 0) + 1

    if total_clusters != EXPECTED_CLUSTERS:
        raise ValueError(f"Expected {EXPECTED_CLUSTERS} cluster instances, found {total_clusters}")
    if set(per_packet) != set(packets) or any(count != 3 for count in per_packet.values()):
        raise ValueError("Each Stage 2 packet must have exactly three frozen partitions")
    return rows


def build_state(implementation_commit: str) -> dict[str, Any]:
    verify_frozen_sources()
    packets, index = load_stage2_packets()
    topic_mapping = load_topic_mapping()
    anchors = load_anchors()
    partitions = load_partitions(packets)

    if set(topic_mapping.values()) != set(anchors):
        raise ValueError("Topic mapping and focal-anchor topics do not match")

    partition_order = sorted(
        partitions,
        key=lambda row: (
            sha256_text(PACKET_ORDER_SALT + row["task_id"]),
            row["task_id"],
        ),
    )

    alignment_packets: list[dict[str, Any]] = []
    private_packets: list[dict[str, Any]] = []
    cluster_total = 0

    for packet_number, row in enumerate(partition_order, start=1):
        source_packet_id = row["packet_id"]
        source_packet = packets[source_packet_id]
        topic_packet_id = source_packet.get("topic_packet_id")
        if topic_packet_id not in topic_mapping:
            raise ValueError(f"Unknown topic packet ID: {topic_packet_id}")
        topic_id = topic_mapping[topic_packet_id]
        anchor = anchors[topic_id]
        target_text = {
            target["target_id"]: target["canonical_target"].strip()
            for target in source_packet["targets"]
        }

        alignment_packet_id = f"AU-E1-FA1-P{packet_number:03d}"
        source_clusters = row["partition"]["clusters"]
        ordered_clusters = sorted(
            source_clusters,
            key=lambda cluster: (
                sha256_text(
                    CLUSTER_ORDER_SALT
                    + row["task_id"]
                    + "|"
                    + cluster["cluster_id"]
                ),
                cluster["cluster_id"],
            ),
        )

        visible_clusters: list[dict[str, Any]] = []
        private_cluster_rows: list[dict[str, Any]] = []
        for cluster_number, cluster in enumerate(ordered_clusters, start=1):
            cluster_ref = f"K{cluster_number:03d}"
            member_ids = sorted(
                cluster["target_ids"],
                key=lambda target_id: (
                    sha256_text(
                        MEMBER_ORDER_SALT
                        + row["task_id"]
                        + "|"
                        + cluster["cluster_id"]
                        + "|"
                        + target_id
                    ),
                    target_id,
                ),
            )
            visible_clusters.append(
                {
                    "cluster_ref": cluster_ref,
                    "member_targets": [target_text[target_id] for target_id in member_ids],
                }
            )
            private_cluster_rows.append(
                {
                    "cluster_ref": cluster_ref,
                    "source_cluster_id": cluster["cluster_id"],
                    "source_cluster_uid": f"{row['task_id']}:{cluster['cluster_id']}",
                    "source_target_ids": member_ids,
                }
            )

        cluster_total += len(visible_clusters)
        alignment_packets.append(
            {
                "schema_version": "au-e1-fa1-alignment-packet-v1",
                "study": "Attainable Unknowns API Pilot 0.1",
                "protocol_id": "FA1",
                "alignment_packet_id": alignment_packet_id,
                "focal_unknown_anchor": anchor,
                "cluster_count": len(visible_clusters),
                "clusters": visible_clusters,
            }
        )
        private_packets.append(
            {
                "alignment_packet_id": alignment_packet_id,
                "source_task_id": row["task_id"],
                "source_packet_id": source_packet_id,
                "source_partition_replicate": row.get("partition_replicate"),
                "source_partitioner_model_key": row.get("model_key"),
                "representation_set_id": source_packet.get("representation_set_id"),
                "topic_packet_id": topic_packet_id,
                "topic_id": topic_id,
                "clusters": private_cluster_rows,
            }
        )

    if len(alignment_packets) != EXPECTED_PARTITIONS or cluster_total != EXPECTED_CLUSTERS:
        raise ValueError("FA1 packet construction coverage mismatch")

    source_hashes = {
        rel(FOCAL_ANCHORS): sha256_file(FOCAL_ANCHORS),
        rel(STAGE2_INDEX): sha256_file(STAGE2_INDEX),
        rel(STAGE2_PRIVATE_KEY): sha256_file(STAGE2_PRIVATE_KEY),
        rel(P1D3_PARTITIONS): sha256_file(P1D3_PARTITIONS),
    }
    bundle_material = (
        BUNDLE_SALT
        + implementation_commit
        + "|"
        + "|".join(f"{path}:{digest}" for path, digest in sorted(source_hashes.items()))
    )
    bundle_id = f"AU-E1-FA1-{sha256_text(bundle_material)[:16]}"

    return {
        "bundle_id": bundle_id,
        "packets": alignment_packets,
        "private_packets": private_packets,
        "cluster_total": cluster_total,
        "source_hashes": source_hashes,
        "stage2_index": index,
    }


def preflight(implementation_ref: str) -> dict[str, Any]:
    implementation_commit = verify_implementation(implementation_ref)
    state = build_state(implementation_commit)
    sizes = [packet["cluster_count"] for packet in state["packets"]]
    return {
        "status": "fa1_packet_preflight_complete_no_files_written",
        "implementation_commit": implementation_commit,
        "bundle_id": state["bundle_id"],
        "alignment_packets": len(state["packets"]),
        "cluster_instances": state["cluster_total"],
        "minimum_clusters_per_packet": min(sizes),
        "maximum_clusters_per_packet": max(sizes),
        "focal_anchors": EXPECTED_ANCHORS,
        "original_model_gap_metadata_used": False,
        "cluster_descriptive_names_used": False,
    }


def generate(implementation_ref: str) -> None:
    implementation_commit = verify_implementation(implementation_ref)
    state = build_state(implementation_commit)
    output_dir = GENERATED_ROOT / state["bundle_id"]
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing FA1 bundle: {output_dir}")

    blinded_dir = output_dir / "blinded"
    private_dir = output_dir / "private"
    blinded_dir.mkdir(parents=True)
    private_dir.mkdir(parents=True)

    instructions_copy = blinded_dir / "E1_FOCAL_ALIGNMENT_INSTRUCTIONS.md"
    instructions_copy.write_bytes(INSTRUCTIONS.read_bytes())

    index_rows: list[dict[str, Any]] = []
    for packet in state["packets"]:
        path = blinded_dir / f"{packet['alignment_packet_id']}.json"
        write_json(path, packet)
        index_rows.append(
            {
                "alignment_packet_id": packet["alignment_packet_id"],
                "cluster_count": packet["cluster_count"],
                "path": rel(path),
                "sha256": sha256_file(path),
            }
        )

    packet_index = {
        "schema_version": "au-e1-fa1-packet-index-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "FA1",
        "bundle_id": state["bundle_id"],
        "packet_count": len(index_rows),
        "cluster_instance_count": state["cluster_total"],
        "instructions_path": rel(instructions_copy),
        "instructions_sha256": sha256_file(instructions_copy),
        "packets": index_rows,
    }
    index_path = blinded_dir / "FA1_PACKET_INDEX.json"
    write_json(index_path, packet_index)

    private_key = {
        "schema_version": "au-e1-fa1-private-key-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "FA1",
        "bundle_id": state["bundle_id"],
        "warning": (
            "Do not provide this file to FA1 alignment raters. It maps opaque alignment "
            "packets and cluster references to frozen Stage 2 provenance."
        ),
        "implementation_commit": implementation_commit,
        "packets": state["private_packets"],
    }
    private_path = private_dir / "FA1_PRIVATE_KEY.json"
    write_json(private_path, private_key)

    record = {
        "schema_version": "au-e1-fa1-generation-record-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "FA1",
        "bundle_id": state["bundle_id"],
        "generated_at_utc": utc_now(),
        "implementation_commit": implementation_commit,
        "implementation_signature_verified": True,
        "generator_path": rel(GENERATOR),
        "generator_sha256": sha256_file(GENERATOR),
        "protocol_path": rel(PROTOCOL),
        "protocol_sha256": sha256_file(PROTOCOL),
        "instructions_source_path": rel(INSTRUCTIONS),
        "instructions_source_sha256": sha256_file(INSTRUCTIONS),
        "packet_index_path": rel(index_path),
        "packet_index_sha256": sha256_file(index_path),
        "private_key_path": rel(private_path),
        "private_key_sha256": sha256_file(private_path),
        "source_files_sha256": state["source_hashes"],
        "alignment_packet_count": len(index_rows),
        "cluster_instance_count": state["cluster_total"],
        "focal_anchor_count": EXPECTED_ANCHORS,
        "cluster_descriptive_names_used": False,
        "j1_joined_metadata_used": False,
    }
    write_json(output_dir / "FA1_GENERATION_RECORD.json", record)

    print(
        json.dumps(
            {
                "status": "fa1_packet_bundle_generated",
                "bundle_id": state["bundle_id"],
                "output_dir": rel(output_dir),
                "alignment_packets": len(index_rows),
                "cluster_instances": state["cluster_total"],
                "next_step": "freeze this generated bundle in a founder-signed Git commit before real primary coding",
            },
            indent=2,
            sort_keys=True,
        )
    )


def self_test() -> None:
    # Test only deterministic ordering primitives and code-independent invariants.
    task_ids = ["P1-X", "P2-X", "P3-X"]
    first = sorted(task_ids, key=lambda x: (sha256_text(PACKET_ORDER_SALT + x), x))
    second = sorted(task_ids, key=lambda x: (sha256_text(PACKET_ORDER_SALT + x), x))
    if first != second or set(first) != set(task_ids):
        raise AssertionError("Deterministic packet ordering failed")

    cluster_ids = ["C001", "C002", "C003", "C004"]
    ordered = sorted(
        cluster_ids,
        key=lambda cid: (sha256_text(CLUSTER_ORDER_SALT + "P1-X|" + cid), cid),
    )
    if len(ordered) != len(cluster_ids) or set(ordered) != set(cluster_ids):
        raise AssertionError("Deterministic cluster ordering failed")

    print(
        json.dumps(
            {
                "status": "fa1_generator_self_test_passed",
                "packet_order": first,
                "cluster_order": ordered,
            },
            indent=2,
            sort_keys=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("self-test", help="Run local deterministic tests; no repository writes or API calls")

    pre = sub.add_parser("preflight", help="Verify signed implementation and frozen inputs; write nothing")
    pre.add_argument("--implementation-commit", required=True)

    gen = sub.add_parser("generate", help="Generate the blinded FA1 packet bundle")
    gen.add_argument("--implementation-commit", required=True)

    args = parser.parse_args()
    if args.command == "self-test":
        self_test()
    elif args.command == "preflight":
        print(json.dumps(preflight(args.implementation_commit), indent=2, sort_keys=True))
    elif args.command == "generate":
        generate(args.implementation_commit)
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
