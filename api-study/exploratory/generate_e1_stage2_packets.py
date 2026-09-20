#!/usr/bin/env python3
"""Generate the frozen E1/E1A Stage 2 blinded topic packets.

This script performs no semantic clustering. It mechanically joins the two
frozen Stage 1 canonical-target representations to the already-frozen private
topic mapping, replaces Stage 1 card IDs with packet-local opaque target IDs,
and emits 24 blinded topic packets: 12 per representation.
"""

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

PACKET_ID = "AU-E1-S1-cad71b8ce8fe0866"
STAGE1_PACKET_DIR = E1_DIR / "e1" / "generated" / PACKET_ID
PRIVATE_KEY = STAGE1_PACKET_DIR / "private" / "E1_STAGE1_PRIVATE_KEY.json"

SOL_TARGETS = (
    E1_DIR / "e1" / "stage1_outputs" / PACKET_ID / "sol" / "CANONICAL_TARGETS.jsonl"
)
OPUS_TARGETS = (
    E1_DIR / "e1" / "stage1_outputs" / PACKET_ID / "opus_d2_512" / "CANONICAL_TARGETS.jsonl"
)

STAGE2_INSTRUCTIONS = E1_DIR / "STAGE2_PARTITION_INSTRUCTIONS.md"
GENERATED_ROOT = E1_DIR / "e1" / "stage2" / "generated"

STAGE1_FREEZE_COMMIT = "07722a3da8b34b5f01a57f5caf13cf709ea45e18"
EXPECTED_CARDS = 1984
EXPECTED_TOPICS = 12
EXPECTED_REPRESENTATIONS = ("sol", "opus")

REPRESENTATION_ORDER_SALT = "AU-E1-STAGE2-REPRESENTATION-ORDER-v1|"
TARGET_ORDER_SALT = "AU-E1-STAGE2-TARGET-ORDER-v1|"
BUNDLE_SALT = "AU-E1-STAGE2-BUNDLE-v1|"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
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
        check=False,
        capture_output=True,
        text=True,
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
    path_text = rel(path)
    committed = git("rev-parse", f"{commit}:{path_text}")
    current = git("hash-object", f"--path={path_text}", path_text)
    return (
        committed.returncode == 0
        and current.returncode == 0
        and committed.stdout.strip() == current.stdout.strip()
    )


def verify_stage1_freeze() -> str:
    commit = verify_signed_commit(STAGE1_FREEZE_COMMIT, "Stage 1 dual-representation freeze")
    if commit != STAGE1_FREEZE_COMMIT:
        raise ValueError("Resolved Stage 1 freeze commit differs from frozen SHA")

    for path in (PRIVATE_KEY, SOL_TARGETS, OPUS_TARGETS):
        if not path.is_file():
            raise FileNotFoundError(path)
        if not committed_blob_matches_worktree(commit, path):
            raise ValueError(
                f"Working Stage 2 input differs from frozen Stage 1 commit: {rel(path)}"
            )
    return commit


def verify_implementation_commit(ref: str, freeze_commit: str) -> str:
    commit = verify_signed_commit(ref, "Stage 2 packet-generator implementation")
    if git("merge-base", "--is-ancestor", freeze_commit, commit).returncode != 0:
        raise ValueError(
            f"Stage 1 freeze {freeze_commit} is not an ancestor of implementation {commit}"
        )

    for path in (Path(__file__).resolve(), STAGE2_INSTRUCTIONS):
        if not path.is_file():
            raise FileNotFoundError(path)
        if not committed_blob_matches_worktree(commit, path):
            raise ValueError(
                f"Working implementation file differs from signed commit {commit}: {rel(path)}"
            )
    return commit


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


