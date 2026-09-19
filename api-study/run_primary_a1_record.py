#!/usr/bin/env python3
"""Run adopted A1 analysis and preserve a reproducibility record.

This wrapper does not alter the A1 calculations. On platforms that cannot parse
the Windows locator stored in a manifest, it creates a temporary manifest copy
whose only change is the records_file locator. The original manifest and raw
hashes remain the validated inputs and are recorded explicitly.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "api-study" / "analyze_confirmatory_a1.py"
FROZEN_ANALYZER = ROOT / "api-study" / "analyze_confirmatory.py"
FREEZE_RECORD = ROOT / "prereg" / "API_PILOT_0.1_FREEZE_RECORD.json"
OUTPUT = ROOT / "api-study" / "results" / "PRIMARY_A1.json"
RUN_RECORD = ROOT / "api-study" / "results" / "PRIMARY_A1_RUN_RECORD.json"

MANIFESTS = [
    ROOT / "api-study" / "data" / "raw" / "20260918T200715Z-luna-667cc52d.manifest.json",
    ROOT / "api-study" / "data" / "raw" / "20260918T202517Z-terra-a31f0c2b.manifest.json",
    ROOT / "api-study" / "data" / "raw" / "20260918T210718Z-haiku-c13f68a4.manifest.json",
    ROOT / "api-study" / "data" / "raw" / "20260918T225249Z-sonnet-2059332f.manifest.json",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
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


def resolve_records(manifest_path: Path, locator: str) -> Path:
    direct = Path(locator)
    if direct.exists():
        return direct.resolve()

    native_sibling = manifest_path.parent / direct.name
    if native_sibling.exists():
        return native_sibling.resolve()

    windows_sibling = manifest_path.parent / PureWindowsPath(locator).name
    if windows_sibling.exists():
        return windows_sibling.resolve()

    raise FileNotFoundError(f"Cannot resolve records file from {manifest_path}: {locator}")


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


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def main() -> int:
    for required in [ANALYZER, FROZEN_ANALYZER, FREEZE_RECORD, *MANIFESTS]:
        if not required.is_file():
            raise FileNotFoundError(required)

    canonical_inputs: list[dict[str, Any]] = []
    adapter_used = False

    with tempfile.TemporaryDirectory(prefix="au-primary-a1-") as temp_name:
        temp_dir = Path(temp_name)
        invocation_manifests: list[Path] = []

        for manifest_path in MANIFESTS:
            manifest = load_json(manifest_path)
            records_path = resolve_records(manifest_path, str(manifest.get("records_file", "")))
            observed_records_hash = sha256(records_path)
            expected_records_hash = str(manifest.get("records_sha256", ""))
            if observed_records_hash != expected_records_hash:
                raise ValueError(
                    f"Raw hash mismatch for {records_path}: "
                    f"{observed_records_hash} != {expected_records_hash}"
                )

            canonical_inputs.append(
                {
                    "manifest_path": rel(manifest_path),
                    "manifest_sha256": sha256(manifest_path),
                    "model_key": manifest.get("model_key"),
                    "run_id": manifest.get("run_id"),
                    "records_path": rel(records_path),
                    "records_sha256": observed_records_hash,
                }
            )

            original_locator = str(manifest.get("records_file", ""))
            frozen_native_name = Path(original_locator).name
            frozen_resolves = Path(original_locator).exists() or (
                manifest_path.parent / frozen_native_name
            ).exists()

            if frozen_resolves:
                invocation_manifests.append(manifest_path)
            else:
                adapter_used = True
                adapted = dict(manifest)
                adapted["records_file"] = str(records_path)
                adapted_path = temp_dir / manifest_path.name
                write_json(adapted_path, adapted)
                invocation_manifests.append(adapted_path)

        command = [
            sys.executable,
            str(ANALYZER),
            *(str(path) for path in invocation_manifests),
            "--expected-hashes",
            str(FREEZE_RECORD),
            "--output",
            str(OUTPUT),
        ]

        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)

    result = load_json(OUTPUT)
    if result.get("analysis_version") != "api-pilot-0.1-amendment-a1":
        raise ValueError("Unexpected analysis_version in PRIMARY_A1.json")
    if result.get("validation", {}).get("attempted_records") != 3600:
        raise ValueError("PRIMARY_A1.json does not contain 3,600 attempted records")

    observed_runs = {
        (row.get("run_id"), row.get("records_sha256"))
        for row in result.get("accepted_runs", [])
    }
    expected_runs = {
        (row["run_id"], row["records_sha256"])
        for row in canonical_inputs
    }
    if observed_runs != expected_runs:
        raise ValueError("PRIMARY_A1 accepted run set differs from canonical inputs")

    status_lines = (git_output("status", "--porcelain=v1") or "").splitlines()
    record = {
        "study": "Attainable Unknowns API Pilot 0.1",
        "artifact": rel(OUTPUT),
        "artifact_sha256": sha256(OUTPUT),
        "analysis_version": result["analysis_version"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git": {
            "head": git_output("rev-parse", "HEAD"),
            "worktree_dirty": bool(status_lines),
            "porcelain_entry_count": len(status_lines),
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": {
                name: package_version(name)
                for name in ["numpy", "pandas", "scipy", "statsmodels"]
            },
        },
        "implementation": {
            "a1_analyzer_path": rel(ANALYZER),
            "a1_analyzer_sha256": sha256(ANALYZER),
            "frozen_analyzer_path": rel(FROZEN_ANALYZER),
            "frozen_analyzer_sha256": sha256(FROZEN_ANALYZER),
            "freeze_record_path": rel(FREEZE_RECORD),
            "freeze_record_sha256": sha256(FREEZE_RECORD),
        },
        "canonical_inputs": sorted(canonical_inputs, key=lambda row: str(row["model_key"])),
        "execution": {
            "portability_manifest_adapter_used": adapter_used,
            "adapter_scope": (
                "records_file locator only; temporary adapters were not retained"
                if adapter_used
                else None
            ),
            "command_template": (
                "python api-study/analyze_confirmatory_a1.py <four accepted manifests> "
                "--expected-hashes prereg/API_PILOT_0.1_FREEZE_RECORD.json "
                "--output api-study/results/PRIMARY_A1.json"
            ),
        },
        "summary": {
            "attempted_records": result["validation"]["attempted_records"],
            "successful_records": result["validation"]["successful_records"],
            "primary_format_valid_records": result["validation"]["primary_format_valid_records"],
            "format_invalid_successes": result["validation"]["format_invalid_successes"],
            "h1_decision_status": result["primary_outcome"]["h1_decision_status"],
            "h1_supported": result["primary_outcome"]["h1_supported_governing"],
            "h1_governing_estimator": result["primary_outcome"]["governing_estimators"]["h1"],
            "h2_decision_status": result["primary_outcome"]["h2_decision_status"],
            "h2_p": result["primary_outcome"]["h2_p_governing"],
            "h2_governing_estimator": result["primary_outcome"]["governing_estimators"]["h2"],
        },
        "note": (
            "The A1 analyzer produced the result artifact. This wrapper adds only "
            "input, environment, invocation, and artifact-hash provenance."
        ),
    }
    write_json(RUN_RECORD, record)

    print(json.dumps({
        "status": "complete",
        "result": rel(OUTPUT),
        "result_sha256": sha256(OUTPUT),
        "run_record": rel(RUN_RECORD),
        "run_record_sha256": sha256(RUN_RECORD),
        "portability_manifest_adapter_used": adapter_used,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
