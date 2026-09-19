#!/usr/bin/env python3
"""Build the technical pre-packet freeze record for Specificity Protocol B1."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "prereg" / "API_PILOT_0.1_PREPACKET_FREEZE_RECORD.json"
PRIMARY = ROOT / "api-study" / "results" / "PRIMARY_A1.json"
PRIMARY_RECORD = ROOT / "api-study" / "results" / "PRIMARY_A1_RUN_RECORD.json"
GENERATOR = ROOT / "api-study" / "specificity" / "generate_packet.py"
GENERATED_DIR = ROOT / "api-study" / "specificity" / "generated"

FROZEN_PATHS = [
    "prereg/API_PILOT_0.1_PREREGISTRATION.md",
    "prereg/API_PILOT_0.1_FREEZE_RECORD.json",
    "prereg/API_PILOT_0.1_AMENDMENT_A1.md",
    "prereg/API_PILOT_0.1_SPECIFICITY_PROTOCOL_B1.md",
    "api-study/config.yaml",
    "api-study/passages.json",
    "api-study/SPECIFICITY_CODEBOOK.md",
    "api-study/analyze_confirmatory.py",
    "api-study/analyze_confirmatory_a1.py",
    "api-study/requirements-analysis.txt",
    "api-study/run_primary_a1_record.py",
    "api-study/results/PRIMARY_A1.json",
    "api-study/results/PRIMARY_A1_RUN_RECORD.json",
    "api-study/specificity/generate_packet.py",
    "api-study/specificity/coding_pipeline.py",
    "api-study/specificity/coder.html",
    "api-study/specificity/CODER_INSTRUCTIONS.md",
    "api-study/specificity/README.md",
    "api-study/data/raw/20260918T200715Z-luna-667cc52d.manifest.json",
    "api-study/data/raw/20260918T200715Z-luna-667cc52d.jsonl",
    "api-study/data/raw/20260918T202517Z-terra-a31f0c2b.manifest.json",
    "api-study/data/raw/20260918T202517Z-terra-a31f0c2b.jsonl",
    "api-study/data/raw/20260918T210718Z-haiku-c13f68a4.manifest.json",
    "api-study/data/raw/20260918T210718Z-haiku-c13f68a4.jsonl",
    "api-study/data/raw/20260918T225249Z-sonnet-2059332f.manifest.json",
    "api-study/data/raw/20260918T225249Z-sonnet-2059332f.jsonl",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    path.write_bytes(payload)


def git_output(*args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip()


def assert_packet_absent() -> None:
    if GENERATED_DIR.exists() and any(path.is_file() for path in GENERATED_DIR.rglob("*")):
        raise ValueError(
            "A generated specificity packet already exists. B1 must be frozen before packet generation."
        )


def validate_primary() -> tuple[dict[str, Any], dict[str, Any]]:
    if not PRIMARY.is_file() or not PRIMARY_RECORD.is_file():
        raise FileNotFoundError(
            "Run `python .\\api-study\\run_primary_a1_record.py` before building the freeze record."
        )
    primary = load_json(PRIMARY)
    run_record = load_json(PRIMARY_RECORD)
    if primary.get("analysis_version") != "api-pilot-0.1-amendment-a1":
        raise ValueError("PRIMARY_A1.json has an unexpected analysis_version")
    if primary.get("validation", {}).get("attempted_records") != 3600:
        raise ValueError("PRIMARY_A1.json does not validate 3,600 attempted records")
    if run_record.get("artifact_sha256") != sha256(PRIMARY):
        raise ValueError("PRIMARY_A1_RUN_RECORD.json does not match PRIMARY_A1.json")

    expected = {
        (
            load_json(ROOT / path)["run_id"],
            load_json(ROOT / path)["records_sha256"],
        )
        for path in FROZEN_PATHS
        if path.endswith(".manifest.json")
    }
    observed = {
        (row.get("run_id"), row.get("records_sha256"))
        for row in primary.get("accepted_runs", [])
    }
    if observed != expected:
        raise ValueError("PRIMARY_A1.json accepted run set does not match B1 inputs")
    return primary, run_record


def run_preflight() -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(GENERATOR), "--preflight-only"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Packet preflight failed:\n" + (completed.stderr or completed.stdout)
        )
    value = json.loads(completed.stdout)
    if value.get("sampled_observations") != 180:
        raise ValueError("B1 preflight did not produce 180 sampled observations")
    if value.get("unique_visible_cards") != 169:
        raise ValueError("B1 preflight did not produce 169 unique visible cards")
    return value


def main() -> int:
    assert_packet_absent()
    primary, run_record = validate_primary()
    preflight = run_preflight()

    frozen_hashes: dict[str, str] = {}
    for path_text in FROZEN_PATHS:
        path = ROOT / path_text
        if not path.is_file():
            raise FileNotFoundError(path)
        frozen_hashes[path_text] = sha256(path)

    accepted_runs = []
    for path_text in sorted(
        path for path in FROZEN_PATHS if path.endswith(".manifest.json")
    ):
        path = ROOT / path_text
        manifest = load_json(path)
        accepted_runs.append({
            "model_key": manifest["model_key"],
            "run_id": manifest["run_id"],
            "manifest_path": path_text,
            "manifest_sha256": sha256(path),
            "records_sha256": manifest["records_sha256"],
        })

    status_lines = (git_output("status", "--porcelain=v1") or "").splitlines()
    record = {
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "B1",
        "status": (
            "candidate; adopted only by the founder-signed commit containing this record"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "packet_status": "not_generated",
        "semantic_coding_status": "not_started",
        "item_level_unblinding_status": "not_performed",
        "base_git_state": {
            "head_before_freeze_commit": git_output("rev-parse", "HEAD"),
            "head_signature_status": git_output("log", "-1", "--format=%G?"),
            "worktree_dirty_while_building_candidate": bool(status_lines),
            "porcelain_entry_count": len(status_lines),
            "note": (
                "The signed commit that adds this record and the frozen files is the adoption act; "
                "the pre-commit HEAD is recorded only as provenance."
            ),
        },
        "knowledge_disclosure": {
            "founder_knew_aggregate_primary_result": True,
            "preparing_assistant_knew_aggregate_primary_result": True,
            "semantic_item_codes_assigned_before_freeze": False,
            "mechanical_workload_sizing_performed_before_freeze": True,
            "preparing_assistant_raw_item_texts_displayed_for_schema_check": 1,
            "raw_item_text_used_to_choose_sampling_or_coding_rules": False,
        },
        "primary_analysis_artifact": "api-study/results/PRIMARY_A1.json",
        "primary_analysis_artifact_sha256": sha256(PRIMARY),
        "primary_analysis_run_record": "api-study/results/PRIMARY_A1_RUN_RECORD.json",
        "primary_analysis_run_record_sha256": sha256(PRIMARY_RECORD),
        "primary_analysis_summary": {
            "attempted_records": primary["validation"]["attempted_records"],
            "successful_records": primary["validation"]["successful_records"],
            "primary_format_valid_records": primary["validation"]["primary_format_valid_records"],
            "h1_decision_status": primary["primary_outcome"]["h1_decision_status"],
            "h1_supported": primary["primary_outcome"]["h1_supported_governing"],
            "h1_governing_estimator": primary["primary_outcome"]["governing_estimators"]["h1"],
            "h2_decision_status": primary["primary_outcome"]["h2_decision_status"],
            "h2_p": primary["primary_outcome"]["h2_p_governing"],
            "h2_governing_estimator": primary["primary_outcome"]["governing_estimators"]["h2"],
        },
        "primary_execution_adapter_used": run_record.get("execution", {}).get(
            "portability_manifest_adapter_used"
        ),
        "accepted_runs": sorted(accepted_runs, key=lambda row: row["model_key"]),
        "mechanical_preflight": preflight,
        "frozen_files_sha256": dict(sorted(frozen_hashes.items())),
        "adoption_instruction": (
            "Create one founder-signed Git commit containing this record and every frozen file, "
            "then verify it with git verify-commit before generating the packet."
        ),
    }
    write_json(OUTPUT, record)

    print(json.dumps({
        "status": "prepacket_freeze_candidate_built",
        "output": OUTPUT.relative_to(ROOT).as_posix(),
        "output_sha256": sha256(OUTPUT),
        "packet_status": "not_generated",
        "sampled_observations": preflight["sampled_observations"],
        "unique_visible_cards": preflight["unique_visible_cards"],
        "next": (
            "Review, stage only the intended study artifacts, founder-sign the commit, "
            "and run git verify-commit HEAD."
        ),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