def load_private_mapping() -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    key = load_json(PRIVATE_KEY)
    if key.get("packet_id") != PACKET_ID:
        raise ValueError("Private key packet ID mismatch")

    cards = key.get("cards")
    if not isinstance(cards, list) or len(cards) != EXPECTED_CARDS:
        raise ValueError(f"Private key must contain {EXPECTED_CARDS} card mappings")

    card_map: dict[str, dict[str, Any]] = {}
    topic_packets: set[str] = set()
    for row in cards:
        if not isinstance(row, dict):
            raise ValueError("Private card mapping contains a non-object row")
        card_id = row.get("card_id")
        topic_packet_id = row.get("topic_packet_id")
        if not isinstance(card_id, str) or not card_id:
            raise ValueError("Private mapping has invalid card_id")
        if not isinstance(topic_packet_id, str) or not topic_packet_id:
            raise ValueError(f"Private mapping has invalid topic packet for {card_id}")
        if card_id in card_map:
            raise ValueError(f"Duplicate private mapping for {card_id}")
        card_map[card_id] = row
        topic_packets.add(topic_packet_id)

    if len(topic_packets) != EXPECTED_TOPICS:
        raise ValueError(
            f"Expected {EXPECTED_TOPICS} opaque topic packets, found {len(topic_packets)}"
        )

    topic_mapping = key.get("topic_packet_mapping")
    if not isinstance(topic_mapping, list) or len(topic_mapping) != EXPECTED_TOPICS:
        raise ValueError("Private key topic_packet_mapping is missing or incomplete")

    cleaned_topic_mapping: list[dict[str, str]] = []
    for row in topic_mapping:
        cleaned_topic_mapping.append(
            {
                "topic_packet_id": str(row["topic_packet_id"]),
                "topic_id": str(row["topic_id"]),
            }
        )

    return card_map, cleaned_topic_mapping


def load_representation(
    path: Path,
    expected_representation: str,
    expected_card_ids: set[str],
) -> dict[str, dict[str, Any]]:
    rows = load_jsonl(path)
    if len(rows) != EXPECTED_CARDS:
        raise ValueError(
            f"{expected_representation} must contain {EXPECTED_CARDS} rows; found {len(rows)}"
        )

    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if set(row) != {"card_id", "canonical_target", "representation", "uncertain"}:
            raise ValueError(
                f"Unexpected fields in {expected_representation} Stage 1 output: {sorted(row)}"
            )
        card_id = row["card_id"]
        if row["representation"] != expected_representation:
            raise ValueError(
                f"Representation mismatch for {card_id}: {row['representation']}"
            )
        if not isinstance(card_id, str) or card_id not in expected_card_ids:
            raise ValueError(f"Unknown card_id in {expected_representation}: {card_id!r}")
        if card_id in out:
            raise ValueError(f"Duplicate {expected_representation} card_id: {card_id}")
        if not isinstance(row["canonical_target"], str) or not row["canonical_target"].strip():
            raise ValueError(f"Empty canonical target for {card_id}")
        if not isinstance(row["uncertain"], bool):
            raise ValueError(f"Non-boolean uncertain value for {card_id}")
        out[card_id] = row

    missing = expected_card_ids - set(out)
    extra = set(out) - expected_card_ids
    if missing or extra:
        raise ValueError(
            f"{expected_representation} card coverage mismatch: "
            f"missing={len(missing)}, extra={len(extra)}"
        )
    return out


def representation_set_ids() -> dict[str, str]:
    ordered = sorted(
        EXPECTED_REPRESENTATIONS,
        key=lambda name: (sha256_text(REPRESENTATION_ORDER_SALT + name), name),
    )
    return {
        name: f"AU-E1-R{index:02d}" for index, name in enumerate(ordered, start=1)
    }


