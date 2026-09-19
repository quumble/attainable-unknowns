#!/usr/bin/env python3
"""Generate the deterministic blinded Stage 1 corpus packet for E1."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "api-study" / "data" / "raw"
E1_DIR = ROOT / "api-study" / "exploratory"
GENERATED_DIR = E1_DIR / "e1" / "generated"
E1_PROTOCOL = E1_DIR / "API_PILOT_0.1_TARGET_CLUSTERING_E1.md"
STAGE1_INSTRUCTIONS = E1_DIR / "STAGE1_CANONICALIZATION_INSTRUCTIONS.md"

EXPECTED_RECORDS = 3600
EXPECTED_ELIGIBLE = 2919
EXPECTED_CARDS = 1984
EXPECTED_TOPICS = 12
EXPECTED_DUPLICATE_OBSERVATIONS = 935
EXPECTED_DUPLICATE_CARDS = 345
EXPECTED_MAX_MULTIPLICITY = 38

CARD_ORDER_SALT = "AU-E1-STAGE1-CARD-ORDER-V1|"
TOPIC_ORDER_SALT = "AU-E1-TOPIC-ORDER-V1|"
PACKET_SALT = "AU-E1-STAGE1-PACKET-V1|"

ACCEPTED_RUNS = (
    {
        "model_key": "luna",
        "manifest_name": "20260918T200715Z-luna-667cc52d.manifest.json",
        "run_id": "20260918T200715Z-luna-667cc52d",
        "records_sha256": "9f4d6ee729ee42360989e701cd62bc1801ca9a6b407650869ac9ef1f66d21236",
    },
    {
        "model_key": "terra",
        "manifest_name": "20260918T202517Z-terra-a31f0c2b.manifest.json",
        "run_id": "20260918T202517Z-terra-a31f0c2b",
        "records_sha256": "26e312ea7f1e493beb9e04be9a0320f462fafe2927812fdec9ad6d8537b9508e",
    },
    {
        "model_key": "haiku",
        "manifest_name": "20260918T210718Z-haiku-c13f68a4.manifest.json",
        "run_id": "20260918T210718Z-haiku-c13f68a4",
        "records_sha256": "2ce8f319e46c4fa836a72f6392125aa3762bd9f6c340477dbba8a0330debd762",
    },
    {
        "model_key": "sonnet",
        "manifest_name": "20260918T225249Z-sonnet-2059332f.manifest.json",
        "run_id": "20260918T225249Z-sonnet-2059332f",
        "records_sha256": "627d372ea407103005b8244c8ab84548bdbf0310cea274a5052bdef89cba1c92",
    },
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def compact_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


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


def committed_blob_matches_worktree(commit: str, path_text: str) -> bool:
    committed = git("rev-parse", f"{commit}:{path_text}")
    current = git("hash-object", f"--path={path_text}", path_text)
    return (
        committed.returncode == 0
        and current.returncode == 0
        and committed.stdout.strip() == current.stdout.strip()
    )


def verify_e1_commit(ref: str) -> str:
    if not E1_PROTOCOL.is_file():
        raise FileNotFoundError(E1_PROTOCOL)

    resolved = git("rev-parse", "--verify", f"{ref}^{{commit}}")
    if resolved.returncode != 0:
        raise ValueError(f"Cannot resolve E1 commit {ref}: {resolved.stderr.strip()}")
    commit = resolved.stdout.strip()

    verified = git("verify-commit", commit)
    if verified.returncode != 0:
        detail = (verified.stderr or verified.stdout).strip()
        raise ValueError(f"E1 commit signature verification failed for {commit}: {detail}")

    ancestor = git("merge-base", "--is-ancestor", commit, "HEAD")
    if ancestor.returncode != 0:
        raise ValueError(f"E1 commit {commit} is not an ancestor of HEAD")

    if not committed_blob_matches_worktree(commit, rel(E1_PROTOCOL)):
        raise ValueError("Working E1 protocol differs from the supplied signed E1 commit")

    return commit


def verify_implementation_commit(ref: str, e1_commit: str) -> str:
    resolved = git("rev-parse", "--verify", f"{ref}^{{commit}}")
    if resolved.returncode != 0:
        raise ValueError(
            f"Cannot resolve implementation commit {ref}: {resolved.stderr.strip()}"
        )
    commit = resolved.stdout.strip()

    verified = git("verify-commit", commit)
    if verified.returncode != 0:
        detail = (verified.stderr or verified.stdout).strip()
        raise ValueError(
            f"Implementation commit signature verification failed for {commit}: {detail}"
        )

    if git("merge-base", "--is-ancestor", e1_commit, commit).returncode != 0:
        raise ValueError(
            f"E1 adoption commit {e1_commit} is not an ancestor of implementation commit {commit}"
        )
    if git("merge-base", "--is-ancestor", commit, "HEAD").returncode != 0:
        raise ValueError(f"Implementation commit {commit} is not an ancestor of HEAD")

    required_paths = (E1_PROTOCOL, Path(__file__).resolve(), STAGE1_INSTRUCTIONS)
    for path in required_paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        path_text = rel(path)
        if not committed_blob_matches_worktree(commit, path_text):
            raise ValueError(
                f"Working file differs from signed implementation commit {commit}: {path_text}"
            )

    return commit


def resolve_records_path(manifest_path: Path, locator: str) -> Path:
    direct = Path(locator)
    if direct.exists():
        return direct.resolve()
    native_sibling = manifest_path.parent / direct.name
    if native_sibling.exists():
        return native_sibling.resolve()
    windows_sibling = manifest_path.parent / PureWindowsPath(locator).name
    if windows_sibling.exists():
        return windows_sibling.resolve()
    raise FileNotFoundError(f"Cannot resolve records file for {manifest_path}: {locator}")


def eligible(row: dict[str, Any]) -> bool:
    question = row.get("parsed_question")
    return (
        row.get("status") == "success"
        and row.get("format_valid") is True
        and row.get("parsed_none") is not True
        and isinstance(question, str)
        and bool(question)
    )


def load_accepted_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for expected in ACCEPTED_RUNS:
        manifest_path = RAW_DIR / expected["manifest_name"]
        if not manifest_path.is_file():
            raise FileNotFoundError(manifest_path)
        manifest = load_json(manifest_path)

        if manifest.get("status") != "complete" or manifest.get("full_design_run") is not True:
            raise ValueError(f"Manifest is not a complete full-design run: {manifest_path}")
        if manifest.get("run_id") != expected["run_id"]:
            raise ValueError(f"run_id mismatch in {manifest_path}")
        if manifest.get("model_key") != expected["model_key"]:
            raise ValueError(f"model_key mismatch in {manifest_path}")
        if manifest.get("successful_requests") != 900 or manifest.get("error_requests") != 0:
            raise ValueError(f"Unexpected request counts in {manifest_path}")

        records_path = resolve_records_path(manifest_path, str(manifest.get("records_file", "")))
        observed_hash = sha256_file(records_path)
        if observed_hash != expected["records_sha256"]:
            raise ValueError(
                f"Raw SHA-256 mismatch for {records_path}: expected {expected['records_sha256']}, "
                f"observed {observed_hash}"
            )
        if manifest.get("records_sha256") != expected["records_sha256"]:
            raise ValueError(f"Manifest raw hash differs from E1 accepted-run hash: {manifest_path}")

        rows: list[dict[str, Any]] = []
        with records_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                row["_line_number"] = line_number
                rows.append(row)

        if len(rows) != 900:
            raise ValueError(f"Expected 900 rows in {records_path}, found {len(rows)}")

        for row in rows:
            record_id = row.get("record_id")
            if not isinstance(record_id, str) or not record_id:
                raise ValueError(f"Missing record_id in {records_path}")
            if record_id in seen_ids:
                raise ValueError(f"Duplicate record_id across accepted runs: {record_id}")
            seen_ids.add(record_id)
            if row.get("run_id") != expected["run_id"]:
                raise ValueError(f"Row run_id mismatch in {records_path}")
            if row.get("model_key") != expected["model_key"]:
                raise ValueError(f"Row model_key mismatch in {records_path}")

        manifests.append(
            {
                "model_key": expected["model_key"],
                "run_id": expected["run_id"],
                "manifest_path": rel(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "records_path": rel(records_path),
                "records_sha256": observed_hash,
            }
        )
        records.extend(rows)

    if len(records) != EXPECTED_RECORDS:
        raise ValueError(f"Expected {EXPECTED_RECORDS} accepted records, found {len(records)}")
    return records, manifests


def make_state(e1_commit: str) -> dict[str, Any]:
    records, manifests = load_accepted_records()
    eligible_rows = [row for row in records if eligible(row)]
    if len(eligible_rows) != EXPECTED_ELIGIBLE:
        raise ValueError(f"Expected {EXPECTED_ELIGIBLE} eligible observations, found {len(eligible_rows)}")

    visible_groups: dict[str, dict[str, Any]] = {}
    group_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in eligible_rows:
        passage = row.get("passage")
        question = row.get("parsed_question")
        if not isinstance(passage, str) or not isinstance(question, str):
            raise ValueError("Eligible row lacks passage or parsed_question string")
        visible = {"passage": passage, "question": question}
        key = compact_json(visible)
        visible_groups.setdefault(key, visible)
        group_rows[key].append(row)

    ordered_keys = sorted(
        visible_groups,
        key=lambda key: (sha256_text(CARD_ORDER_SALT + key), key),
    )

    if len(ordered_keys) != EXPECTED_CARDS:
        raise ValueError(f"Expected {EXPECTED_CARDS} unique visible cards, found {len(ordered_keys)}")

    cards: list[dict[str, Any]] = []
    key_to_card: dict[str, str] = {}
    for index, key in enumerate(ordered_keys, start=1):
        card_id = f"AU-E1-S1-{index:04d}"
        key_to_card[key] = card_id
        cards.append({"card_id": card_id, **visible_groups[key]})

    multiplicities = Counter({key_to_card[key]: len(group_rows[key]) for key in ordered_keys})
    duplicate_observations = EXPECTED_ELIGIBLE - EXPECTED_CARDS
    duplicate_cards = sum(count > 1 for count in multiplicities.values())
    max_multiplicity = max(multiplicities.values())
    if duplicate_observations != EXPECTED_DUPLICATE_OBSERVATIONS:
        raise ValueError("Unexpected duplicate-observation count")
    if duplicate_cards != EXPECTED_DUPLICATE_CARDS:
        raise ValueError(f"Expected {EXPECTED_DUPLICATE_CARDS} duplicate cards, found {duplicate_cards}")
    if max_multiplicity != EXPECTED_MAX_MULTIPLICITY:
        raise ValueError(f"Expected max multiplicity {EXPECTED_MAX_MULTIPLICITY}, found {max_multiplicity}")

    topic_ids = sorted({str(row.get("topic_id")) for row in eligible_rows})
    if len(topic_ids) != EXPECTED_TOPICS or "None" in topic_ids:
        raise ValueError(f"Expected {EXPECTED_TOPICS} topic IDs, found {topic_ids}")
    ordered_topics = sorted(
        topic_ids,
        key=lambda topic_id: (sha256_text(TOPIC_ORDER_SALT + topic_id), topic_id),
    )
    topic_to_packet = {
        topic_id: f"AU-E1-T{index:02d}" for index, topic_id in enumerate(ordered_topics, start=1)
    }

    card_private: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    for key in ordered_keys:
        card_id = key_to_card[key]
        rows = group_rows[key]
        card_topics = {str(row.get("topic_id")) for row in rows}
        if len(card_topics) != 1:
            raise ValueError(f"Card {card_id} maps to multiple topic IDs: {sorted(card_topics)}")
        topic_id = next(iter(card_topics))
        topic_labels = sorted({str(row.get("topic_label")) for row in rows})

        card_private.append(
            {
                "card_id": card_id,
                "visible_sha256": sha256_text(key),
                "multiplicity": len(rows),
                "topic_packet_id": topic_to_packet[topic_id],
                "topic_id": topic_id,
                "topic_labels_observed": topic_labels,
                "record_ids": sorted(str(row["record_id"]) for row in rows),
            }
        )

        for row in rows:
            observations.append(
                {
                    "card_id": card_id,
                    "record_id": row["record_id"],
                    "model_key": row.get("model_key"),
                    "provider": row.get("provider"),
                    "model_requested": row.get("model_requested"),
                    "run_id": row.get("run_id"),
                    "gap_structure": row.get("gap_structure"),
                    "condition_id": row.get("condition_id"),
                    "domain_class": row.get("domain_class"),
                    "topic_id": row.get("topic_id"),
                    "topic_label": row.get("topic_label"),
                    "replicate": row.get("replicate"),
                    "sequence": row.get("sequence"),
                    "source_line_number": row.get("_line_number"),
                }
            )

    observations.sort(key=lambda row: (str(row["run_id"]), int(row["source_line_number"])))
    card_private.sort(key=lambda row: row["card_id"])

    raw_fingerprints = "|".join(
        sorted(f"{m['run_id']}:{m['records_sha256']}" for m in manifests)
    )
    packet_digest = sha256_text(PACKET_SALT + e1_commit + "|" + raw_fingerprints)
    packet_id = f"AU-E1-S1-{packet_digest[:16]}"

    return {
        "packet_id": packet_id,
        "records": records,
        "manifests": manifests,
        "eligible_rows": eligible_rows,
        "cards": cards,
        "card_private": card_private,
        "observations": observations,
        "topic_to_packet": topic_to_packet,
        "multiplicities": dict(sorted(multiplicities.items())),
    }


def preflight(e1_ref: str) -> None:
    e1_commit = verify_e1_commit(e1_ref)
    state = make_state(e1_commit)
    print(
        json.dumps(
            {
                "status": "e1_stage1_preflight_complete_no_files_written",
                "e1_commit": e1_commit,
                "packet_id": state["packet_id"],
                "accepted_records": len(state["records"]),
                "eligible_observations": len(state["eligible_rows"]),
                "unique_visible_cards": len(state["cards"]),
                "duplicate_observations_collapsed": len(state["eligible_rows"]) - len(state["cards"]),
                "cards_with_multiplicity_gt_1": sum(
                    count > 1 for count in state["multiplicities"].values()
                ),
                "maximum_card_multiplicity": max(state["multiplicities"].values()),
                "topic_families": len(state["topic_to_packet"]),
                "semantic_targets_assigned": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


def generate(e1_ref: str, implementation_ref: str) -> None:
    e1_commit = verify_e1_commit(e1_ref)
    implementation_commit = verify_implementation_commit(implementation_ref, e1_commit)
    state = make_state(e1_commit)

    if not STAGE1_INSTRUCTIONS.is_file():
        raise FileNotFoundError(
            f"Missing Stage 1 instructions: {rel(STAGE1_INSTRUCTIONS)}"
        )

    output_dir = GENERATED_DIR / state["packet_id"]
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing packet directory: {output_dir}")

    blinded_dir = output_dir / "blinded"
    private_dir = output_dir / "private"
    blinded_dir.mkdir(parents=True)
    private_dir.mkdir(parents=True)

    stage1_packet = {
        "schema_version": "au-e1-stage1-master-packet-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "E1",
        "stage": "stage1_canonical_target_extraction",
        "packet_id": state["packet_id"],
        "card_count": len(state["cards"]),
        "dispatch_rule": "Send exactly one card per semantic-coder request; never send this full packet to a Stage 1 coder.",
        "cards": state["cards"],
    }
    packet_path = blinded_dir / "STAGE1_MASTER_PACKET.json"
    write_json(packet_path, stage1_packet)

    instructions_path = blinded_dir / "STAGE1_CANONICALIZATION_INSTRUCTIONS.md"
    instructions_path.write_bytes(STAGE1_INSTRUCTIONS.read_bytes())

    private_key = {
        "schema_version": "au-e1-stage1-private-key-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "E1",
        "packet_id": state["packet_id"],
        "warning": (
            "Do not provide this file to Stage 1 or Stage 2 semantic coders. "
            "Do not join its model/gap metadata to semantic outputs before the blind semantic bundle is frozen."
        ),
        "e1_adoption_commit": e1_commit,
        "eligible_observations": len(state["eligible_rows"]),
        "unique_visible_cards": len(state["cards"]),
        "topic_packet_mapping": [
            {"topic_packet_id": opaque, "topic_id": topic_id}
            for topic_id, opaque in sorted(state["topic_to_packet"].items(), key=lambda item: item[1])
        ],
        "cards": state["card_private"],
        "observations": state["observations"],
    }
    key_path = private_dir / "E1_STAGE1_PRIVATE_KEY.json"
    write_json(key_path, private_key)

    input_manifest = {
        "schema_version": "au-e1-stage1-input-manifest-v1",
        "protocol_id": "E1",
        "packet_id": state["packet_id"],
        "e1_adoption_commit": e1_commit,
        "stage1_dispatch_contract": {
            "one_card_per_request": True,
            "permitted_visible_fields": ["card_id", "passage", "question"],
            "other_questions_same_passage_visible": False,
        },
        "files_sha256": {
            rel(packet_path): sha256_file(packet_path),
            rel(instructions_path): sha256_file(instructions_path),
        },
    }
    manifest_path = blinded_dir / "STAGE1_INPUT_MANIFEST.json"
    write_json(manifest_path, input_manifest)

    generation_record = {
        "schema_version": "au-e1-stage1-generation-record-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "E1",
        "packet_id": state["packet_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "e1_adoption_commit": e1_commit,
        "e1_signature_verified": True,
        "signed_stage1_implementation_commit": implementation_commit,
        "stage1_implementation_signature_verified": True,
        "stage1_generator_path": rel(Path(__file__).resolve()),
        "stage1_generator_sha256": sha256_file(Path(__file__).resolve()),
        "stage1_instructions_source_path": rel(STAGE1_INSTRUCTIONS),
        "stage1_instructions_source_sha256": sha256_file(STAGE1_INSTRUCTIONS),
        "e1_protocol_path": rel(E1_PROTOCOL),
        "e1_protocol_sha256": sha256_file(E1_PROTOCOL),
        "accepted_runs": state["manifests"],
        "corpus": {
            "accepted_records": len(state["records"]),
            "eligible_observations": len(state["eligible_rows"]),
            "unique_visible_cards": len(state["cards"]),
            "exact_visible_duplicate_collapse": True,
            "duplicate_observations_collapsed": len(state["eligible_rows"]) - len(state["cards"]),
            "cards_with_multiplicity_gt_1": sum(
                count > 1 for count in state["multiplicities"].values()
            ),
            "maximum_card_multiplicity": max(state["multiplicities"].values()),
            "topic_families": len(state["topic_to_packet"]),
        },
        "blinding": {
            "stage1_visible_fields": ["card_id", "passage", "question"],
            "one_card_per_stage1_request_required": True,
            "multiplicity_hidden": True,
            "topic_label_hidden": True,
            "model_hidden": True,
            "provider_hidden": True,
            "gap_structure_hidden": True,
            "run_metadata_hidden": True,
            "private_key_separate": True,
        },
        "semantic_targets_assigned": False,
        "stage2_partitions_assigned": False,
        "metadata_rejoined": False,
        "files_sha256": {
            rel(packet_path): sha256_file(packet_path),
            rel(instructions_path): sha256_file(instructions_path),
            rel(manifest_path): sha256_file(manifest_path),
            rel(key_path): sha256_file(key_path),
        },
    }
    generation_path = output_dir / "E1_STAGE1_GENERATION_RECORD.json"
    write_json(generation_path, generation_record)

    print(
        json.dumps(
            {
                "status": "e1_stage1_packet_generated",
                "packet_id": state["packet_id"],
                "output_directory": rel(output_dir),
                "eligible_observations": len(state["eligible_rows"]),
                "unique_visible_cards": len(state["cards"]),
                "stage1_master_packet": rel(packet_path),
                "stage1_instructions": rel(instructions_path),
                "stage1_input_manifest": rel(manifest_path),
                "private_key": rel(key_path),
                "semantic_targets_assigned": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight", help="Validate E1 and corpus; write nothing")
    pre.add_argument("--e1-commit", required=True)

    gen = sub.add_parser("generate", help="Generate blinded Stage 1 packet and private key")
    gen.add_argument("--e1-commit", required=True)
    gen.add_argument("--implementation-commit", required=True)

    args = parser.parse_args()
    if args.command == "preflight":
        preflight(args.e1_commit)
    elif args.command == "generate":
        generate(args.e1_commit, args.implementation_commit)
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
