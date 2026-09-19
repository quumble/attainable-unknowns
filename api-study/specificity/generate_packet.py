#!/usr/bin/env python3
"""Generate the deterministic blinded specificity packet under Protocol B1."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "api-study" / "data" / "raw"
SPEC_DIR = ROOT / "api-study" / "specificity"
GENERATED_DIR = SPEC_DIR / "generated"
FREEZE_RECORD = ROOT / "prereg" / "API_PILOT_0.1_PREPACKET_FREEZE_RECORD.json"
CODEBOOK = ROOT / "api-study" / "SPECIFICITY_CODEBOOK.md"
INSTRUCTIONS = SPEC_DIR / "CODER_INSTRUCTIONS.md"

EXPECTED_MODELS = ("haiku", "luna", "sonnet", "terra")
EXPECTED_GAPS = ("closed", "seamed", "explicit_gap")
SAMPLE_PER_STRATUM = 15
EXPECTED_SAMPLE = 180
EXPECTED_CARDS = 169

SELECTION_SALT = "AU-SPECIFICITY-V1|"
CARD_ORDER_SALT = "AU-SPEC-CARD-ORDER-V1|"
CODER_ORDER_SALT = "AU-SPEC-CODER-ORDER-V1|"
PACKET_SALT = "AU-SPEC-PACKET-V1|"

MANIFEST_NAMES = (
    "20260918T200715Z-luna-667cc52d.manifest.json",
    "20260918T202517Z-terra-a31f0c2b.manifest.json",
    "20260918T210718Z-haiku-c13f68a4.manifest.json",
    "20260918T225249Z-sonnet-2059332f.manifest.json",
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


def git(*args: str, text: bool = True) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=text,
    )


def committed_blob_matches_worktree(commit: str, path_text: str) -> bool:
    committed = git("rev-parse", f"{commit}:{path_text}")
    current = git("hash-object", f"--path={path_text}", path_text)
    return (
        committed.returncode == 0
        and current.returncode == 0
        and committed.stdout.strip() == current.stdout.strip()
    )


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


def verify_signed_freeze(ref: str) -> tuple[str, dict[str, Any]]:
    if not FREEZE_RECORD.is_file():
        raise FileNotFoundError(
            f"Missing {rel(FREEZE_RECORD)}; build and sign the pre-packet freeze first"
        )

    resolved = git("rev-parse", "--verify", f"{ref}^{{commit}}")
    if resolved.returncode != 0:
        raise ValueError(f"Cannot resolve freeze commit {ref}: {resolved.stderr.strip()}")
    commit = resolved.stdout.strip()

    verified = git("verify-commit", commit)
    if verified.returncode != 0:
        detail = (verified.stderr or verified.stdout).strip()
        raise ValueError(f"Founder-signed freeze verification failed for {commit}: {detail}")

    ancestor = git("merge-base", "--is-ancestor", commit, "HEAD")
    if ancestor.returncode != 0:
        raise ValueError(f"Freeze commit {commit} is not an ancestor of HEAD")

    freeze_record = load_json(FREEZE_RECORD)
    if freeze_record.get("protocol_id") != "B1":
        raise ValueError("Pre-packet freeze record is not Protocol B1")
    if freeze_record.get("packet_status") != "not_generated":
        raise ValueError("Freeze record does not state packet_status=not_generated")

    if not committed_blob_matches_worktree(commit, rel(FREEZE_RECORD)):
        raise ValueError("Working freeze record differs from the signed commit")

    frozen_files = freeze_record.get("frozen_files_sha256", {})
    if not isinstance(frozen_files, dict) or not frozen_files:
        raise ValueError("Freeze record has no frozen_files_sha256 map")

    for path_text, expected in sorted(frozen_files.items()):
        path = ROOT / path_text
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256_file(path)
        if observed != expected:
            raise ValueError(f"Working file hash mismatch for {path_text}")
        if not committed_blob_matches_worktree(commit, path_text):
            raise ValueError(
                f"Working file does not match the signed commit after Git filters: {path_text}"
            )

    return commit, freeze_record


def load_accepted_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifests: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for name in MANIFEST_NAMES:
        manifest_path = RAW_DIR / name
        manifest = load_json(manifest_path)
        if manifest.get("status") != "complete" or manifest.get("full_design_run") is not True:
            raise ValueError(f"Manifest is not a complete full-design run: {manifest_path}")
        if manifest.get("successful_requests") != 900 or manifest.get("error_requests") != 0:
            raise ValueError(f"Unexpected request counts in {manifest_path}")

        records_path = resolve_records_path(manifest_path, str(manifest.get("records_file", "")))
        observed_hash = sha256_file(records_path)
        if observed_hash != manifest.get("records_sha256"):
            raise ValueError(f"Raw SHA-256 mismatch: {records_path}")

        rows: list[dict[str, Any]] = []
        with records_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                row["_line_number"] = line_number
                rows.append(row)

        if len(rows) != 900:
            raise ValueError(f"Expected 900 records in {records_path}, found {len(rows)}")
        for row in rows:
            record_id = row.get("record_id")
            if not isinstance(record_id, str) or not record_id or record_id in seen_ids:
                raise ValueError(f"Missing or duplicate record_id: {record_id}")
            seen_ids.add(record_id)
            if row.get("run_id") != manifest.get("run_id"):
                raise ValueError(f"run_id mismatch in {records_path}")
            if row.get("model_key") != manifest.get("model_key"):
                raise ValueError(f"model_key mismatch in {records_path}")

        manifest["_manifest_path"] = rel(manifest_path)
        manifest["_manifest_sha256"] = sha256_file(manifest_path)
        manifest["_records_path"] = rel(records_path)
        manifests.append(manifest)
        records.extend(rows)

    if len(records) != 3600:
        raise ValueError(f"Expected 3,600 accepted records, found {len(records)}")
    if {m.get("model_key") for m in manifests} != set(EXPECTED_MODELS):
        raise ValueError("Accepted manifest set does not contain the four expected models")
    return records, manifests


def eligible(row: dict[str, Any]) -> bool:
    question = row.get("parsed_question")
    return (
        row.get("status") == "success"
        and row.get("format_valid") is True
        and row.get("parsed_none") is not True
        and isinstance(question, str)
        and bool(question)
    )


def stratified_sample(
    records: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    cells: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        if eligible(row):
            key = (str(row.get("model_key")), str(row.get("gap_structure")))
            cells[key].append(row)

    expected_cells = {(model, gap) for model in EXPECTED_MODELS for gap in EXPECTED_GAPS}
    if set(cells) != expected_cells:
        raise ValueError(f"Eligible cell set mismatch: {sorted(cells)}")

    selected: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for model in EXPECTED_MODELS:
        for gap in EXPECTED_GAPS:
            key = (model, gap)
            cell = cells[key]
            counts[f"{model}::{gap}"] = len(cell)
            if len(cell) < SAMPLE_PER_STRATUM:
                raise ValueError(f"Cell {key} has only {len(cell)} eligible records")
            ranked = sorted(
                cell,
                key=lambda row: (
                    sha256_text(SELECTION_SALT + str(row["record_id"])),
                    str(row["record_id"]),
                ),
            )
            for rank, row in enumerate(ranked[:SAMPLE_PER_STRATUM], start=1):
                item = dict(row)
                item["_selection_hash"] = sha256_text(
                    SELECTION_SALT + str(row["record_id"])
                )
                item["_selection_rank"] = rank
                selected.append(item)

    if len(selected) != EXPECTED_SAMPLE:
        raise ValueError(f"Expected {EXPECTED_SAMPLE} sampled observations, found {len(selected)}")
    return selected, counts


def make_cards(
    selected: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], dict[str, str]]:
    groups: dict[str, dict[str, Any]] = {}
    for row in selected:
        visible = {
            "passage": row.get("passage"),
            "question": row.get("parsed_question"),
        }
        if not isinstance(visible["passage"], str) or not isinstance(visible["question"], str):
            raise ValueError("Sampled row lacks visible passage or question string")
        key = compact_json(visible)
        groups.setdefault(key, visible)

    ordered_keys = sorted(groups, key=lambda key: sha256_text(CARD_ORDER_SALT + key))
    cards: list[dict[str, str]] = []
    key_to_card: dict[str, str] = {}
    for index, key in enumerate(ordered_keys, start=1):
        card_id = f"AU-SPEC-B1-{index:04d}"
        key_to_card[key] = card_id
        cards.append({"card_id": card_id, **groups[key]})

    if len(cards) != EXPECTED_CARDS:
        raise ValueError(
            f"B1 expected {EXPECTED_CARDS} unique visible cards, found {len(cards)}; stop"
        )
    return cards, key_to_card


def mechanical_state() -> dict[str, Any]:
    records, manifests = load_accepted_records()
    selected, eligible_counts = stratified_sample(records)
    cards, key_to_card = make_cards(selected)

    selected_ids = sorted(str(row["record_id"]) for row in selected)
    packet_digest = sha256_text(PACKET_SALT + "|".join(selected_ids))
    packet_id = f"AU-SPEC-B1-{packet_digest[:16]}"

    observation_rows: list[dict[str, Any]] = []
    for row in selected:
        visible_key = compact_json(
            {"passage": row["passage"], "question": row["parsed_question"]}
        )
        observation_rows.append(
            {
                "card_id": key_to_card[visible_key],
                "record_id": row["record_id"],
                "model_key": row["model_key"],
                "provider": row.get("provider"),
                "model_requested": row.get("model_requested"),
                "run_id": row["run_id"],
                "gap_structure": row["gap_structure"],
                "condition_id": row.get("condition_id"),
                "domain_class": row.get("domain_class"),
                "topic_id": row.get("topic_id"),
                "topic_label": row.get("topic_label"),
                "replicate": row.get("replicate"),
                "sequence": row.get("sequence"),
                "selection_hash": row["_selection_hash"],
                "selection_rank_within_model_gap": row["_selection_rank"],
            }
        )

    observation_rows.sort(
        key=lambda row: (
            str(row["model_key"]),
            str(row["gap_structure"]),
            int(row["selection_rank_within_model_gap"]),
        )
    )
    multiplicities = Counter(row["card_id"] for row in observation_rows)

    return {
        "packet_id": packet_id,
        "records": records,
        "manifests": manifests,
        "selected": selected,
        "cards": cards,
        "observations": observation_rows,
        "eligible_counts": eligible_counts,
        "multiplicities": dict(sorted(multiplicities.items())),
    }


def preflight() -> None:
    state = mechanical_state()
    print(json.dumps({
        "status": "preflight_complete_no_packet_written",
        "packet_id": state["packet_id"],
        "accepted_records": len(state["records"]),
        "eligible_observations": sum(state["eligible_counts"].values()),
        "eligible_by_model_gap": state["eligible_counts"],
        "sampled_observations": len(state["observations"]),
        "unique_visible_cards": len(state["cards"]),
        "cards_with_multiplicity_gt_1": sum(
            count > 1 for count in state["multiplicities"].values()
        ),
        "maximum_card_multiplicity": max(state["multiplicities"].values()),
    }, indent=2, sort_keys=True))


def generate(freeze_ref: str) -> None:
    freeze_commit, freeze_record = verify_signed_freeze(freeze_ref)
    state = mechanical_state()
    packet_id = state["packet_id"]
    output_dir = GENERATED_DIR / packet_id
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing packet directory: {output_dir}")

    blinded_dir = output_dir / "blinded"
    private_dir = output_dir / "private"
    blinded_dir.mkdir(parents=True)
    private_dir.mkdir(parents=True)

    common = {
        "schema_version": "au-specificity-packet-v1",
        "protocol_id": "B1",
        "packet_id": packet_id,
        "card_count": len(state["cards"]),
        "allowed_codes": ["1", "0", "U"],
        "codebook_path": "SPECIFICITY_CODEBOOK.md",
    }

    master = {**common, "coder_id": "MASTER", "cards": state["cards"]}
    write_json(blinded_dir / "MASTER_PACKET.json", master)

    for coder_id in ("C1", "C2", "C3"):
        ordered_cards = sorted(
            state["cards"],
            key=lambda card: sha256_text(
                CODER_ORDER_SALT + coder_id + "|" + card["card_id"]
            ),
        )
        write_json(
            blinded_dir / f"CODER_{coder_id}.json",
            {**common, "coder_id": coder_id, "cards": ordered_cards},
        )

    (blinded_dir / "SPECIFICITY_CODEBOOK.md").write_bytes(CODEBOOK.read_bytes())
    (blinded_dir / "CODER_INSTRUCTIONS.md").write_bytes(INSTRUCTIONS.read_bytes())

    unblinding_key = {
        "schema_version": "au-specificity-unblinding-key-v1",
        "protocol_id": "B1",
        "packet_id": packet_id,
        "warning": "Do not provide this file to coders or open it before blind coding is frozen.",
        "eligible_counts_by_model_gap": state["eligible_counts"],
        "sample_per_model_gap": SAMPLE_PER_STRATUM,
        "sampled_observations": len(state["observations"]),
        "unique_visible_cards": len(state["cards"]),
        "card_multiplicity": state["multiplicities"],
        "observations": state["observations"],
    }
    write_json(private_dir / "UNBLINDING_KEY.json", unblinding_key)

    packet_files = sorted(
        path for path in output_dir.rglob("*") if path.is_file()
    )
    generation_record = {
        "schema_version": "au-specificity-generation-record-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "B1",
        "packet_id": packet_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "signed_prepacket_freeze_commit": freeze_commit,
        "signed_prepacket_freeze_verified": True,
        "prepacket_freeze_record_sha256": sha256_file(FREEZE_RECORD),
        "accepted_runs": [
            {
                "model_key": manifest["model_key"],
                "run_id": manifest["run_id"],
                "manifest_path": manifest["_manifest_path"],
                "manifest_sha256": manifest["_manifest_sha256"],
                "records_path": manifest["_records_path"],
                "records_sha256": manifest["records_sha256"],
            }
            for manifest in sorted(state["manifests"], key=lambda row: row["model_key"])
        ],
        "selection": {
            "salt": SELECTION_SALT,
            "sample_per_model_gap": SAMPLE_PER_STRATUM,
            "eligible_counts_by_model_gap": state["eligible_counts"],
            "eligible_observations": sum(state["eligible_counts"].values()),
            "sampled_observations": len(state["observations"]),
            "unique_visible_cards": len(state["cards"]),
            "exact_visible_duplicate_collapse": True,
            "cards_with_multiplicity_gt_1": sum(
                count > 1 for count in state["multiplicities"].values()
            ),
            "maximum_card_multiplicity": max(state["multiplicities"].values()),
        },
        "semantic_codes_assigned": False,
        "blinding": {
            "coder_packets_exclude_hidden_metadata": True,
            "unblinding_key_separate": True,
            "founder_known_aggregate_primary_result": True,
        },
        "files_sha256": {
            rel(path): sha256_file(path)
            for path in packet_files
        },
        "freeze_record_declared_primary_artifact_sha256": freeze_record.get(
            "primary_analysis_artifact_sha256"
        ),
    }
    write_json(output_dir / "PACKET_GENERATION_RECORD.json", generation_record)

    print(json.dumps({
        "status": "packet_generated",
        "packet_id": packet_id,
        "output_directory": rel(output_dir),
        "sampled_observations": len(state["observations"]),
        "unique_visible_cards": len(state["cards"]),
        "coder_packets": [
            rel(blinded_dir / f"CODER_{coder_id}.json")
            for coder_id in ("C1", "C2", "C3")
        ],
        "unblinding_key": rel(private_dir / "UNBLINDING_KEY.json"),
    }, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate and report mechanical counts without writing any packet.",
    )
    mode.add_argument(
        "--freeze-commit",
        help="Founder-signed commit containing the B1 pre-packet freeze (for example HEAD).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.preflight_only:
        preflight()
    else:
        generate(args.freeze_commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