def make_state() -> dict[str, Any]:
    freeze_commit = verify_stage1_freeze()
    card_private, topic_mapping = load_private_mapping()
    card_ids = set(card_private)

    representations = {
        "sol": load_representation(SOL_TARGETS, "sol", card_ids),
        "opus": load_representation(OPUS_TARGETS, "opus", card_ids),
    }
    rep_ids = representation_set_ids()

    topics = sorted({row["topic_packet_id"] for row in card_private.values()})
    if len(topics) != EXPECTED_TOPICS:
        raise ValueError("Unexpected topic packet count")

    packets: list[dict[str, Any]] = []
    private_target_mapping: list[dict[str, Any]] = []

    for representation in EXPECTED_REPRESENTATIONS:
        representation_set_id = rep_ids[representation]
        rep_rows = representations[representation]

        for topic_packet_id in topics:
            member_card_ids = [
                card_id
                for card_id, meta in card_private.items()
                if meta["topic_packet_id"] == topic_packet_id
            ]
            ordered_cards = sorted(
                member_card_ids,
                key=lambda card_id: (
                    sha256_text(
                        TARGET_ORDER_SALT
                        + representation_set_id
                        + "|"
                        + topic_packet_id
                        + "|"
                        + card_id
                    ),
                    card_id,
                ),
            )
            if not ordered_cards:
                raise ValueError(f"Empty topic packet: {topic_packet_id}")

            packet_id = f"AU-E1-S2-{representation_set_id.split('-')[-1]}-{topic_packet_id.split('-')[-1]}"
            visible_targets: list[dict[str, str]] = []

            for index, card_id in enumerate(ordered_cards, start=1):
                target_id = f"T{index:03d}"
                canonical_target = rep_rows[card_id]["canonical_target"].strip()
                visible_targets.append(
                    {
                        "target_id": target_id,
                        "canonical_target": canonical_target,
                    }
                )
                private_target_mapping.append(
                    {
                        "packet_id": packet_id,
                        "representation_set_id": representation_set_id,
                        "topic_packet_id": topic_packet_id,
                        "target_id": target_id,
                        "card_id": card_id,
                        "representation": representation,
                        "stage1_uncertain": rep_rows[card_id]["uncertain"],
                        "multiplicity": int(card_private[card_id]["multiplicity"]),
                    }
                )

            packets.append(
                {
                    "schema_version": "au-e1-stage2-topic-packet-v1",
                    "study": "Attainable Unknowns API Pilot 0.1",
                    "protocol_id": "E1",
                    "amendment_id": "E1A",
                    "stage": "stage2_blinded_topic_partition",
                    "packet_id": packet_id,
                    "representation_set_id": representation_set_id,
                    "topic_packet_id": topic_packet_id,
                    "target_count": len(visible_targets),
                    "targets": visible_targets,
                }
            )

    if len(packets) != EXPECTED_TOPICS * len(EXPECTED_REPRESENTATIONS):
        raise ValueError("Unexpected Stage 2 packet count")
    if len(private_target_mapping) != EXPECTED_CARDS * len(EXPECTED_REPRESENTATIONS):
        raise ValueError("Unexpected Stage 2 target mapping count")

    source_hashes = {
        rel(PRIVATE_KEY): sha256_file(PRIVATE_KEY),
        rel(SOL_TARGETS): sha256_file(SOL_TARGETS),
        rel(OPUS_TARGETS): sha256_file(OPUS_TARGETS),
    }
    bundle_material = (
        BUNDLE_SALT
        + freeze_commit
        + "|"
        + "|".join(f"{path}:{digest}" for path, digest in sorted(source_hashes.items()))
    )
    bundle_id = f"AU-E1-S2-{sha256_text(bundle_material)[:16]}"

    return {
        "freeze_commit": freeze_commit,
        "bundle_id": bundle_id,
        "packets": packets,
        "rep_ids": rep_ids,
        "topic_mapping": topic_mapping,
        "private_target_mapping": private_target_mapping,
        "source_hashes": source_hashes,
    }


