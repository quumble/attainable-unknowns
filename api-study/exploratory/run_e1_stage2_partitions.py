#!/usr/bin/env python3
"""Run E1/E1A Stage 2 blinded semantic partitions with canaries and robust resume."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
E1_DIR = ROOT / "api-study" / "exploratory"

BUNDLE_ID = "AU-E1-S2-b021f4b9caf73dad"
BUNDLE_DIR = E1_DIR / "e1" / "stage2" / "generated" / BUNDLE_ID
BLINDED_DIR = BUNDLE_DIR / "blinded"
PACKET_INDEX = BLINDED_DIR / "STAGE2_PACKET_INDEX.json"
INSTRUCTIONS = BLINDED_DIR / "STAGE2_PARTITION_INSTRUCTIONS.md"

EXECUTION_PROTOCOL = E1_DIR / "E1_STAGE2_EXECUTION_PROTOCOL_P1.md"
EXECUTION_CORRECTION = E1_DIR / "E1_STAGE2_EXECUTION_CORRECTION_P1D1.md"
EXECUTION_CORRECTION_P1D2 = E1_DIR / "E1_STAGE2_EXECUTION_CORRECTION_P1D2.md"
OUTPUT_ENCODING_P1D2 = E1_DIR / "E1_STAGE2_OUTPUT_ENCODING_P1D2.md"
EXECUTION_CORRECTION_P1D3 = E1_DIR / "E1_STAGE2_EXECUTION_CORRECTION_P1D3.md"
OUTPUT_ENCODING_P1D3 = E1_DIR / "E1_STAGE2_OUTPUT_ENCODING_P1D3.md"
OUTPUT_DIR = E1_DIR / "e1" / "stage2" / "partitions" / BUNDLE_ID / "P1D3"
ATTEMPTS_PATH = OUTPUT_DIR / "ATTEMPTS.jsonl"
PARTITIONS_PATH = OUTPUT_DIR / "PARTITIONS.jsonl"
MANIFEST_PATH = OUTPUT_DIR / "RUN_MANIFEST.json"
INFLIGHT_PATH = OUTPUT_DIR / "INFLIGHT.json"

BUNDLE_COMMIT = "435c01cb5971fd6b0487eaebfc7a8a5803311c06"
PREDECESSOR_EXECUTION_COMMIT = "3c1dd0529fe8581f56fc290de9aed344a77f091a"
EXPECTED_PACKETS = 24
EXPECTED_TASKS = 72
MAX_ATTEMPTS_PER_TASK = 3
MAX_EXHAUSTED_TASKS_BEFORE_MODEL_BREAK = 2
TRANSIENT_BACKOFF_SECONDS = (10, 30)
PREDECESSOR_VARIANT = "P1D2"
EXECUTION_VARIANT = "P1D3"
OUTPUT_ENCODING = "fixed_width_triplet_string_v1"
CODE_WIDTH = 3
MAX_OUTPUT_TOKENS_BY_MODEL = {
    "sol": 16000,
    "opus": 16000,
    "terra": 16000,
    "sonnet": 64000,
}

MODEL_CONFIGS: dict[str, dict[str, Any]] = {
    "sol": {
        "provider": "openai",
        "model": "gpt-5.6-sol",
        "api_key_env": "OPENAI_API_KEY",
        "reasoning_effort": "low",
        "input_per_million": 4.00,
        "output_per_million": 20.00,
        "stop_limit_usd": 10.00,
    },
    "opus": {
        "provider": "anthropic",
        "model": "claude-opus-5",
        "api_key_env": "ANTHROPIC_API_KEY",
        "thinking": {"type": "adaptive"},
        "effort": "low",
        "input_per_million": 5.00,
        "output_per_million": 25.00,
        "stop_limit_usd": 15.00,
    },
    "terra": {
        "provider": "openai",
        "model": "gpt-5.6-terra",
        "api_key_env": "OPENAI_API_KEY",
        "reasoning_effort": "low",
        "input_per_million": 2.00,
        "output_per_million": 12.00,
        "stop_limit_usd": 5.00,
    },
    "sonnet": {
        "provider": "anthropic",
        "model": "claude-sonnet-5",
        "api_key_env": "ANTHROPIC_API_KEY",
        "thinking": {"type": "adaptive"},
        "effort": "low",
        "input_per_million": 2.00,
        "output_per_million": 10.00,
        "stop_limit_usd": 5.00,
    },
}

CANARY_TASK_IDS = {
    "P1-AU-E1-S2-R01-T04",
    "P2-AU-E1-S2-R02-T04",
    "P3-AU-E1-S2-R01-T09",
    "P3-AU-E1-S2-R02-T04",
    "P2-AU-E1-S2-R02-T08",
    "P3-AU-E1-S2-R01-T05",
    "P3-AU-E1-S2-R02-T09",
}

SYNTHETIC_PACKET = {
    "schema_version": "au-e1-stage2-topic-packet-v1",
    "study": "synthetic runner fixture",
    "protocol_id": "synthetic",
    "amendment_id": "synthetic",
    "stage": "synthetic_stage2_partition",
    "packet_id": "SYNTHETIC-AU-E1-S2-230",
    "representation_set_id": "SYNTHETIC-R01",
    "topic_packet_id": "SYNTHETIC-T00",
    "target_count": 230,
    "targets": [
        {
            "target_id": f"T{i:03d}",
            "canonical_target": (
                f"Synthetic information request in category {((i - 1) % 7) + 1}, item {i}. "
                f"Items sharing a category refer to the same synthetic answer-space."
            ),
        }
        for i in range(1, 231)
    ],
}



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


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n", buffering=1) as handle:
        handle.write(canonical_json(value) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
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


def verify_bundle() -> dict[str, Any]:
    commit = verify_signed_commit(BUNDLE_COMMIT, "Stage 2 bundle anchor")
    if commit != BUNDLE_COMMIT:
        raise ValueError("Resolved bundle commit differs from frozen Stage 2 SHA")
    for path in (PACKET_INDEX, INSTRUCTIONS):
        if not path.is_file():
            raise FileNotFoundError(path)
        if not committed_blob_matches_worktree(commit, path):
            raise ValueError(f"Working Stage 2 input differs from bundle commit: {rel(path)}")

    index = load_json(PACKET_INDEX)
    if index.get("bundle_id") != BUNDLE_ID or index.get("packet_count") != EXPECTED_PACKETS:
        raise ValueError("Stage 2 packet index identity/count mismatch")

    for row in index["packets"]:
        packet_path = ROOT / row["path"]
        if not packet_path.is_file():
            raise FileNotFoundError(packet_path)
        if sha256_file(packet_path) != row["sha256"]:
            raise ValueError(f"Packet SHA-256 mismatch: {row['packet_id']}")
        if not committed_blob_matches_worktree(commit, packet_path):
            raise ValueError(f"Packet differs from signed bundle: {row['packet_id']}")

    if sha256_file(INSTRUCTIONS) != index["instructions_sha256"]:
        raise ValueError("Stage 2 instruction hash mismatch")

    return index


def verify_implementation(ref: str) -> str:
    commit = verify_signed_commit(ref, "Stage 2 execution implementation")
    predecessor = verify_signed_commit(
        PREDECESSOR_EXECUTION_COMMIT,
        "Incomplete P1/P1D1 execution anchor",
    )
    if predecessor != PREDECESSOR_EXECUTION_COMMIT:
        raise ValueError("Resolved predecessor execution commit differs from frozen SHA")
    if git("merge-base", "--is-ancestor", BUNDLE_COMMIT, commit).returncode != 0:
        raise ValueError("Stage 2 bundle anchor is not an ancestor of implementation")
    if git("merge-base", "--is-ancestor", PREDECESSOR_EXECUTION_COMMIT, commit).returncode != 0:
        raise ValueError("P1D2 incomplete execution anchor is not an ancestor of implementation")
    for path in (
        Path(__file__).resolve(),
        EXECUTION_PROTOCOL,
        EXECUTION_CORRECTION,
        EXECUTION_CORRECTION_P1D2,
        OUTPUT_ENCODING_P1D2,
        EXECUTION_CORRECTION_P1D3,
        OUTPUT_ENCODING_P1D3,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
        if not committed_blob_matches_worktree(commit, path):
            raise ValueError(
                f"Working execution file differs from signed implementation: {rel(path)}"
            )
    return commit


def load_env_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def packet_topic_number(packet_id: str) -> int:
    match = re.search(r"-T(\d+)$", packet_id)
    if not match:
        raise ValueError(f"Cannot parse topic number from packet_id: {packet_id}")
    return int(match.group(1))


def build_tasks(index: dict[str, Any]) -> list[dict[str, Any]]:
    packets = {row["packet_id"]: row for row in index["packets"]}
    tasks: list[dict[str, Any]] = []
    for packet_id, row in packets.items():
        topic_number = packet_topic_number(packet_id)
        assignments = [
            ("P1", "sol"),
            ("P2", "opus"),
            ("P3", "terra" if topic_number % 2 == 1 else "sonnet"),
        ]
        for replicate, model_key in assignments:
            tasks.append(
                {
                    "task_id": f"{replicate}-{packet_id}",
                    "partition_replicate": replicate,
                    "packet_id": packet_id,
                    "packet_path": row["path"],
                    "packet_sha256": row["sha256"],
                    "target_count": int(row["target_count"]),
                    "representation_set_id": row["representation_set_id"],
                    "topic_packet_id": row["topic_packet_id"],
                    "model_key": model_key,
                }
            )
    if len(tasks) != EXPECTED_TASKS:
        raise ValueError(f"Expected {EXPECTED_TASKS} Stage 2 tasks, found {len(tasks)}")
    if {t["task_id"] for t in tasks if t["task_id"] in CANARY_TASK_IDS} != CANARY_TASK_IDS:
        raise ValueError("Canary roster mismatch")
    return sorted(tasks, key=lambda x: x["task_id"])


def load_packet(task: dict[str, Any]) -> dict[str, Any]:
    packet = load_json(ROOT / task["packet_path"])
    if packet.get("packet_id") != task["packet_id"]:
        raise ValueError("Task/packet identity mismatch")
    targets = packet.get("targets")
    if not isinstance(targets, list) or len(targets) != task["target_count"]:
        raise ValueError("Packet target count mismatch")
    seen: set[str] = set()
    for target in targets:
        if set(target) != {"canonical_target", "target_id"}:
            raise ValueError("Unexpected target fields")
        target_id = target["target_id"]
        if not isinstance(target_id, str) or not target_id:
            raise ValueError("Invalid target_id")
        if target_id in seen:
            raise ValueError(f"Duplicate target_id {target_id}")
        seen.add(target_id)
        if not isinstance(target["canonical_target"], str) or not target["canonical_target"].strip():
            raise ValueError(f"Empty canonical target for {target_id}")
    return packet


def output_schema(packet: dict[str, Any], provider: str) -> dict[str, Any]:
    del provider  # The P1D3 schema is deliberately identical across providers.
    target_count = int(packet["target_count"])
    digit_count = target_count * CODE_WIDTH
    return {
        "type": "object",
        "properties": {
            "packet_id": {"type": "string"},
            "assignment_code": {
                "type": "string",
                "pattern": rf"^[0-9]{{{digit_count}}}$",
            },
        },
        "required": ["packet_id", "assignment_code"],
        "additionalProperties": False,
    }


def validate_partition(text: str, packet: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Response is not valid JSON: {exc}") from exc

    if not isinstance(value, dict) or set(value) != {"packet_id", "assignment_code"}:
        raise ValueError("Output must contain exactly packet_id and assignment_code")
    if value["packet_id"] != packet["packet_id"]:
        raise ValueError("packet_id mismatch")

    assignment_code = value["assignment_code"]
    input_ids = [target["target_id"] for target in packet["targets"]]
    expected_length = len(input_ids) * CODE_WIDTH

    if not isinstance(assignment_code, str):
        raise ValueError("assignment_code must be a string")
    if len(assignment_code) != expected_length:
        raise ValueError(
            f"Expected {expected_length} assignment digits, observed {len(assignment_code)}"
        )
    if re.fullmatch(r"[0-9]+", assignment_code) is None:
        raise ValueError("assignment_code must contain decimal digits only")

    labels = [
        assignment_code[i : i + CODE_WIDTH]
        for i in range(0, expected_length, CODE_WIDTH)
    ]
    if len(labels) != len(input_ids):
        raise ValueError(
            f"Expected {len(input_ids)} fixed-width assignments, observed {len(labels)}"
        )

    # Canonicalize arbitrary fixed-width labels by first occurrence. This is a
    # pure relabeling of the partition and makes no semantic decision.
    label_to_cluster_id: dict[str, str] = {}
    cluster_targets: dict[str, list[str]] = {}
    for target_id, label in zip(input_ids, labels):
        if label not in label_to_cluster_id:
            label_to_cluster_id[label] = f"C{len(label_to_cluster_id) + 1:03d}"
            cluster_targets[label] = []
        cluster_targets[label].append(target_id)

    return {
        "packet_id": packet["packet_id"],
        "clusters": [
            {
                "cluster_id": label_to_cluster_id[label],
                "target_ids": cluster_targets[label],
            }
            for label in label_to_cluster_id
        ],
    }


def build_system_instructions() -> str:
    parent = INSTRUCTIONS.read_text(encoding="utf-8")
    marker = "\n## Cluster IDs\n"
    if marker not in parent:
        raise ValueError("Cannot locate Cluster IDs section in frozen Stage 2 instructions")
    semantic_prefix = parent.split(marker, 1)[0].rstrip()
    encoding = OUTPUT_ENCODING_P1D3.read_text(encoding="utf-8").strip()
    return semantic_prefix + "\n\n" + encoding + "\n"



def rough_tokens(text: str) -> int:
    return max(1, (len(text) + 2) // 3)


def build_client(model_key: str, api_key: str):
    cfg = MODEL_CONFIGS[model_key]
    if cfg["provider"] == "openai":
        from openai import OpenAI
        return OpenAI(api_key=api_key, max_retries=0, timeout=600.0)
    import anthropic
    return anthropic.Anthropic(api_key=api_key, max_retries=0, timeout=600.0)


def call_provider(
    model_key: str,
    client: Any,
    system: str,
    packet: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    cfg = MODEL_CONFIGS[model_key]
    payload = canonical_json(packet)
    schema = output_schema(packet, cfg["provider"])

    if cfg["provider"] == "openai":
        response = client.responses.create(
            model=cfg["model"],
            instructions=system,
            input=payload,
            max_output_tokens=MAX_OUTPUT_TOKENS_BY_MODEL[model_key],
            reasoning={"effort": cfg["reasoning_effort"]},
            text={
                "format": {
                    "type": "json_schema",
                    "name": "e1_stage2_fixed_width_partition",
                    "strict": True,
                    "schema": schema,
                }
            },
        )
        return response.output_text, response.model_dump(mode="json")

    response = client.messages.create(
        model=cfg["model"],
        system=system,
        messages=[{"role": "user", "content": payload}],
        max_tokens=MAX_OUTPUT_TOKENS_BY_MODEL[model_key],
        thinking=cfg["thinking"],
        output_config={
            "effort": cfg["effort"],
            "format": {
                "type": "json_schema",
                "schema": schema,
            },
        },
    )
    text = "".join(
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text"
    )
    return text, response.model_dump(mode="json")


def usage_record(raw: dict[str, Any], model_key: str) -> dict[str, Any]:
    cfg = MODEL_CONFIGS[model_key]
    usage = raw.get("usage") or {}
    inp = usage.get("input_tokens")
    out = usage.get("output_tokens")
    result = {
        "input_tokens": int(inp) if isinstance(inp, (int, float)) else None,
        "output_tokens": int(out) if isinstance(out, (int, float)) else None,
        "conservative_cost_usd": None,
    }
    if result["input_tokens"] is not None and result["output_tokens"] is not None:
        result["conservative_cost_usd"] = (
            result["input_tokens"] / 1_000_000 * float(cfg["input_per_million"])
            + result["output_tokens"] / 1_000_000 * float(cfg["output_per_million"])
        )
    return result


def clear_inflight_marker(retries: int = 40, delay_seconds: float = 0.05) -> None:
    last_error: PermissionError | None = None
    for _ in range(retries):
        try:
            INFLIGHT_PATH.unlink(missing_ok=True)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(delay_seconds)
    raise SystemExit(
        "A provider attempt was preserved but INFLIGHT.json could not be removed: "
        f"{last_error}. This is a local cleanup failure, not an API failure."
    )


def is_transient_exception(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None)
    if status in {408, 409, 429, 500, 502, 503, 504, 529}:
        return True
    name = type(exc).__name__.lower()
    return any(token in name for token in ("timeout", "connection", "ratelimit", "overloaded"))


def terminal_attempt_matches_marker(row: dict[str, Any], marker: dict[str, Any]) -> bool:
    return (
        row.get("task_id") == marker.get("task_id")
        and row.get("attempt_index") == marker.get("attempt_index")
        and row.get("execution_variant", PREDECESSOR_VARIANT)
        == marker.get("execution_variant", PREDECESSOR_VARIANT)
        and row.get("request_sha256") == marker.get("request_sha256")
        and row.get("status") in {"valid", "invalid_output", "api_error"}
    )


def reconcile_inflight() -> bool:
    if not INFLIGHT_PATH.exists():
        return False
    marker = load_json(INFLIGHT_PATH)
    attempts = read_jsonl(ATTEMPTS_PATH)
    if any(terminal_attempt_matches_marker(row, marker) for row in attempts):
        clear_inflight_marker()
        return True
    return False


def derive_state(
    attempts: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    task_map = {task["task_id"]: task for task in tasks}
    completed: dict[str, dict[str, Any]] = {}
    attempt_counts: dict[str, int] = {}
    exhausted: set[str] = set()
    model_costs = {key: 0.0 for key in MODEL_CONFIGS}

    for row in attempts:
        task_id = row.get("task_id")
        if task_id not in task_map:
            raise ValueError(f"Attempt log contains unknown task_id: {task_id}")
        model_key = row.get("model_key")
        row_variant = row.get("execution_variant")
        if row_variant != EXECUTION_VARIANT:
            raise ValueError(
                f"P1D3 output directory contains non-P1D3 attempt lineage: {row_variant!r}"
            )
        attempt_counts[task_id] = attempt_counts.get(task_id, 0) + 1
        cost = row.get("usage", {}).get("conservative_cost_usd")
        if model_key in model_costs and isinstance(cost, (int, float)):
            model_costs[model_key] += float(cost)
        if row.get("status") == "valid":
            if task_id in completed:
                raise ValueError(f"More than one valid partition exists for {task_id}")
            parsed = row.get("parsed")
            if not isinstance(parsed, dict):
                raise ValueError(f"Valid attempt lacks parsed partition: {task_id}")
            completed[task_id] = parsed

    for task_id, count in attempt_counts.items():
        if count >= MAX_ATTEMPTS_PER_TASK and task_id not in completed:
            exhausted.add(task_id)

    return {
        "completed": completed,
        "attempt_counts": attempt_counts,
        "exhausted": exhausted,
        "model_costs": model_costs,
    }


def write_partitions(
    tasks: list[dict[str, Any]],
    completed: dict[str, dict[str, Any]],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with PARTITIONS_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for task in sorted(tasks, key=lambda x: x["task_id"]):
            task_id = task["task_id"]
            if task_id not in completed:
                continue
            row = {
                "task_id": task_id,
                "partition_replicate": task["partition_replicate"],
                "packet_id": task["packet_id"],
                "model_key": task["model_key"],
                "partition": completed[task_id],
            }
            handle.write(canonical_json(row) + "\n")


def package_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for pkg in ("openai", "anthropic"):
        try:
            out[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            pass
    return out


def build_manifest(
    implementation_commit: str | None,
    tasks: list[dict[str, Any]],
    state: dict[str, Any],
    status: str,
    detail: str | None = None,
) -> dict[str, Any]:
    attempts = read_jsonl(ATTEMPTS_PATH)
    return {
        "schema_version": "au-e1-stage2-partition-run-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol": "E1/E1A",
        "execution_protocol": "P1",
        "execution_correction": EXECUTION_VARIANT,
        "predecessor_execution_commit": PREDECESSOR_EXECUTION_COMMIT,
        "output_encoding": OUTPUT_ENCODING,
        "bundle_id": BUNDLE_ID,
        "bundle_commit": BUNDLE_COMMIT,
        "implementation_commit": implementation_commit,
        "runner_path": rel(Path(__file__).resolve()),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "execution_protocol_path": rel(EXECUTION_PROTOCOL),
        "execution_protocol_sha256": sha256_file(EXECUTION_PROTOCOL),
        "foundational_execution_correction_path": rel(EXECUTION_CORRECTION),
        "foundational_execution_correction_sha256": sha256_file(EXECUTION_CORRECTION),
        "prior_execution_correction_path": rel(EXECUTION_CORRECTION_P1D2),
        "prior_execution_correction_sha256": sha256_file(EXECUTION_CORRECTION_P1D2),
        "prior_output_encoding_path": rel(OUTPUT_ENCODING_P1D2),
        "prior_output_encoding_sha256": sha256_file(OUTPUT_ENCODING_P1D2),
        "execution_correction_path": rel(EXECUTION_CORRECTION_P1D3),
        "execution_correction_sha256": sha256_file(EXECUTION_CORRECTION_P1D3),
        "output_encoding_path": rel(OUTPUT_ENCODING_P1D3),
        "output_encoding_sha256": sha256_file(OUTPUT_ENCODING_P1D3),
        "execution_variant_policy": {
            "all_fresh_tasks": EXECUTION_VARIANT,
            "predecessor_execution_is_frozen_and_superseded": True,
        },
        "instructions_sha256": sha256_file(INSTRUCTIONS),
        "runtime_system_sha256": sha256_text(build_system_instructions()),
        "status": status,
        "updated_at": utc_now(),
        "task_count": len(tasks),
        "completed_tasks": len(state["completed"]),
        "remaining_tasks": len(tasks) - len(state["completed"]),
        "exhausted_tasks": sorted(state["exhausted"]),
        "attempt_records": len(attempts),
        "model_costs_usd": {
            key: round(value, 6) for key, value in state["model_costs"].items()
        },
        "model_configs_without_secrets": MODEL_CONFIGS,
        "max_output_tokens_by_model": MAX_OUTPUT_TOKENS_BY_MODEL,
        "max_attempts_per_task": MAX_ATTEMPTS_PER_TASK,
        "canary_task_ids": sorted(CANARY_TASK_IDS),
        "packages": package_versions(),
        "python": sys.version,
        "platform": platform.platform(),
        "attempts_sha256": sha256_file(ATTEMPTS_PATH) if ATTEMPTS_PATH.exists() else None,
        "partitions_sha256": sha256_file(PARTITIONS_PATH) if PARTITIONS_PATH.exists() else None,
        "detail": detail,
    }


def write_manifest(
    implementation_commit: str | None,
    tasks: list[dict[str, Any]],
    state: dict[str, Any],
    status: str,
    detail: str | None = None,
) -> None:
    write_json(
        MANIFEST_PATH,
        build_manifest(implementation_commit, tasks, state, status, detail),
    )


def preflight(implementation_commit: str | None) -> dict[str, Any]:
    index = verify_bundle()
    if implementation_commit is not None:
        verify_implementation(implementation_commit)
    tasks = build_tasks(index)

    instruction_text = build_system_instructions()
    input_by_model = {key: 0 for key in MODEL_CONFIGS}
    max_packet_tokens = 0
    for task in tasks:
        packet = load_packet(task)
        estimated = rough_tokens(instruction_text + "\n" + canonical_json(packet))
        input_by_model[task["model_key"]] += estimated
        max_packet_tokens = max(max_packet_tokens, estimated)

    attempts = read_jsonl(ATTEMPTS_PATH)
    state = derive_state(attempts, tasks)

    result = {
        "status": "stage2_execution_preflight_complete_no_api_calls",
        "bundle_id": BUNDLE_ID,
        "tasks": len(tasks),
        "canary_tasks": len(CANARY_TASK_IDS),
        "completed_tasks_existing": len(state["completed"]),
        "exhausted_tasks_existing": len(state["exhausted"]),
        "inflight_exists": INFLIGHT_PATH.exists(),
        "max_packet_rough_input_tokens": max_packet_tokens,
        "rough_input_tokens_by_model": input_by_model,
        "models": {
            key: {
                "provider": cfg["provider"],
                "model": cfg["model"],
                "reasoning_effort": cfg.get("reasoning_effort"),
                "thinking": cfg.get("thinking"),
                "effort": cfg.get("effort"),
                "max_output_tokens": MAX_OUTPUT_TOKENS_BY_MODEL[key],
                "stop_limit_usd": cfg["stop_limit_usd"],
            }
            for key, cfg in MODEL_CONFIGS.items()
        },
        "canary_task_ids": sorted(CANARY_TASK_IDS),
    }
    return {"result": result, "tasks": tasks, "state": state}


def synthetic_test(model_key: str) -> None:
    load_env_file()
    cfg = MODEL_CONFIGS[model_key]
    api_key = os.environ.get(cfg["api_key_env"])
    if not api_key:
        raise SystemExit(f"Missing environment variable: {cfg['api_key_env']}")
    client = build_client(model_key, api_key)
    system = build_system_instructions()
    raw_text, raw = call_provider(model_key, client, system, SYNTHETIC_PACKET)
    parsed = validate_partition(raw_text, SYNTHETIC_PACKET)
    print(
        json.dumps(
            {
                "status": "synthetic_test_passed",
                "model_key": model_key,
                "model": cfg["model"],
                "max_output_tokens": MAX_OUTPUT_TOKENS_BY_MODEL[model_key],
                "synthetic_target_count": SYNTHETIC_PACKET["target_count"],
                "expected_assignment_digits": SYNTHETIC_PACKET["target_count"] * CODE_WIDTH,
                "cluster_count": len(parsed["clusters"]),
                "usage": usage_record(raw, model_key),
            },
            indent=2,
            sort_keys=True,
        )
    )


def task_execution_variant(task: dict[str, Any]) -> str:
    return EXECUTION_VARIANT


def attempt_task(
    task: dict[str, Any],
    client: Any,
    system: str,
    attempt_index: int,
) -> dict[str, Any]:
    packet = load_packet(task)
    execution_variant = task_execution_variant(task)
    request_config = {
        "execution_variant": execution_variant,
        "model_key": task["model_key"],
        "max_output_tokens": MAX_OUTPUT_TOKENS_BY_MODEL[task["model_key"]],
        "output_encoding": OUTPUT_ENCODING,
    }
    request_sha = sha256_text(
        system + "\n" + canonical_json(packet) + "\n" + canonical_json(request_config)
    )
    marker = {
        "task_id": task["task_id"],
        "attempt_index": attempt_index,
        "model_key": task["model_key"],
        "execution_variant": execution_variant,
        "max_output_tokens": MAX_OUTPUT_TOKENS_BY_MODEL[task["model_key"]],
        "output_encoding": OUTPUT_ENCODING,
        "started_at": utc_now(),
        "request_sha256": request_sha,
    }
    write_json(INFLIGHT_PATH, marker)
    before = time.monotonic()
    base = {
        "schema_version": "au-e1-stage2-partition-attempt-v1",
        "task_id": task["task_id"],
        "partition_replicate": task["partition_replicate"],
        "packet_id": task["packet_id"],
        "model_key": task["model_key"],
        "provider": MODEL_CONFIGS[task["model_key"]]["provider"],
        "model_requested": MODEL_CONFIGS[task["model_key"]]["model"],
        "execution_variant": execution_variant,
        "max_output_tokens": MAX_OUTPUT_TOKENS_BY_MODEL[task["model_key"]],
        "output_encoding": OUTPUT_ENCODING,
        "attempt_index": attempt_index,
        "target_count": task["target_count"],
        "started_at": marker["started_at"],
        "request_sha256": request_sha,
    }

    try:
        raw_text, raw = call_provider(task["model_key"], client, system, packet)
        usage = usage_record(raw, task["model_key"])
        try:
            parsed = validate_partition(raw_text, packet)
        except Exception as exc:
            row = {
                **base,
                "status": "invalid_output",
                "finished_at": utc_now(),
                "elapsed_seconds": round(time.monotonic() - before, 6),
                "raw_text": raw_text,
                "parse_error_type": type(exc).__name__,
                "parse_error": str(exc),
                "usage": usage,
                "raw_provider_response": raw,
            }
            append_jsonl(ATTEMPTS_PATH, row)
            clear_inflight_marker()
            return row

        row = {
            **base,
            "status": "valid",
            "finished_at": utc_now(),
            "elapsed_seconds": round(time.monotonic() - before, 6),
            "raw_text": raw_text,
            "parsed": parsed,
            "usage": usage,
            "raw_provider_response": raw,
        }
        append_jsonl(ATTEMPTS_PATH, row)
        clear_inflight_marker()
        return row

    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        row = {
            **base,
            "status": "api_error",
            "finished_at": utc_now(),
            "elapsed_seconds": round(time.monotonic() - before, 6),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "transient": is_transient_exception(exc),
            "status_code": getattr(exc, "status_code", None),
            "usage": {
                "input_tokens": None,
                "output_tokens": None,
                "conservative_cost_usd": None,
            },
        }
        append_jsonl(ATTEMPTS_PATH, row)
        clear_inflight_marker()
        return row


def run_task_with_retries(
    task: dict[str, Any],
    client: Any,
    system: str,
    existing_attempts: int,
) -> tuple[bool, bool]:
    """Return (completed, permanent_model_failure)."""
    attempt_index = existing_attempts + 1
    while attempt_index <= MAX_ATTEMPTS_PER_TASK:
        row = attempt_task(task, client, system, attempt_index)
        if row["status"] == "valid":
            return True, False

        if row["status"] == "api_error" and not row.get("transient", False):
            return False, True

        if attempt_index >= MAX_ATTEMPTS_PER_TASK:
            return False, False

        delay = TRANSIENT_BACKOFF_SECONDS[min(attempt_index - 1, len(TRANSIENT_BACKOFF_SECONDS) - 1)]
        if row["status"] == "invalid_output":
            delay = min(delay, 5)
        time.sleep(delay)
        attempt_index += 1

    return False, False


def ensure_no_ambiguous_inflight() -> None:
    if not INFLIGHT_PATH.exists():
        return
    if reconcile_inflight():
        return
    raise SystemExit(
        f"{rel(INFLIGHT_PATH)} exists with no matching terminal attempt record. "
        "Do not silently duplicate the request. Use resolve-inflight after inspection."
    )


def execute(
    mode: str,
    implementation_commit: str,
) -> None:
    load_env_file()
    pf = preflight(implementation_commit)
    tasks: list[dict[str, Any]] = pf["tasks"]
    ensure_no_ambiguous_inflight()

    attempts = read_jsonl(ATTEMPTS_PATH)
    state = derive_state(attempts, tasks)
    system = build_system_instructions()

    if mode == "run":
        missing_canaries = sorted(CANARY_TASK_IDS - set(state["completed"]))
        if missing_canaries:
            raise SystemExit(
                "Full run is gated on all required valid canaries. Run the canary command first. "
                f"Missing: {missing_canaries}"
            )
        selected = [
            task for task in tasks
            if task["task_id"] not in state["completed"]
            and task["task_id"] not in state["exhausted"]
        ]
        selected.sort(key=lambda x: (-x["target_count"], x["model_key"], x["task_id"]))
    elif mode == "canary":
        selected = [
            task for task in tasks
            if task["task_id"] in CANARY_TASK_IDS
            and task["task_id"] not in state["completed"]
            and task["task_id"] not in state["exhausted"]
        ]
        selected.sort(key=lambda x: x["model_key"])
    else:
        raise ValueError(mode)

    clients: dict[str, Any] = {}
    blocked_models: set[str] = set()
    exhausted_count_by_model = {key: 0 for key in MODEL_CONFIGS}

    for task in selected:
        model_key = task["model_key"]
        if model_key in blocked_models:
            continue

        attempts = read_jsonl(ATTEMPTS_PATH)
        state = derive_state(attempts, tasks)
        if task["task_id"] in state["completed"] or task["task_id"] in state["exhausted"]:
            continue

        if state["model_costs"][model_key] >= float(MODEL_CONFIGS[model_key]["stop_limit_usd"]):
            blocked_models.add(model_key)
            continue

        if model_key not in clients:
            cfg = MODEL_CONFIGS[model_key]
            api_key = os.environ.get(cfg["api_key_env"])
            if not api_key:
                blocked_models.add(model_key)
                continue
            clients[model_key] = build_client(model_key, api_key)

        existing = state["attempt_counts"].get(task["task_id"], 0)
        completed, permanent_failure = run_task_with_retries(
            task, clients[model_key], system, existing
        )

        if permanent_failure:
            blocked_models.add(model_key)
        elif not completed:
            exhausted_count_by_model[model_key] += 1
            if exhausted_count_by_model[model_key] >= MAX_EXHAUSTED_TASKS_BEFORE_MODEL_BREAK:
                blocked_models.add(model_key)

        attempts = read_jsonl(ATTEMPTS_PATH)
        state = derive_state(attempts, tasks)
        write_partitions(tasks, state["completed"])
        write_manifest(
            implementation_commit,
            tasks,
            state,
            "running" if mode == "run" else "canary_running",
            detail=f"blocked_models={sorted(blocked_models)}",
        )

    attempts = read_jsonl(ATTEMPTS_PATH)
    state = derive_state(attempts, tasks)
    write_partitions(tasks, state["completed"])

    if mode == "canary":
        missing = sorted(CANARY_TASK_IDS - set(state["completed"]))
        status = "canary_passed" if not missing else "canary_incomplete"
        write_manifest(
            implementation_commit, tasks, state, status,
            detail=f"missing_canaries={missing}; blocked_models={sorted(blocked_models)}",
        )
        print(
            json.dumps(
                {
                    "status": status,
                    "completed_canaries": len(CANARY_TASK_IDS) - len(missing),
                    "missing_canaries": missing,
                    "completed_tasks_total": len(state["completed"]),
                    "attempt_records": len(attempts),
                    "model_costs_usd": {
                        k: round(v, 6) for k, v in state["model_costs"].items()
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    status = "complete" if len(state["completed"]) == EXPECTED_TASKS else "incomplete"
    write_manifest(
        implementation_commit, tasks, state, status,
        detail=f"blocked_models={sorted(blocked_models)}",
    )
    print(
        json.dumps(
            {
                "status": status,
                "completed_tasks": len(state["completed"]),
                "remaining_tasks": EXPECTED_TASKS - len(state["completed"]),
                "exhausted_tasks": sorted(state["exhausted"]),
                "blocked_models": sorted(blocked_models),
                "attempt_records": len(attempts),
                "model_costs_usd": {
                    k: round(v, 6) for k, v in state["model_costs"].items()
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


def status_command() -> None:
    index = verify_bundle()
    tasks = build_tasks(index)
    attempts = read_jsonl(ATTEMPTS_PATH)
    state = derive_state(attempts, tasks)
    by_model = {}
    for model_key in MODEL_CONFIGS:
        model_tasks = [t for t in tasks if t["model_key"] == model_key]
        completed = sum(t["task_id"] in state["completed"] for t in model_tasks)
        by_model[model_key] = {
            "completed": completed,
            "total": len(model_tasks),
            "remaining": len(model_tasks) - completed,
            "cost_usd": round(state["model_costs"][model_key], 6),
        }
    print(
        json.dumps(
            {
                "status": "complete" if len(state["completed"]) == EXPECTED_TASKS else "incomplete",
                "completed_tasks": len(state["completed"]),
                "total_tasks": EXPECTED_TASKS,
                "percent_complete": round(100 * len(state["completed"]) / EXPECTED_TASKS, 1),
                "canaries_complete": len(CANARY_TASK_IDS & set(state["completed"])),
                "exhausted_tasks": sorted(state["exhausted"]),
                "attempt_records": len(attempts),
                "by_model": by_model,
            },
            indent=2,
            sort_keys=True,
        )
    )


def validate_command(implementation_commit: str | None) -> None:
    pf = preflight(implementation_commit)
    tasks: list[dict[str, Any]] = pf["tasks"]
    attempts = read_jsonl(ATTEMPTS_PATH)
    state = derive_state(attempts, tasks)
    write_partitions(tasks, state["completed"])

    per_packet: dict[str, int] = {}
    for task in tasks:
        if task["task_id"] in state["completed"]:
            per_packet[task["packet_id"]] = per_packet.get(task["packet_id"], 0) + 1

    bad_packet_counts = {
        packet_id: count
        for packet_id, count in per_packet.items()
        if count != 3
    }
    missing_packet_ids = sorted(
        {task["packet_id"] for task in tasks} - set(per_packet)
    )

    result = {
        "status": "complete" if len(state["completed"]) == EXPECTED_TASKS else "incomplete",
        "completed_tasks": len(state["completed"]),
        "remaining_tasks": EXPECTED_TASKS - len(state["completed"]),
        "attempt_records": len(attempts),
        "exhausted_tasks": sorted(state["exhausted"]),
        "canaries_complete": len(CANARY_TASK_IDS & set(state["completed"])),
        "packets_with_three_partitions": sum(count == 3 for count in per_packet.values()),
        "bad_packet_partition_counts": bad_packet_counts,
        "missing_packet_ids": missing_packet_ids,
        "model_costs_usd": {
            k: round(v, 6) for k, v in state["model_costs"].items()
        },
        "attempts_sha256": sha256_file(ATTEMPTS_PATH) if ATTEMPTS_PATH.exists() else None,
        "partitions_sha256": sha256_file(PARTITIONS_PATH) if PARTITIONS_PATH.exists() else None,
        "inflight_exists": INFLIGHT_PATH.exists(),
    }
    write_manifest(
        implementation_commit, tasks, state, result["status"],
        detail="validation pass",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def resolve_inflight(action: str) -> None:
    if not INFLIGHT_PATH.exists():
        raise SystemExit("No INFLIGHT.json exists.")
    if action != "retry":
        raise ValueError(action)
    marker = load_json(INFLIGHT_PATH)
    row = {
        "schema_version": "au-e1-stage2-partition-attempt-v1",
        "task_id": marker["task_id"],
        "partition_replicate": marker["task_id"].split("-", 1)[0],
        "packet_id": marker["task_id"].split("-", 1)[1],
        "model_key": marker["model_key"],
        "provider": MODEL_CONFIGS[marker["model_key"]]["provider"],
        "model_requested": MODEL_CONFIGS[marker["model_key"]]["model"],
        "attempt_index": marker["attempt_index"],
        "execution_variant": marker.get("execution_variant", PREDECESSOR_VARIANT),
        "output_encoding": marker.get("output_encoding"),
        "max_output_tokens": marker.get(
            "max_output_tokens",
            MAX_OUTPUT_TOKENS_BY_MODEL[marker["model_key"]],
        ),
        "started_at": marker["started_at"],
        "finished_at": utc_now(),
        "request_sha256": marker["request_sha256"],
        "status": "orphaned_dispatch",
        "usage": {
            "input_tokens": None,
            "output_tokens": None,
            "conservative_cost_usd": None,
        },
        "note": (
            "Process ended with this request in flight. Provider-side completion is unknown "
            "and no local semantic result exists. The orphan is preserved before retry."
        ),
    }
    append_jsonl(ATTEMPTS_PATH, row)
    clear_inflight_marker()
    print(json.dumps({"status": "inflight_preserved_for_retry", "task_id": marker["task_id"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight", help="Verify signed inputs and roster; no API calls")
    pre.add_argument("--implementation-commit")

    syn = sub.add_parser("synthetic-test", help="Test one model path with a synthetic packet")
    syn.add_argument("--model", required=True, choices=sorted(MODEL_CONFIGS))

    can = sub.add_parser("canary", help="Run/resume the seven real stress/recovery canaries")
    can.add_argument("--implementation-commit", required=True)

    run = sub.add_parser("run", help="Run/resume all remaining partitions after canaries pass")
    run.add_argument("--implementation-commit", required=True)

    sub.add_parser("status", help="Safe read-only progress summary from the attempt log")

    val = sub.add_parser("validate", help="Validate/rebuild final partitions")
    val.add_argument("--implementation-commit")

    res = sub.add_parser("resolve-inflight", help="Preserve an ambiguous interrupted dispatch")
    res.add_argument("--action", required=True, choices=["retry"])

    args = parser.parse_args()

    if args.command == "preflight":
        pf = preflight(args.implementation_commit)
        print(json.dumps(pf["result"], indent=2, sort_keys=True))
    elif args.command == "synthetic-test":
        synthetic_test(args.model)
    elif args.command == "canary":
        execute("canary", args.implementation_commit)
    elif args.command == "run":
        execute("run", args.implementation_commit)
    elif args.command == "status":
        status_command()
    elif args.command == "validate":
        validate_command(args.implementation_commit)
    elif args.command == "resolve-inflight":
        resolve_inflight(args.action)
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
