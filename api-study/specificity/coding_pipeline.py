#!/usr/bin/env python3
"""Validate, reconcile, freeze, and unblind B1 specificity codes."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
ALLOWED_CODES = ("1", "0", "U")


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
    payload = json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    path.write_bytes(payload)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def packet_paths(packet_dir: Path) -> dict[str, Path]:
    return {
        "generation": packet_dir / "PACKET_GENERATION_RECORD.json",
        "master": packet_dir / "blinded" / "MASTER_PACKET.json",
        "adjudication_packet": packet_dir / "blinded" / "ADJUDICATION_PACKET.json",
        "inputs": packet_dir / "blinded" / "coding-inputs",
        "blind_final": packet_dir / "blinded" / "BLIND_CODING_FINAL.json",
        "key": packet_dir / "private" / "UNBLINDING_KEY.json",
        "results": packet_dir / "results" / "SPECIFICITY_RESULTS.json",
    }


def load_packet(path: Path, expected_coder: str | None = None) -> dict[str, Any]:
    packet = load_json(path)
    if packet.get("schema_version") != "au-specificity-packet-v1":
        raise ValueError(f"Unexpected packet schema: {path}")
    if expected_coder is not None and packet.get("coder_id") != expected_coder:
        raise ValueError(f"Expected coder_id {expected_coder} in {path}")
    cards = packet.get("cards")
    if not isinstance(cards, list):
        raise ValueError(f"Packet cards are missing: {path}")
    ids = [card.get("card_id") for card in cards if isinstance(card, dict)]
    if len(ids) != len(cards) or len(set(ids)) != len(ids):
        raise ValueError(f"Missing or duplicate card IDs in {path}")
    return packet


def validate_codes(
    codes_path: Path,
    packet_path: Path,
    expected_coder: str,
) -> tuple[dict[str, str], dict[str, Any]]:
    packet = load_packet(packet_path, expected_coder)
    value = load_json(codes_path)
    if value.get("schema_version") != "au-specificity-codes-v1":
        raise ValueError(f"Unexpected coding schema in {codes_path}")
    if value.get("packet_id") != packet.get("packet_id"):
        raise ValueError(f"packet_id mismatch in {codes_path}")
    if value.get("coder_id") != expected_coder:
        raise ValueError(f"coder_id mismatch in {codes_path}")
    if not isinstance(value.get("coder_metadata", {}), dict):
        raise ValueError(f"coder_metadata must be an object in {codes_path}")

    rows = value.get("codes")
    if not isinstance(rows, list):
        raise ValueError(f"codes must be an array in {codes_path}")
    expected_order = [card["card_id"] for card in packet["cards"]]
    observed_order: list[str] = []
    mapping: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Non-object coding row in {codes_path}")
        card_id = row.get("card_id")
        code = row.get("code")
        if not isinstance(card_id, str) or card_id in mapping:
            raise ValueError(f"Missing or duplicate card_id in {codes_path}: {card_id}")
        if code not in ALLOWED_CODES:
            raise ValueError(f"Invalid code for {card_id} in {codes_path}: {code}")
        observed_order.append(card_id)
        mapping[card_id] = code

    if observed_order != expected_order:
        missing = sorted(set(expected_order) - set(observed_order))
        extra = sorted(set(observed_order) - set(expected_order))
        if missing or extra:
            raise ValueError(f"Card set mismatch in {codes_path}; missing={missing}, extra={extra}")
        raise ValueError(f"Card order differs from designated packet in {codes_path}")
    return mapping, value


def copy_exact(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(source) != sha256_file(destination):
            raise FileExistsError(f"Refusing to replace different preserved input: {destination}")
        return
    shutil.copyfile(source, destination)


def load_three_coders(
    packet_dir: Path,
    c1: Path,
    c2: Path,
    c3: Path,
    preserve: bool,
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, Any]], dict[str, Path]]:
    maps: dict[str, dict[str, str]] = {}
    raw: dict[str, dict[str, Any]] = {}
    preserved: dict[str, Path] = {}
    inputs_dir = packet_paths(packet_dir)["inputs"]
    for coder_id, source in [("C1", c1), ("C2", c2), ("C3", c3)]:
        designated = packet_dir / "blinded" / f"CODER_{coder_id}.json"
        mapping, value = validate_codes(source, designated, coder_id)
        maps[coder_id] = mapping
        raw[coder_id] = value
        destination = inputs_dir / f"{coder_id}_CODES.json"
        if preserve:
            copy_exact(source, destination)
        preserved[coder_id] = destination
    return maps, raw, preserved


def disagreements(maps: dict[str, dict[str, str]], master_ids: Iterable[str]) -> list[str]:
    return [
        card_id
        for card_id in master_ids
        if len({maps[coder][card_id] for coder in ("C1", "C2", "C3")}) > 1
    ]


def make_adjudication(args: argparse.Namespace) -> None:
    packet_dir = args.packet_dir.resolve()
    paths = packet_paths(packet_dir)
    generation = load_json(paths["generation"])
    master = load_packet(paths["master"], "MASTER")
    maps, raw, preserved = load_three_coders(
        packet_dir, args.c1, args.c2, args.c3, preserve=True
    )
    if generation.get("packet_id") != master.get("packet_id"):
        raise ValueError("Generation record and master packet IDs differ")

    master_by_id = {card["card_id"]: card for card in master["cards"]}
    discordant = disagreements(maps, master_by_id)
    adjudication_cards = [master_by_id[card_id] for card_id in discordant]
    adjudication_packet = {
        "schema_version": "au-specificity-packet-v1",
        "protocol_id": "B1",
        "packet_id": master["packet_id"],
        "coder_id": "FOUNDER_ADJUDICATOR",
        "card_count": len(adjudication_cards),
        "allowed_codes": list(ALLOWED_CODES),
        "codebook_path": "SPECIFICITY_CODEBOOK.md",
        "adjudication_disclosures": {
            "cards_are_initially_discordant": True,
            "initial_votes_hidden": True,
            "founder_knows_aggregate_primary_result": True,
            "item_level_study_metadata_hidden": True,
        },
        "cards": adjudication_cards,
    }
    write_json(paths["adjudication_packet"], adjudication_packet)

    record = {
        "schema_version": "au-specificity-reconciliation-input-record-v1",
        "protocol_id": "B1",
        "packet_id": master["packet_id"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "unique_cards": len(master["cards"]),
        "unanimous_cards": len(master["cards"]) - len(discordant),
        "discordant_cards": len(discordant),
        "initial_votes_in_adjudication_packet": False,
        "coder_files": {
            coder_id: {
                "path": rel(preserved[coder_id]),
                "sha256": sha256_file(preserved[coder_id]),
                "coder_metadata": raw[coder_id].get("coder_metadata", {}),
            }
            for coder_id in ("C1", "C2", "C3")
        },
        "adjudication_packet": {
            "path": rel(paths["adjudication_packet"]),
            "sha256": sha256_file(paths["adjudication_packet"]),
        },
    }
    write_json(packet_dir / "blinded" / "RECONCILIATION_INPUT_RECORD.json", record)

    print(json.dumps({
        "status": "adjudication_packet_created",
        "packet_id": master["packet_id"],
        "unique_cards": len(master["cards"]),
        "unanimous_cards": len(master["cards"]) - len(discordant),
        "discordant_cards": len(discordant),
        "adjudication_packet": rel(paths["adjudication_packet"]),
    }, indent=2))


def fleiss_kappa(votes: list[list[str]]) -> float | None:
    n_items = len(votes)
    n_raters = 3
    if n_items == 0:
        return None
    category_totals = Counter(code for item in votes for code in item)
    item_agreement: list[float] = []
    for item in votes:
        counts = Counter(item)
        numerator = sum(count * count for count in counts.values()) - n_raters
        item_agreement.append(numerator / (n_raters * (n_raters - 1)))
    p_bar = sum(item_agreement) / n_items
    p_expected = sum(
        (category_totals[code] / (n_items * n_raters)) ** 2
        for code in ALLOWED_CODES
    )
    if p_expected == 1.0:
        return None
    return (p_bar - p_expected) / (1.0 - p_expected)


def agreement_stats(
    maps: dict[str, dict[str, str]],
    card_ids: list[str],
) -> dict[str, Any]:
    vote_rows = [
        [maps[coder_id][card_id] for coder_id in ("C1", "C2", "C3")]
        for card_id in card_ids
    ]
    unanimous = sum(len(set(votes)) == 1 for votes in vote_rows)
    pairs: dict[str, float] = {}
    for left, right in [("C1", "C2"), ("C1", "C3"), ("C2", "C3")]:
        agree = sum(maps[left][card_id] == maps[right][card_id] for card_id in card_ids)
        pairs[f"{left}_{right}"] = agree / len(card_ids) if card_ids else None
    return {
        "unit": "unique_visible_card",
        "cards": len(card_ids),
        "unanimous_cards": unanimous,
        "unanimity_rate": unanimous / len(card_ids) if card_ids else None,
        "pairwise_agreement_rates": pairs,
        "fleiss_kappa_nominal_1_0_U": fleiss_kappa(vote_rows),
        "kappa_note": (
            "Fleiss' kappa is null when undefined because all ratings occupy one category."
        ),
    }


def finalize_blind(args: argparse.Namespace) -> None:
    packet_dir = args.packet_dir.resolve()
    paths = packet_paths(packet_dir)
    master = load_packet(paths["master"], "MASTER")
    maps, raw, preserved = load_three_coders(
        packet_dir, args.c1, args.c2, args.c3, preserve=True
    )
    master_ids = [card["card_id"] for card in master["cards"]]
    discordant = disagreements(maps, master_ids)

    expected_adjudication = load_packet(
        paths["adjudication_packet"], "FOUNDER_ADJUDICATOR"
    )
    if expected_adjudication.get("packet_id") != master.get("packet_id"):
        raise ValueError("Adjudication packet has the wrong packet_id")
    adjudication_ids = [card["card_id"] for card in expected_adjudication["cards"]]
    if adjudication_ids != discordant:
        raise ValueError("Adjudication packet does not match current discordant cards")

    if discordant:
        if args.adjudication is None:
            raise ValueError("Founder adjudication file is required for discordant cards")
        adjudication_map, adjudication_raw = validate_codes(
            args.adjudication,
            paths["adjudication_packet"],
            "FOUNDER_ADJUDICATOR",
        )
        preserved_adjudication = paths["inputs"] / "FOUNDER_ADJUDICATION.json"
        copy_exact(args.adjudication, preserved_adjudication)
    else:
        adjudication_map = {}
        adjudication_raw = {"coder_metadata": {}}
        preserved_adjudication = None

    final_rows: list[dict[str, Any]] = []
    final_counts: Counter[str] = Counter()
    for card_id in master_ids:
        votes = {coder: maps[coder][card_id] for coder in ("C1", "C2", "C3")}
        if len(set(votes.values())) == 1:
            final_code = votes["C1"]
            route = "unanimous"
        else:
            final_code = adjudication_map[card_id]
            route = "founder_adjudication"
        final_counts[final_code] += 1
        final_rows.append(
            {
                "card_id": card_id,
                "initial_codes": votes,
                "resolution": route,
                "final_code": final_code,
            }
        )

    input_files = {
        rel(preserved[coder]): sha256_file(preserved[coder])
        for coder in ("C1", "C2", "C3")
    }
    input_files[rel(paths["adjudication_packet"])] = sha256_file(
        paths["adjudication_packet"]
    )
    input_files[rel(paths["master"])] = sha256_file(paths["master"])
    if preserved_adjudication is not None:
        input_files[rel(preserved_adjudication)] = sha256_file(preserved_adjudication)

    final = {
        "schema_version": "au-specificity-blind-final-v1",
        "protocol_id": "B1",
        "packet_id": master["packet_id"],
        "finalized_at_utc": datetime.now(timezone.utc).isoformat(),
        "still_blinded_to_item_level_metadata": True,
        "founder_adjudicator_disclosure": {
            "knew_aggregate_primary_result": True,
            "knew_presented_cards_were_discordant": True,
            "saw_initial_votes": False,
            "saw_model_gap_provider_replicate_metadata": False,
        },
        "coder_metadata": {
            coder: raw[coder].get("coder_metadata", {})
            for coder in ("C1", "C2", "C3")
        },
        "founder_adjudicator_metadata": adjudication_raw.get("coder_metadata", {}),
        "agreement": agreement_stats(maps, master_ids),
        "adjudication": {
            "cards": len(discordant),
            "rate": len(discordant) / len(master_ids) if master_ids else None,
        },
        "final_card_code_counts": {
            code: final_counts.get(code, 0) for code in ALLOWED_CODES
        },
        "input_files_sha256": dict(sorted(input_files.items())),
        "cards": final_rows,
        "unblinding_status": "not_performed",
        "required_next_checkpoint": (
            "Commit this file and its recorded coding inputs in a founder-signed "
            "commit before running unblind-report."
        ),
    }
    write_json(paths["blind_final"], final)

    print(json.dumps({
        "status": "blind_coding_finalized",
        "packet_id": master["packet_id"],
        "blind_final": rel(paths["blind_final"]),
        "unique_cards": len(master_ids),
        "unanimous_cards": len(master_ids) - len(discordant),
        "adjudicated_cards": len(discordant),
        "final_card_code_counts": final["final_card_code_counts"],
        "next": "Create and verify a founder-signed coding-freeze commit before unblinding.",
    }, indent=2))


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


def verify_coding_freeze(ref: str, paths: dict[str, Path], blind: dict[str, Any]) -> str:
    resolved = git("rev-parse", "--verify", f"{ref}^{{commit}}")
    if resolved.returncode != 0:
        raise ValueError(f"Cannot resolve coding freeze commit {ref}")
    commit = resolved.stdout.strip()
    verified = git("verify-commit", commit)
    if verified.returncode != 0:
        detail = (verified.stderr or verified.stdout).strip()
        raise ValueError(f"Coding-freeze signature verification failed: {detail}")
    ancestor = git("merge-base", "--is-ancestor", commit, "HEAD")
    if ancestor.returncode != 0:
        raise ValueError("Coding-freeze commit is not an ancestor of HEAD")

    required = dict(blind.get("input_files_sha256", {}))
    required[rel(paths["blind_final"])] = sha256_file(paths["blind_final"])
    for path_text, expected_hash in sorted(required.items()):
        path = ROOT / path_text
        if not path.is_file() or sha256_file(path) != expected_hash:
            raise ValueError(f"Working blinded file mismatch: {path_text}")
        if not committed_blob_matches_worktree(commit, path_text):
            raise ValueError(
                f"Working blinded file does not match the signed commit after Git filters: {path_text}"
            )
    return commit


def count_codes(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row["final_code"]) for row in rows)
    return {code: counts.get(code, 0) for code in ALLOWED_CODES}


def unweighted_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = count_codes(rows)
    codable = counts["1"] + counts["0"]
    total = sum(counts.values())
    return {
        "sampled_observations": total,
        "counts": counts,
        "codable_observations": codable,
        "proportion_specific_among_codable": counts["1"] / codable if codable else None,
        "proportion_uncertain": counts["U"] / total if total else None,
    }


def weighted_summary(
    rows: list[dict[str, Any]],
    eligible_counts: dict[str, int],
) -> dict[str, Any]:
    weighted = {code: 0.0 for code in ALLOWED_CODES}
    for row in rows:
        stratum = f"{row['model_key']}::{row['gap_structure']}"
        weight = eligible_counts[stratum] / 15.0
        weighted[row["final_code"]] += weight
    codable = weighted["1"] + weighted["0"]
    total = sum(weighted.values())
    return {
        "design_weight": "eligible_N_in_model_gap_cell / 15",
        "weighted_estimated_counts": weighted,
        "weighted_codable_denominator": codable,
        "weighted_proportion_specific_among_codable": (
            weighted["1"] / codable if codable else None
        ),
        "weighted_proportion_uncertain": weighted["U"] / total if total else None,
    }


def unblind_report(args: argparse.Namespace) -> None:
    packet_dir = args.packet_dir.resolve()
    paths = packet_paths(packet_dir)
    blind = load_json(paths["blind_final"])
    if blind.get("schema_version") != "au-specificity-blind-final-v1":
        raise ValueError("Unexpected blind-final schema")
    coding_commit = verify_coding_freeze(args.coding_freeze_commit, paths, blind)

    generation = load_json(paths["generation"])
    key = load_json(paths["key"])
    if key.get("schema_version") != "au-specificity-unblinding-key-v1":
        raise ValueError("Unexpected unblinding-key schema")
    if key.get("packet_id") != blind.get("packet_id"):
        raise ValueError("Blind-final and unblinding-key packet IDs differ")
    if generation.get("packet_id") != blind.get("packet_id"):
        raise ValueError("Generation record and blind-final packet IDs differ")
    expected_key_hash = generation.get("files_sha256", {}).get(rel(paths["key"]))
    if not expected_key_hash or sha256_file(paths["key"]) != expected_key_hash:
        raise ValueError("Unblinding key hash differs from the packet-generation record")

    final_by_card = {
        row["card_id"]: row["final_code"] for row in blind.get("cards", [])
    }
    observations: list[dict[str, Any]] = []
    for hidden in key.get("observations", []):
        card_id = hidden.get("card_id")
        if card_id not in final_by_card:
            raise ValueError(f"No final code for sampled card {card_id}")
        observations.append({**hidden, "final_code": final_by_card[card_id]})
    if len(observations) != 180:
        raise ValueError(f"Expected 180 unblinded observations, found {len(observations)}")

    eligible_counts = key.get("eligible_counts_by_model_gap", {})
    by_cell: list[dict[str, Any]] = []
    for model in ("haiku", "luna", "sonnet", "terra"):
        for gap in ("closed", "seamed", "explicit_gap"):
            cell_rows = [
                row for row in observations
                if row["model_key"] == model and row["gap_structure"] == gap
            ]
            cell = {
                "model_key": model,
                "gap_structure": gap,
                "eligible_population": eligible_counts[f"{model}::{gap}"],
                **unweighted_summary(cell_rows),
            }
            by_cell.append(cell)

    by_model: list[dict[str, Any]] = []
    for model in ("haiku", "luna", "sonnet", "terra"):
        rows = [row for row in observations if row["model_key"] == model]
        by_model.append({
            "model_key": model,
            "unweighted_sample": unweighted_summary(rows),
            "design_weighted_population_estimate": weighted_summary(rows, eligible_counts),
        })

    by_gap: list[dict[str, Any]] = []
    for gap in ("closed", "seamed", "explicit_gap"):
        rows = [row for row in observations if row["gap_structure"] == gap]
        by_gap.append({
            "gap_structure": gap,
            "unweighted_sample": unweighted_summary(rows),
            "design_weighted_population_estimate": weighted_summary(rows, eligible_counts),
        })

    result = {
        "schema_version": "au-specificity-results-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "B1",
        "packet_id": blind["packet_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "coding_freeze_commit": coding_commit,
        "coding_freeze_signature_verified": True,
        "blinded_final_sha256": sha256_file(paths["blind_final"]),
        "unblinding_key_sha256": sha256_file(paths["key"]),
        "sampled_observations": len(observations),
        "unique_visible_cards": len(final_by_card),
        "agreement": blind.get("agreement"),
        "adjudication": blind.get("adjudication"),
        "by_model_gap": by_cell,
        "by_model": by_model,
        "by_gap": by_gap,
        "overall": {
            "unweighted_sample": unweighted_summary(observations),
            "design_weighted_population_estimate": weighted_summary(
                observations, eligible_counts
            ),
        },
        "observations": observations,
        "interpretation": (
            "Descriptive specificity coding for the B1 stratified sample of eligible "
            "emitted questions. No inferential specificity test is performed."
        ),
    }
    write_json(paths["results"], result)

    print(json.dumps({
        "status": "specificity_unblinded_and_reported",
        "packet_id": blind["packet_id"],
        "results": rel(paths["results"]),
        "sampled_observations": len(observations),
        "unique_visible_cards": len(final_by_card),
    }, indent=2))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)

    adjudicate = sub.add_parser("make-adjudication")
    adjudicate.add_argument("--packet-dir", type=Path, required=True)
    adjudicate.add_argument("--c1", type=Path, required=True)
    adjudicate.add_argument("--c2", type=Path, required=True)
    adjudicate.add_argument("--c3", type=Path, required=True)
    adjudicate.set_defaults(func=make_adjudication)

    finalize = sub.add_parser("finalize-blind")
    finalize.add_argument("--packet-dir", type=Path, required=True)
    finalize.add_argument("--c1", type=Path, required=True)
    finalize.add_argument("--c2", type=Path, required=True)
    finalize.add_argument("--c3", type=Path, required=True)
    finalize.add_argument("--adjudication", type=Path)
    finalize.set_defaults(func=finalize_blind)

    unblind = sub.add_parser("unblind-report")
    unblind.add_argument("--packet-dir", type=Path, required=True)
    unblind.add_argument("--coding-freeze-commit", required=True)
    unblind.set_defaults(func=unblind_report)
    return root


def main() -> int:
    args = parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