def preflight() -> None:
    state = make_state()
    packet_sizes = [packet["target_count"] for packet in state["packets"]]
    by_representation: dict[str, int] = {}
    for packet in state["packets"]:
        by_representation[packet["representation_set_id"]] = (
            by_representation.get(packet["representation_set_id"], 0)
            + packet["target_count"]
        )

    print(
        json.dumps(
            {
                "status": "e1_stage2_packet_preflight_complete_no_files_written",
                "stage1_freeze_commit": state["freeze_commit"],
                "bundle_id": state["bundle_id"],
                "topic_packets_total": len(state["packets"]),
                "representation_sets": len(state["rep_ids"]),
                "targets_per_representation_set": by_representation,
                "total_visible_target_rows": sum(packet_sizes),
                "minimum_topic_packet_size": min(packet_sizes),
                "maximum_topic_packet_size": max(packet_sizes),
                "semantic_partitions_assigned": False,
                "cluster_names_assigned": False,
                "model_gap_metadata_rejoined": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


def generate(implementation_ref: str) -> None:
    state = make_state()
    implementation_commit = verify_implementation_commit(
        implementation_ref, state["freeze_commit"]
    )

    output_dir = GENERATED_ROOT / state["bundle_id"]
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing Stage 2 bundle: {output_dir}"
        )

    blinded_dir = output_dir / "blinded"
    private_dir = output_dir / "private"
    blinded_dir.mkdir(parents=True)
    private_dir.mkdir(parents=True)

    instructions_path = blinded_dir / "STAGE2_PARTITION_INSTRUCTIONS.md"
    instructions_path.write_bytes(STAGE2_INSTRUCTIONS.read_bytes())

    packet_index_rows: list[dict[str, Any]] = []
    for packet in sorted(state["packets"], key=lambda row: row["packet_id"]):
        packet_path = blinded_dir / f"{packet['packet_id']}.json"
        write_json(packet_path, packet)
        packet_index_rows.append(
            {
                "packet_id": packet["packet_id"],
                "representation_set_id": packet["representation_set_id"],
                "topic_packet_id": packet["topic_packet_id"],
                "target_count": packet["target_count"],
                "path": rel(packet_path),
                "sha256": sha256_file(packet_path),
            }
        )

    index = {
        "schema_version": "au-e1-stage2-packet-index-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "E1",
        "amendment_id": "E1A",
        "bundle_id": state["bundle_id"],
        "packet_count": len(packet_index_rows),
        "representation_set_count": len(state["rep_ids"]),
        "topic_packet_count_per_representation": EXPECTED_TOPICS,
        "instructions_path": rel(instructions_path),
        "instructions_sha256": sha256_file(instructions_path),
        "packets": packet_index_rows,
    }
    index_path = blinded_dir / "STAGE2_PACKET_INDEX.json"
    write_json(index_path, index)

    private_key = {
        "schema_version": "au-e1-stage2-private-key-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "E1",
        "amendment_id": "E1A",
        "bundle_id": state["bundle_id"],
        "warning": (
            "Do not provide this file to Stage 2 partitioners. It maps opaque "
            "representation/topic/target identifiers to Stage 1 provenance."
        ),
        "stage1_freeze_commit": state["freeze_commit"],
        "stage2_generator_implementation_commit": implementation_commit,
        "representation_mapping": [
            {
                "representation_set_id": opaque,
                "representation": representation,
                "source_path": rel(
                    SOL_TARGETS if representation == "sol" else OPUS_TARGETS
                ),
                "source_sha256": state["source_hashes"][
                    rel(SOL_TARGETS if representation == "sol" else OPUS_TARGETS)
                ],
            }
            for representation, opaque in sorted(
                state["rep_ids"].items(), key=lambda item: item[1]
            )
        ],
        "topic_packet_mapping": state["topic_mapping"],
        "targets": state["private_target_mapping"],
    }
    private_key_path = private_dir / "E1_STAGE2_PRIVATE_KEY.json"
    write_json(private_key_path, private_key)

    generation_record = {
        "schema_version": "au-e1-stage2-generation-record-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "E1",
        "amendment_id": "E1A",
        "bundle_id": state["bundle_id"],
        "generated_at_utc": utc_now(),
        "stage1_freeze_commit": state["freeze_commit"],
        "stage1_freeze_signature_verified": True,
        "stage2_generator_implementation_commit": implementation_commit,
        "stage2_generator_signature_verified": True,
        "generator_path": rel(Path(__file__).resolve()),
        "generator_sha256": sha256_file(Path(__file__).resolve()),
        "instructions_source_path": rel(STAGE2_INSTRUCTIONS),
        "instructions_source_sha256": sha256_file(STAGE2_INSTRUCTIONS),
        "source_files_sha256": state["source_hashes"],
        "packet_index_path": rel(index_path),
        "packet_index_sha256": sha256_file(index_path),
        "private_key_path": rel(private_key_path),
        "private_key_sha256": sha256_file(private_key_path),
        "topic_packets_total": len(packet_index_rows),
        "total_visible_target_rows": sum(row["target_count"] for row in packet_index_rows),
        "semantic_partitions_assigned": False,
        "cluster_names_assigned": False,
        "model_gap_metadata_rejoined": False,
    }
    generation_record_path = output_dir / "STAGE2_GENERATION_RECORD.json"
    write_json(generation_record_path, generation_record)

    print(
        json.dumps(
            {
                "status": "e1_stage2_packets_generated",
                "bundle_id": state["bundle_id"],
                "output_dir": rel(output_dir),
                "topic_packets": len(packet_index_rows),
                "total_visible_target_rows": generation_record[
                    "total_visible_target_rows"
                ],
                "packet_index_sha256": generation_record["packet_index_sha256"],
                "private_key_sha256": generation_record["private_key_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "preflight",
        help="Verify frozen Stage 1 inputs and compute Stage 2 packet structure; write nothing",
    )

    gen = sub.add_parser(
        "generate",
        help="Generate the blinded Stage 2 packet bundle",
    )
    gen.add_argument("--implementation-commit", required=True)

    args = parser.parse_args()

    if args.command == "preflight":
        preflight()
    elif args.command == "generate":
        generate(args.implementation_commit)
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
