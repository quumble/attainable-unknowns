#!/usr/bin/env python3
"""Run E1/FA1 blinded focal-alignment coding, tiebreaking, and finalization."""

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
PROTOCOL = E1_DIR / "E1_FOCAL_ALIGNMENT_EXECUTION_FA1.md"
INSTRUCTIONS_SOURCE = E1_DIR / "E1_FOCAL_ALIGNMENT_INSTRUCTIONS.md"
GENERATOR = E1_DIR / "generate_e1_focal_alignment.py"
RUNNER = Path(__file__).resolve()

GENERATED_ROOT = E1_DIR / "e1" / "focal_alignment" / "generated"
CODING_ROOT = E1_DIR / "e1" / "focal_alignment" / "coding"

EXPECTED_PACKETS = 72
EXPECTED_CLUSTERS = 2026
MAX_ATTEMPTS_PER_TASK = 3
TRANSIENT_BACKOFF_SECONDS = (5, 15)
LABELS = {"F": "focal", "A": "adjacent", "P": "peripheral", "I": "indeterminate"}
LABEL_CODES = set(LABELS)

MODEL_CONFIGS: dict[str, dict[str, Any]] = {
    "sol": {
        "provider": "openai",
        "model": "gpt-5.6-sol",
        "api_key_env": "OPENAI_API_KEY",
        "reasoning_effort": "low",
        "input_per_million": 4.00,
        "output_per_million": 20.00,
        "stop_limit_usd": 10.00,
        "max_output_tokens": 4096,
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
        "max_output_tokens": 8192,
    },
    "terra": {
        "provider": "openai",
        "model": "gpt-5.6-terra",
        "api_key_env": "OPENAI_API_KEY",
        "reasoning_effort": "low",
        "input_per_million": 2.00,
        "output_per_million": 12.00,
        "stop_limit_usd": 5.00,
        "max_output_tokens": 4096,
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
        "max_output_tokens": 8192,
    },
}

SYNTHETIC_PACKET = {
    "schema_version": "au-e1-fa1-alignment-packet-v1",
    "study": "synthetic runner fixture",
    "protocol_id": "FA1",
    "alignment_packet_id": "SYNTHETIC-FA1-001",
    "focal_unknown_anchor": "The planning problem is choosing a route that balances speed and reliability.",
    "cluster_count": 8,
    "clusters": [
        {"cluster_ref": "K001", "member_targets": ["Which route best balances speed and reliability?"]},
        {"cluster_ref": "K002", "member_targets": ["How variable is travel time on each route?"]},
        {"cluster_ref": "K003", "member_targets": ["What landmarks appear along the route?"]},
        {"cluster_ref": "K004", "member_targets": ["What decision rule should determine the route choice?"]},
        {"cluster_ref": "K005", "member_targets": ["How does weather affect route reliability?"]},
        {"cluster_ref": "K006", "member_targets": ["Who first mapped the area?"]},
        {"cluster_ref": "K007", "member_targets": ["What are the consequences of a delayed arrival?"]},
        {"cluster_ref": "K008", "member_targets": ["Mixed target A", "Unrelated target B"]},
    ],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


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


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n", buffering=1) as handle:
        handle.write(canonical_json(value) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(canonical_json(row) + "\n")


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)


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
    return committed.returncode == 0 and current.returncode == 0 and committed.stdout.strip() == current.stdout.strip()


def load_env_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def bundle_dir(bundle_id: str) -> Path:
    return GENERATED_ROOT / bundle_id


def bundle_paths(bundle_id: str) -> dict[str, Path]:
    base = bundle_dir(bundle_id)
    return {
        "base": base,
        "record": base / "FA1_GENERATION_RECORD.json",
        "index": base / "blinded" / "FA1_PACKET_INDEX.json",
        "instructions": base / "blinded" / "E1_FOCAL_ALIGNMENT_INSTRUCTIONS.md",
        "private": base / "private" / "FA1_PRIVATE_KEY.json",
    }


def verify_bundle(bundle_id: str, bundle_commit_ref: str) -> dict[str, Any]:
    paths = bundle_paths(bundle_id)
    for path in paths.values():
        if path == paths["base"]:
            continue
        if not path.is_file():
            raise FileNotFoundError(path)

    record = load_json(paths["record"])
    if record.get("bundle_id") != bundle_id:
        raise ValueError("FA1 generation record bundle ID mismatch")
    implementation_commit = str(record.get("implementation_commit"))
    verify_signed_commit(implementation_commit, "FA1 implementation")
    for implementation_path in (PROTOCOL, INSTRUCTIONS_SOURCE, GENERATOR, RUNNER):
        if not implementation_path.is_file():
            raise FileNotFoundError(implementation_path)
        if not committed_blob_matches_worktree(implementation_commit, implementation_path):
            raise ValueError(
                f"Working FA1 implementation file differs from signed implementation: {rel(implementation_path)}"
            )

    bundle_commit = verify_signed_commit(bundle_commit_ref, "FA1 generated packet bundle")
    if git("merge-base", "--is-ancestor", implementation_commit, bundle_commit).returncode != 0:
        raise ValueError("FA1 implementation is not an ancestor of packet-bundle freeze")

    index = load_json(paths["index"])
    if index.get("bundle_id") != bundle_id or index.get("packet_count") != EXPECTED_PACKETS:
        raise ValueError("FA1 packet index identity/count mismatch")
    if index.get("cluster_instance_count") != EXPECTED_CLUSTERS:
        raise ValueError("FA1 packet index cluster count mismatch")
    if sha256_file(paths["index"]) != record.get("packet_index_sha256"):
        raise ValueError("FA1 packet index SHA-256 mismatch")
    if sha256_file(paths["private"]) != record.get("private_key_sha256"):
        raise ValueError("FA1 private-key SHA-256 mismatch")
    if sha256_file(paths["instructions"]) != index.get("instructions_sha256"):
        raise ValueError("FA1 copied instruction SHA-256 mismatch")

    required = [paths["record"], paths["index"], paths["instructions"], paths["private"]]
    packet_ids: set[str] = set()
    cluster_total = 0
    for row in index["packets"]:
        packet_id = row.get("alignment_packet_id")
        path = ROOT / row.get("path", "")
        if not isinstance(packet_id, str) or packet_id in packet_ids:
            raise ValueError("Invalid/duplicate FA1 alignment packet ID")
        packet_ids.add(packet_id)
        if not path.is_file() or sha256_file(path) != row.get("sha256"):
            raise ValueError(f"FA1 alignment packet hash mismatch: {packet_id}")
        packet = load_json(path)
        if packet.get("alignment_packet_id") != packet_id:
            raise ValueError(f"FA1 alignment packet identity mismatch: {packet_id}")
        if packet.get("cluster_count") != row.get("cluster_count"):
            raise ValueError(f"FA1 alignment packet cluster-count mismatch: {packet_id}")
        clusters = packet.get("clusters")
        if not isinstance(clusters, list) or len(clusters) != int(row["cluster_count"]):
            raise ValueError(f"Invalid cluster list in {packet_id}")
        refs = [c.get("cluster_ref") for c in clusters]
        if len(refs) != len(set(refs)) or not all(isinstance(x, str) for x in refs):
            raise ValueError(f"Invalid cluster refs in {packet_id}")
        for cluster in clusters:
            members = cluster.get("member_targets")
            if not isinstance(members, list) or not members or not all(isinstance(x, str) and x.strip() for x in members):
                raise ValueError(f"Invalid member targets in {packet_id}:{cluster.get('cluster_ref')}")
        cluster_total += len(clusters)
        required.append(path)

    if cluster_total != EXPECTED_CLUSTERS:
        raise ValueError(f"Expected {EXPECTED_CLUSTERS} cluster instances, found {cluster_total}")
    for path in required:
        if not committed_blob_matches_worktree(bundle_commit, path):
            raise ValueError(f"Generated FA1 bundle file differs from signed bundle commit: {rel(path)}")

    private = load_json(paths["private"])
    if private.get("bundle_id") != bundle_id or len(private.get("packets", [])) != EXPECTED_PACKETS:
        raise ValueError("FA1 private key identity/count mismatch")

    return {
        "bundle_commit": bundle_commit,
        "implementation_commit": implementation_commit,
        "record": record,
        "index": index,
        "private": private,
        "paths": paths,
    }


def load_packet(index_row: dict[str, Any]) -> dict[str, Any]:
    packet = load_json(ROOT / index_row["path"])
    if packet.get("alignment_packet_id") != index_row["alignment_packet_id"]:
        raise ValueError("Alignment packet identity mismatch")
    return packet


def output_schema(packet_id_field: str, packet_id: str, count: int) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            packet_id_field: {"type": "string"},
            "alignment_code": {"type": "string", "pattern": rf"^[FAPI]{{{count}}}$"},
        },
        "required": [packet_id_field, "alignment_code"],
        "additionalProperties": False,
    }


def validate_alignment_output(text: str, packet: dict[str, Any], packet_id_field: str) -> dict[str, Any]:
    try:
        value = json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Response is not valid JSON: {exc}") from exc
    packet_id = packet[packet_id_field]
    if not isinstance(value, dict) or set(value) != {packet_id_field, "alignment_code"}:
        raise ValueError(f"Output must contain exactly {packet_id_field} and alignment_code")
    if value[packet_id_field] != packet_id:
        raise ValueError(f"{packet_id_field} mismatch")
    code = value["alignment_code"]
    expected = int(packet["cluster_count"])
    if not isinstance(code, str) or len(code) != expected or any(ch not in LABEL_CODES for ch in code):
        raise ValueError(f"alignment_code must contain exactly {expected} F/A/P/I characters")
    clusters = packet["clusters"]
    return {
        packet_id_field: packet_id,
        "labels": [
            {"cluster_ref": cluster["cluster_ref"], "code": ch, "label": LABELS[ch]}
            for cluster, ch in zip(clusters, code)
        ],
    }


def build_client(model_key: str, api_key: str):
    cfg = MODEL_CONFIGS[model_key]
    if cfg["provider"] == "openai":
        from openai import OpenAI
        return OpenAI(api_key=api_key, max_retries=0, timeout=600.0)
    import anthropic
    return anthropic.Anthropic(api_key=api_key, max_retries=0, timeout=600.0)


def call_provider(model_key: str, client: Any, instructions: str, packet: dict[str, Any], packet_id_field: str) -> tuple[str, dict[str, Any]]:
    cfg = MODEL_CONFIGS[model_key]
    payload = canonical_json(packet)
    schema = output_schema(packet_id_field, packet[packet_id_field], int(packet["cluster_count"]))

    if cfg["provider"] == "openai":
        response = client.responses.create(
            model=cfg["model"],
            instructions=instructions,
            input=payload,
            max_output_tokens=cfg["max_output_tokens"],
            reasoning={"effort": cfg["reasoning_effort"]},
            text={
                "format": {
                    "type": "json_schema",
                    "name": "e1_fa1_alignment",
                    "strict": True,
                    "schema": schema,
                }
            },
        )
        return response.output_text, response.model_dump(mode="json")

    response = client.messages.create(
        model=cfg["model"],
        system=instructions,
        messages=[{"role": "user", "content": payload}],
        max_tokens=cfg["max_output_tokens"],
        thinking=cfg["thinking"],
        output_config={
            "effort": cfg["effort"],
            "format": {"type": "json_schema", "schema": schema},
        },
    )
    text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
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


def is_transient_exception(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None)
    if status in {408, 409, 429, 500, 502, 503, 504, 529}:
        return True
    name = type(exc).__name__.lower()
    return any(token in name for token in ("timeout", "connection", "ratelimit", "overloaded"))


def clear_marker(path: Path) -> None:
    for _ in range(40):
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError:
            time.sleep(0.05)
    raise SystemExit(f"Could not remove in-flight marker: {path}")


def package_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for pkg in ("openai", "anthropic"):
        try:
            out[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            pass
    return out


def primary_paths(bundle_id: str) -> dict[str, Path]:
    base = CODING_ROOT / bundle_id / "primary"
    return {
        "base": base,
        "attempts": base / "ATTEMPTS.jsonl",
        "codes": base / "PRIMARY_CODES.jsonl",
        "manifest": base / "RUN_MANIFEST.json",
        "inflight": base / "INFLIGHT.json",
    }


def build_primary_tasks(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for row in bundle["index"]["packets"]:
        for model_key in ("sol", "opus"):
            tasks.append(
                {
                    "task_id": f"{model_key}-{row['alignment_packet_id']}",
                    "model_key": model_key,
                    "alignment_packet_id": row["alignment_packet_id"],
                    "packet_path": row["path"],
                    "packet_sha256": row["sha256"],
                    "cluster_count": int(row["cluster_count"]),
                }
            )
    if len(tasks) != EXPECTED_PACKETS * 2:
        raise ValueError("Unexpected FA1 primary task count")
    return sorted(tasks, key=lambda x: x["task_id"])


def derive_state(attempts: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> dict[str, Any]:
    task_map = {t["task_id"]: t for t in tasks}
    completed: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {}
    model_costs = {key: 0.0 for key in MODEL_CONFIGS}
    for row in attempts:
        tid = row.get("task_id")
        if tid not in task_map:
            raise ValueError(f"Attempt log contains unknown task: {tid}")
        counts[tid] = counts.get(tid, 0) + 1
        cost = row.get("usage", {}).get("conservative_cost_usd")
        mk = row.get("model_key")
        if mk in model_costs and isinstance(cost, (int, float)):
            model_costs[mk] += float(cost)
        if row.get("status") == "valid":
            if tid in completed:
                raise ValueError(f"Multiple valid outputs for task: {tid}")
            completed[tid] = row["parsed"]
    exhausted = {tid for tid, n in counts.items() if n >= MAX_ATTEMPTS_PER_TASK and tid not in completed}
    return {"completed": completed, "attempt_counts": counts, "exhausted": exhausted, "model_costs": model_costs}


def write_primary_codes(bundle_id: str, tasks: list[dict[str, Any]], completed: dict[str, dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = []
    for task in sorted(tasks, key=lambda x: x["task_id"]):
        if task["task_id"] not in completed:
            continue
        parsed = completed[task["task_id"]]
        rows.append(
            {
                "schema_version": "au-e1-fa1-primary-code-v1",
                "task_id": task["task_id"],
                "model_key": task["model_key"],
                "alignment_packet_id": task["alignment_packet_id"],
                "labels": parsed["labels"],
            }
        )
    write_jsonl(primary_paths(bundle_id)["codes"], rows)


def primary_manifest(bundle_id: str, bundle: dict[str, Any], tasks: list[dict[str, Any]], state: dict[str, Any], status: str) -> dict[str, Any]:
    paths = primary_paths(bundle_id)
    attempts = read_jsonl(paths["attempts"])
    return {
        "schema_version": "au-e1-fa1-primary-run-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "FA1",
        "bundle_id": bundle_id,
        "packet_bundle_commit": bundle["bundle_commit"],
        "implementation_commit": bundle["implementation_commit"],
        "runner_path": rel(RUNNER),
        "runner_sha256": sha256_file(RUNNER),
        "instructions_sha256": sha256_file(bundle["paths"]["instructions"]),
        "status": status,
        "updated_at_utc": utc_now(),
        "task_count": len(tasks),
        "completed_tasks": len(state["completed"]),
        "remaining_tasks": len(tasks) - len(state["completed"]),
        "exhausted_tasks": sorted(state["exhausted"]),
        "attempt_records": len(attempts),
        "model_costs_usd": {k: round(v, 6) for k, v in state["model_costs"].items()},
        "model_configs_without_secrets": MODEL_CONFIGS,
        "packages": package_versions(),
        "python": sys.version,
        "platform": platform.platform(),
        "attempts_sha256": sha256_file(paths["attempts"]) if paths["attempts"].exists() else None,
        "primary_codes_sha256": sha256_file(paths["codes"]) if paths["codes"].exists() else None,
    }


def save_primary_state(bundle_id: str, bundle: dict[str, Any], tasks: list[dict[str, Any]], state: dict[str, Any], status: str) -> None:
    paths = primary_paths(bundle_id)
    paths["base"].mkdir(parents=True, exist_ok=True)
    write_primary_codes(bundle_id, tasks, state["completed"])
    write_json(paths["manifest"], primary_manifest(bundle_id, bundle, tasks, state, status))


def attempt_task(task: dict[str, Any], packet: dict[str, Any], model_key: str, client: Any, instructions: str, attempt_index: int, attempts_path: Path, inflight_path: Path, packet_id_field: str) -> dict[str, Any]:
    request_sha = sha256_text(instructions + "\n" + canonical_json(packet) + "\n" + model_key)
    marker = {
        "task_id": task["task_id"],
        "model_key": model_key,
        "attempt_index": attempt_index,
        "started_at": utc_now(),
        "request_sha256": request_sha,
    }
    write_json(inflight_path, marker)
    before = time.monotonic()
    base = {
        "schema_version": "au-e1-fa1-attempt-v1",
        "task_id": task["task_id"],
        "model_key": model_key,
        "provider": MODEL_CONFIGS[model_key]["provider"],
        "model_requested": MODEL_CONFIGS[model_key]["model"],
        "attempt_index": attempt_index,
        "started_at": marker["started_at"],
        "request_sha256": request_sha,
    }
    try:
        raw_text, raw = call_provider(model_key, client, instructions, packet, packet_id_field)
        usage = usage_record(raw, model_key)
        try:
            parsed = validate_alignment_output(raw_text, packet, packet_id_field)
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
            append_jsonl(attempts_path, row)
            clear_marker(inflight_path)
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
        append_jsonl(attempts_path, row)
        clear_marker(inflight_path)
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
            "usage": {"input_tokens": None, "output_tokens": None, "conservative_cost_usd": None},
        }
        append_jsonl(attempts_path, row)
        clear_marker(inflight_path)
        return row


def run_one(task: dict[str, Any], packet: dict[str, Any], client: Any, instructions: str, existing_attempts: int, attempts_path: Path, inflight_path: Path, packet_id_field: str) -> tuple[bool, bool]:
    attempt_index = existing_attempts + 1
    while attempt_index <= MAX_ATTEMPTS_PER_TASK:
        row = attempt_task(task, packet, task["model_key"], client, instructions, attempt_index, attempts_path, inflight_path, packet_id_field)
        if row["status"] == "valid":
            return True, False
        if row["status"] == "api_error" and not row.get("transient", False):
            return False, True
        if attempt_index >= MAX_ATTEMPTS_PER_TASK:
            return False, False
        delay = TRANSIENT_BACKOFF_SECONDS[min(attempt_index - 1, len(TRANSIENT_BACKOFF_SECONDS) - 1)]
        if row["status"] == "invalid_output":
            delay = min(delay, 3)
        time.sleep(delay)
        attempt_index += 1
    return False, False


def ensure_no_ambiguous_inflight(path: Path) -> None:
    if path.exists():
        raise SystemExit(f"Ambiguous in-flight marker exists: {rel(path)}. Inspect before retrying.")


def primary_preflight(bundle_id: str, bundle_commit: str) -> dict[str, Any]:
    bundle = verify_bundle(bundle_id, bundle_commit)
    tasks = build_primary_tasks(bundle)
    paths = primary_paths(bundle_id)
    attempts = read_jsonl(paths["attempts"])
    state = derive_state(attempts, tasks)
    largest = max(bundle["index"]["packets"], key=lambda r: (int(r["cluster_count"]), r["alignment_packet_id"]))
    return {
        "bundle": bundle,
        "tasks": tasks,
        "state": state,
        "result": {
            "status": "fa1_primary_preflight_complete_no_api_calls",
            "bundle_id": bundle_id,
            "packet_bundle_commit": bundle["bundle_commit"],
            "primary_tasks": len(tasks),
            "clusters_per_primary_representation": EXPECTED_CLUSTERS,
            "completed_tasks_existing": len(state["completed"]),
            "exhausted_tasks_existing": len(state["exhausted"]),
            "largest_packet": largest["alignment_packet_id"],
            "largest_packet_cluster_count": largest["cluster_count"],
            "inflight_exists": paths["inflight"].exists(),
        },
    }


def execute_primary(mode: str, bundle_id: str, bundle_commit: str) -> None:
    load_env_file()
    pf = primary_preflight(bundle_id, bundle_commit)
    bundle, tasks = pf["bundle"], pf["tasks"]
    paths = primary_paths(bundle_id)
    paths["base"].mkdir(parents=True, exist_ok=True)
    ensure_no_ambiguous_inflight(paths["inflight"])
    instructions = bundle["paths"]["instructions"].read_text(encoding="utf-8")

    attempts = read_jsonl(paths["attempts"])
    state = derive_state(attempts, tasks)
    largest_packet = max(bundle["index"]["packets"], key=lambda r: (int(r["cluster_count"]), r["alignment_packet_id"]))["alignment_packet_id"]
    canary_ids = {f"sol-{largest_packet}", f"opus-{largest_packet}"}

    if mode == "primary" and not canary_ids.issubset(state["completed"]):
        raise SystemExit("Primary run is gated on both valid primary canaries. Run primary-canary first.")

    selected = [t for t in tasks if t["task_id"] not in state["completed"] and t["task_id"] not in state["exhausted"]]
    if mode == "canary":
        selected = [t for t in selected if t["task_id"] in canary_ids]
    selected.sort(key=lambda x: (-x["cluster_count"], x["model_key"], x["task_id"]))

    index_rows = {r["alignment_packet_id"]: r for r in bundle["index"]["packets"]}
    clients: dict[str, Any] = {}
    blocked: set[str] = set()

    for task in selected:
        model_key = task["model_key"]
        attempts = read_jsonl(paths["attempts"])
        state = derive_state(attempts, tasks)
        if task["task_id"] in state["completed"] or task["task_id"] in state["exhausted"] or model_key in blocked:
            continue
        if state["model_costs"][model_key] >= float(MODEL_CONFIGS[model_key]["stop_limit_usd"]):
            blocked.add(model_key)
            continue
        if model_key not in clients:
            cfg = MODEL_CONFIGS[model_key]
            key = os.environ.get(cfg["api_key_env"])
            if not key:
                blocked.add(model_key)
                continue
            clients[model_key] = build_client(model_key, key)
        packet = load_packet(index_rows[task["alignment_packet_id"]])
        completed, permanent = run_one(
            task,
            packet,
            clients[model_key],
            instructions,
            state["attempt_counts"].get(task["task_id"], 0),
            paths["attempts"],
            paths["inflight"],
            "alignment_packet_id",
        )
        if permanent:
            blocked.add(model_key)
        attempts = read_jsonl(paths["attempts"])
        state = derive_state(attempts, tasks)
        status = "primary_running" if mode == "primary" else "primary_canary_running"
        save_primary_state(bundle_id, bundle, tasks, state, status)

    attempts = read_jsonl(paths["attempts"])
    state = derive_state(attempts, tasks)
    if mode == "canary":
        missing = sorted(canary_ids - set(state["completed"]))
        status = "primary_canary_passed" if not missing else "primary_canary_incomplete"
    else:
        missing = []
        status = "primary_complete" if len(state["completed"]) == len(tasks) else "primary_incomplete"
    save_primary_state(bundle_id, bundle, tasks, state, status)
    print(json.dumps({
        "status": status,
        "completed_tasks": len(state["completed"]),
        "remaining_tasks": len(tasks) - len(state["completed"]),
        "exhausted_tasks": sorted(state["exhausted"]),
        "missing_canaries": missing,
        "blocked_models": sorted(blocked),
        "model_costs_usd": {k: round(v, 6) for k, v in state["model_costs"].items()},
    }, indent=2, sort_keys=True))


def validate_primary(bundle_id: str, bundle_commit: str, write_outputs: bool = True) -> dict[str, Any]:
    pf = primary_preflight(bundle_id, bundle_commit)
    bundle, tasks, state = pf["bundle"], pf["tasks"], pf["state"]
    if write_outputs:
        save_primary_state(bundle_id, bundle, tasks, state, "primary_complete" if len(state["completed"]) == len(tasks) else "primary_incomplete")

    codes_path = primary_paths(bundle_id)["codes"]
    if codes_path.exists():
        actual_rows = read_jsonl(codes_path)
        expected_rows: list[dict[str, Any]] = []
        for task in sorted(tasks, key=lambda x: x["task_id"]):
            if task["task_id"] not in state["completed"]:
                continue
            expected_rows.append({
                "schema_version": "au-e1-fa1-primary-code-v1",
                "task_id": task["task_id"],
                "model_key": task["model_key"],
                "alignment_packet_id": task["alignment_packet_id"],
                "labels": state["completed"][task["task_id"]]["labels"],
            })
        if actual_rows != expected_rows:
            raise ValueError("PRIMARY_CODES.jsonl does not match the validated attempt log")
    elif state["completed"]:
        raise ValueError("Primary attempts exist but PRIMARY_CODES.jsonl is missing")

    by_model = {mk: sum(t["model_key"] == mk and t["task_id"] in state["completed"] for t in tasks) for mk in ("sol", "opus")}
    return {
        "status": "complete" if len(state["completed"]) == len(tasks) else "incomplete",
        "completed_tasks": len(state["completed"]),
        "expected_tasks": len(tasks),
        "by_model": by_model,
        "exhausted_tasks": sorted(state["exhausted"]),
        "primary_codes_sha256": sha256_file(primary_paths(bundle_id)["codes"]) if primary_paths(bundle_id)["codes"].exists() else None,
        "attempts_sha256": sha256_file(primary_paths(bundle_id)["attempts"]) if primary_paths(bundle_id)["attempts"].exists() else None,
        "inflight_exists": primary_paths(bundle_id)["inflight"].exists(),
    }


def verify_primary_freeze(bundle_id: str, bundle_commit: str, primary_commit_ref: str) -> tuple[str, list[dict[str, Any]]]:
    bundle = verify_bundle(bundle_id, bundle_commit)
    result = validate_primary(bundle_id, bundle_commit, write_outputs=False)
    if result["status"] != "complete" or result["inflight_exists"]:
        raise ValueError("Primary coding is not complete and clean")
    commit = verify_signed_commit(primary_commit_ref, "FA1 primary coding freeze")
    if git("merge-base", "--is-ancestor", bundle["bundle_commit"], commit).returncode != 0:
        raise ValueError("Packet-bundle freeze is not an ancestor of primary freeze")
    paths = primary_paths(bundle_id)
    for path in (paths["attempts"], paths["codes"], paths["manifest"]):
        if not committed_blob_matches_worktree(commit, path):
            raise ValueError(f"Primary output differs from signed primary freeze: {rel(path)}")
    rows = read_jsonl(paths["codes"])
    if len(rows) != EXPECTED_PACKETS * 2:
        raise ValueError("Primary code row count mismatch")
    return commit, rows


def private_packet_map(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = bundle["private"].get("packets")
    if not isinstance(rows, list) or len(rows) != EXPECTED_PACKETS:
        raise ValueError("FA1 private packet map missing/incomplete")
    return {row["alignment_packet_id"]: row for row in rows}


def primary_label_maps(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, str]]]:
    out: dict[str, dict[str, dict[str, str]]] = {"sol": {}, "opus": {}}
    for row in rows:
        mk = row.get("model_key")
        pid = row.get("alignment_packet_id")
        if mk not in out or not isinstance(pid, str):
            raise ValueError("Invalid primary code row")
        labels = row.get("labels")
        if not isinstance(labels, list):
            raise ValueError("Invalid primary labels")
        if pid in out[mk]:
            raise ValueError(f"Duplicate primary code row: {mk}/{pid}")
        out[mk][pid] = {x["cluster_ref"]: x["code"] for x in labels}
    if len(out["sol"]) != EXPECTED_PACKETS or len(out["opus"]) != EXPECTED_PACKETS:
        raise ValueError("Incomplete primary label maps")
    return out


def tiebreak_paths(bundle_id: str) -> dict[str, Path]:
    base = CODING_ROOT / bundle_id / "tiebreak"
    return {
        "base": base,
        "generated": base / "generated",
        "index": base / "generated" / "TIEBREAK_PACKET_INDEX.json",
        "private": base / "generated" / "TIEBREAK_PRIVATE_KEY.json",
        "record": base / "generated" / "TIEBREAK_PREPARATION_RECORD.json",
        "results": base / "results",
        "attempts": base / "results" / "ATTEMPTS.jsonl",
        "codes": base / "results" / "TIEBREAK_CODES.jsonl",
        "manifest": base / "results" / "RUN_MANIFEST.json",
        "inflight": base / "results" / "INFLIGHT.json",
    }


def topic_number(topic_packet_id: str) -> int:
    match = re.search(r"T(\d+)$", topic_packet_id)
    if not match:
        raise ValueError(f"Cannot parse topic number: {topic_packet_id}")
    return int(match.group(1))


def prepare_tiebreak(bundle_id: str, bundle_commit: str, primary_commit: str) -> None:
    bundle = verify_bundle(bundle_id, bundle_commit)
    primary_freeze, primary_rows = verify_primary_freeze(bundle_id, bundle_commit, primary_commit)
    label_maps = primary_label_maps(primary_rows)
    pmap = private_packet_map(bundle)
    index_rows = {r["alignment_packet_id"]: r for r in bundle["index"]["packets"]}
    paths = tiebreak_paths(bundle_id)
    if paths["generated"].exists():
        raise FileExistsError(f"Refusing to overwrite existing tiebreak bundle: {paths['generated']}")
    paths["generated"].mkdir(parents=True)

    disagreements: list[tuple[str, str]] = []
    for pid in sorted(index_rows):
        packet = load_packet(index_rows[pid])
        for cluster in packet["clusters"]:
            cref = cluster["cluster_ref"]
            if label_maps["sol"][pid][cref] != label_maps["opus"][pid][cref]:
                disagreements.append((pid, cref))

    by_packet: dict[str, list[str]] = {}
    for pid, cref in disagreements:
        by_packet.setdefault(pid, []).append(cref)

    packet_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    for number, pid in enumerate(sorted(by_packet), start=1):
        source = load_packet(index_rows[pid])
        wanted = set(by_packet[pid])
        clusters = [c for c in source["clusters"] if c["cluster_ref"] in wanted]
        if len(clusters) != len(wanted):
            raise ValueError(f"Tiebreak source-cluster mismatch: {pid}")
        tbid = f"AU-E1-FA1-R{number:03d}"
        packet = {
            "schema_version": "au-e1-fa1-alignment-packet-v1",
            "study": "Attainable Unknowns API Pilot 0.1",
            "protocol_id": "FA1",
            "alignment_packet_id": tbid,
            "focal_unknown_anchor": source["focal_unknown_anchor"],
            "cluster_count": len(clusters),
            "clusters": clusters,
        }
        path = paths["generated"] / f"{tbid}.json"
        write_json(path, packet)
        meta = pmap[pid]
        model_key = "terra" if topic_number(meta["topic_packet_id"]) % 2 == 1 else "sonnet"
        packet_rows.append({
            "tiebreak_packet_id": tbid,
            "cluster_count": len(clusters),
            "path": rel(path),
            "sha256": sha256_file(path),
        })
        private_rows.append({
            "tiebreak_packet_id": tbid,
            "source_alignment_packet_id": pid,
            "model_key": model_key,
            "topic_packet_id": meta["topic_packet_id"],
            "cluster_refs": [c["cluster_ref"] for c in clusters],
        })

    index = {
        "schema_version": "au-e1-fa1-tiebreak-index-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "FA1",
        "bundle_id": bundle_id,
        "primary_freeze_commit": primary_freeze,
        "packet_count": len(packet_rows),
        "disputed_cluster_count": len(disagreements),
        "packets": packet_rows,
    }
    write_json(paths["index"], index)
    write_json(paths["private"], {
        "schema_version": "au-e1-fa1-tiebreak-private-key-v1",
        "bundle_id": bundle_id,
        "warning": "Do not provide this mapping or primary labels to third raters.",
        "packets": private_rows,
    })
    write_json(paths["record"], {
        "schema_version": "au-e1-fa1-tiebreak-preparation-v1",
        "bundle_id": bundle_id,
        "prepared_at_utc": utc_now(),
        "packet_bundle_commit": bundle["bundle_commit"],
        "primary_freeze_commit": primary_freeze,
        "primary_codes_sha256": sha256_file(primary_paths(bundle_id)["codes"]),
        "packet_count": len(packet_rows),
        "disputed_cluster_count": len(disagreements),
        "index_sha256": sha256_file(paths["index"]),
        "private_key_sha256": sha256_file(paths["private"]),
    })
    print(json.dumps({
        "status": "fa1_tiebreak_bundle_prepared",
        "bundle_id": bundle_id,
        "primary_freeze_commit": primary_freeze,
        "disputed_clusters": len(disagreements),
        "tiebreak_packets": len(packet_rows),
        "next_step": "freeze the generated tiebreak bundle in a founder-signed Git commit before third-rater requests",
    }, indent=2, sort_keys=True))


def verify_tiebreak_bundle(bundle_id: str, primary_commit: str, tiebreak_commit_ref: str) -> dict[str, Any]:
    paths = tiebreak_paths(bundle_id)
    for key in ("index", "private", "record"):
        if not paths[key].is_file():
            raise FileNotFoundError(paths[key])
    record = load_json(paths["record"])
    if record.get("bundle_id") != bundle_id:
        raise ValueError("Tiebreak preparation bundle mismatch")
    primary_resolved = verify_signed_commit(primary_commit, "FA1 primary coding freeze")
    if record.get("primary_freeze_commit") != primary_resolved:
        raise ValueError("Tiebreak preparation primary-freeze mismatch")
    commit = verify_signed_commit(tiebreak_commit_ref, "FA1 tiebreak packet freeze")
    if git("merge-base", "--is-ancestor", primary_resolved, commit).returncode != 0:
        raise ValueError("Primary freeze is not an ancestor of tiebreak packet freeze")
    index = load_json(paths["index"])
    private = load_json(paths["private"])
    required = [paths["index"], paths["private"], paths["record"]]
    for row in index.get("packets", []):
        path = ROOT / row["path"]
        if not path.is_file() or sha256_file(path) != row["sha256"]:
            raise ValueError(f"Tiebreak packet hash mismatch: {row.get('tiebreak_packet_id')}")
        packet = load_json(path)
        if packet.get("alignment_packet_id") != row.get("tiebreak_packet_id"):
            raise ValueError(f"Tiebreak packet identity mismatch: {row.get('tiebreak_packet_id')}")
        if packet.get("cluster_count") != row.get("cluster_count"):
            raise ValueError(f"Tiebreak packet cluster-count mismatch: {row.get('tiebreak_packet_id')}")
        required.append(path)
    for path in required:
        if not committed_blob_matches_worktree(commit, path):
            raise ValueError(f"Tiebreak bundle file differs from signed commit: {rel(path)}")
    if len(private.get("packets", [])) != int(index.get("packet_count", -1)):
        raise ValueError("Tiebreak private-key packet count mismatch")
    return {"commit": commit, "record": record, "index": index, "private": private, "paths": paths}


def build_tiebreak_tasks(tb: dict[str, Any]) -> list[dict[str, Any]]:
    private = {r["tiebreak_packet_id"]: r for r in tb["private"]["packets"]}
    tasks: list[dict[str, Any]] = []
    for row in tb["index"]["packets"]:
        tbid = row["tiebreak_packet_id"]
        meta = private[tbid]
        tasks.append({
            "task_id": f"{meta['model_key']}-{tbid}",
            "model_key": meta["model_key"],
            "tiebreak_packet_id": tbid,
            "packet_path": row["path"],
            "cluster_count": int(row["cluster_count"]),
        })
    return sorted(tasks, key=lambda x: x["task_id"])


def write_tiebreak_codes(bundle_id: str, tasks: list[dict[str, Any]], completed: dict[str, dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = []
    for task in sorted(tasks, key=lambda x: x["task_id"]):
        if task["task_id"] not in completed:
            continue
        rows.append({
            "schema_version": "au-e1-fa1-tiebreak-code-v1",
            "task_id": task["task_id"],
            "model_key": task["model_key"],
            "tiebreak_packet_id": task["tiebreak_packet_id"],
            "labels": completed[task["task_id"]]["labels"],
        })
    write_jsonl(tiebreak_paths(bundle_id)["codes"], rows)


def save_tiebreak_state(bundle_id: str, tb: dict[str, Any], tasks: list[dict[str, Any]], state: dict[str, Any], status: str) -> None:
    paths = tiebreak_paths(bundle_id)
    paths["results"].mkdir(parents=True, exist_ok=True)
    write_tiebreak_codes(bundle_id, tasks, state["completed"])
    write_json(paths["manifest"], {
        "schema_version": "au-e1-fa1-tiebreak-run-v1",
        "bundle_id": bundle_id,
        "tiebreak_packet_freeze_commit": tb["commit"],
        "primary_freeze_commit": tb["record"]["primary_freeze_commit"],
        "status": status,
        "updated_at_utc": utc_now(),
        "task_count": len(tasks),
        "completed_tasks": len(state["completed"]),
        "remaining_tasks": len(tasks) - len(state["completed"]),
        "exhausted_tasks": sorted(state["exhausted"]),
        "model_costs_usd": {k: round(v, 6) for k, v in state["model_costs"].items()},
        "attempts_sha256": sha256_file(paths["attempts"]) if paths["attempts"].exists() else None,
        "tiebreak_codes_sha256": sha256_file(paths["codes"]) if paths["codes"].exists() else None,
    })


def execute_tiebreak(bundle_id: str, bundle_commit: str, primary_commit: str, tiebreak_commit: str) -> None:
    load_env_file()
    bundle = verify_bundle(bundle_id, bundle_commit)
    verify_primary_freeze(bundle_id, bundle_commit, primary_commit)
    tb = verify_tiebreak_bundle(bundle_id, primary_commit, tiebreak_commit)
    tasks = build_tiebreak_tasks(tb)
    paths = tiebreak_paths(bundle_id)
    paths["results"].mkdir(parents=True, exist_ok=True)
    ensure_no_ambiguous_inflight(paths["inflight"])
    if not tasks:
        write_jsonl(paths["codes"], [])
        save_tiebreak_state(bundle_id, tb, tasks, {"completed": {}, "exhausted": set(), "model_costs": {k: 0.0 for k in MODEL_CONFIGS}}, "tiebreak_not_needed")
        print(json.dumps({"status": "tiebreak_not_needed", "tasks": 0}, indent=2))
        return

    attempts = read_jsonl(paths["attempts"])
    state = derive_state(attempts, tasks)
    clients: dict[str, Any] = {}
    blocked: set[str] = set()
    instructions = bundle["paths"]["instructions"].read_text(encoding="utf-8")

    for task in sorted(tasks, key=lambda x: (-x["cluster_count"], x["model_key"], x["task_id"])):
        attempts = read_jsonl(paths["attempts"])
        state = derive_state(attempts, tasks)
        mk = task["model_key"]
        if task["task_id"] in state["completed"] or task["task_id"] in state["exhausted"] or mk in blocked:
            continue
        if state["model_costs"][mk] >= float(MODEL_CONFIGS[mk]["stop_limit_usd"]):
            blocked.add(mk)
            continue
        if mk not in clients:
            cfg = MODEL_CONFIGS[mk]
            key = os.environ.get(cfg["api_key_env"])
            if not key:
                blocked.add(mk)
                continue
            clients[mk] = build_client(mk, key)
        packet = load_json(ROOT / task["packet_path"])
        completed, permanent = run_one(
            task, packet, clients[mk], instructions,
            state["attempt_counts"].get(task["task_id"], 0),
            paths["attempts"], paths["inflight"], "alignment_packet_id"
        )
        if permanent:
            blocked.add(mk)
        attempts = read_jsonl(paths["attempts"])
        state = derive_state(attempts, tasks)
        save_tiebreak_state(bundle_id, tb, tasks, state, "tiebreak_running")

    attempts = read_jsonl(paths["attempts"])
    state = derive_state(attempts, tasks)
    status = "tiebreak_complete" if len(state["completed"]) == len(tasks) else "tiebreak_incomplete"
    save_tiebreak_state(bundle_id, tb, tasks, state, status)
    print(json.dumps({
        "status": status,
        "completed_tasks": len(state["completed"]),
        "expected_tasks": len(tasks),
        "exhausted_tasks": sorted(state["exhausted"]),
        "blocked_models": sorted(blocked),
        "model_costs_usd": {k: round(v, 6) for k, v in state["model_costs"].items()},
    }, indent=2, sort_keys=True))


def validate_tiebreak(bundle_id: str, primary_commit: str, tiebreak_commit: str) -> dict[str, Any]:
    tb = verify_tiebreak_bundle(bundle_id, primary_commit, tiebreak_commit)
    tasks = build_tiebreak_tasks(tb)
    paths = tiebreak_paths(bundle_id)
    attempts = read_jsonl(paths["attempts"])
    state = derive_state(attempts, tasks)
    save_tiebreak_state(bundle_id, tb, tasks, state, "tiebreak_complete" if len(state["completed"]) == len(tasks) else "tiebreak_incomplete")
    return {
        "status": "complete" if len(state["completed"]) == len(tasks) else "incomplete",
        "completed_tasks": len(state["completed"]),
        "expected_tasks": len(tasks),
        "disputed_clusters": tb["index"].get("disputed_cluster_count"),
        "exhausted_tasks": sorted(state["exhausted"]),
        "inflight_exists": paths["inflight"].exists(),
    }


def final_paths(bundle_id: str) -> dict[str, Path]:
    base = CODING_ROOT / bundle_id / "final"
    return {
        "base": base,
        "alignment": base / "FINAL_ALIGNMENT.jsonl",
        "agreement": base / "AGREEMENT_SUMMARY.json",
        "record": base / "FINALIZATION_RECORD.json",
    }


def finalize(bundle_id: str, bundle_commit: str, primary_commit: str, tiebreak_commit: str) -> None:
    bundle = verify_bundle(bundle_id, bundle_commit)
    _, primary_rows = verify_primary_freeze(bundle_id, bundle_commit, primary_commit)
    tb_status = validate_tiebreak(bundle_id, primary_commit, tiebreak_commit)
    if tb_status["status"] != "complete" or tb_status["inflight_exists"]:
        raise ValueError("Tiebreak coding is not complete and clean")
    tb = verify_tiebreak_bundle(bundle_id, primary_commit, tiebreak_commit)
    label_maps = primary_label_maps(primary_rows)
    pmap = private_packet_map(bundle)
    tb_private = {r["tiebreak_packet_id"]: r for r in tb["private"]["packets"]}
    tb_code_rows = read_jsonl(tiebreak_paths(bundle_id)["codes"])
    tb_labels: dict[tuple[str, str], tuple[str, str]] = {}
    for row in tb_code_rows:
        meta = tb_private[row["tiebreak_packet_id"]]
        source_pid = meta["source_alignment_packet_id"]
        model_key = row["model_key"]
        for label in row["labels"]:
            key = (source_pid, label["cluster_ref"])
            if key in tb_labels:
                raise ValueError(f"Duplicate tiebreak label: {key}")
            tb_labels[key] = (model_key, label["code"])

    final_rows: list[dict[str, Any]] = []
    confusion = {a: {b: 0 for b in LABEL_CODES} for a in LABEL_CODES}
    agreements_by_code = {code: 0 for code in LABEL_CODES}
    primary_agree = 0
    disputed = 0

    for pid in sorted(pmap):
        meta = pmap[pid]
        for cluster in meta["clusters"]:
            cref = cluster["cluster_ref"]
            sol = label_maps["sol"][pid][cref]
            opus = label_maps["opus"][pid][cref]
            confusion[sol][opus] += 1
            third_model = None
            third = None
            if sol == opus:
                final = sol
                resolution = "primary_agreement"
                primary_agree += 1
                agreements_by_code[sol] += 1
            else:
                disputed += 1
                key = (pid, cref)
                if key not in tb_labels:
                    raise ValueError(f"Missing tiebreak label for {pid}/{cref}")
                third_model, third = tb_labels[key]
                if third == sol or third == opus:
                    final = third
                    resolution = "two_of_three_majority"
                else:
                    final = "I"
                    resolution = "three_way_split_to_indeterminate"
            final_rows.append({
                "schema_version": "au-e1-fa1-final-alignment-v1",
                "cluster_uid": cluster["source_cluster_uid"],
                "source_task_id": meta["source_task_id"],
                "source_cluster_id": cluster["source_cluster_id"],
                "alignment_packet_id": pid,
                "cluster_ref": cref,
                "sol_code": sol,
                "opus_code": opus,
                "tiebreak_model_key": third_model,
                "tiebreak_code": third,
                "final_code": final,
                "final_alignment": LABELS[final],
                "resolution": resolution,
            })

    if len(final_rows) != EXPECTED_CLUSTERS or len({r["cluster_uid"] for r in final_rows}) != EXPECTED_CLUSTERS:
        raise ValueError("Final FA1 cluster coverage mismatch")
    if disputed != int(tb["index"].get("disputed_cluster_count", -1)):
        raise ValueError("Primary disagreement count differs from frozen tiebreak bundle")

    paths = final_paths(bundle_id)
    if paths["base"].exists():
        raise FileExistsError(f"Refusing to overwrite existing final FA1 directory: {paths['base']}")
    paths["base"].mkdir(parents=True)
    write_jsonl(paths["alignment"], sorted(final_rows, key=lambda r: r["cluster_uid"]))
    write_json(paths["agreement"], {
        "schema_version": "au-e1-fa1-agreement-summary-v1",
        "bundle_id": bundle_id,
        "cluster_instances": EXPECTED_CLUSTERS,
        "primary_exact_agreement_count": primary_agree,
        "primary_exact_agreement_rate": primary_agree / EXPECTED_CLUSTERS,
        "primary_disagreement_count": disputed,
        "primary_disagreement_rate": disputed / EXPECTED_CLUSTERS,
        "primary_agreement_counts_by_code": agreements_by_code,
        "sol_by_opus_confusion": confusion,
        "tiebreak_clusters": len(tb_labels),
    })
    write_json(paths["record"], {
        "schema_version": "au-e1-fa1-finalization-record-v1",
        "bundle_id": bundle_id,
        "finalized_at_utc": utc_now(),
        "packet_bundle_commit": bundle["bundle_commit"],
        "primary_freeze_commit": resolve_commit(primary_commit),
        "tiebreak_packet_freeze_commit": tb["commit"],
        "final_alignment_rows": len(final_rows),
        "final_alignment_sha256": sha256_file(paths["alignment"]),
        "agreement_summary_sha256": sha256_file(paths["agreement"]),
        "j1_metadata_joined_during_alignment": False,
    })
    print(json.dumps({
        "status": "fa1_finalized",
        "final_alignment_rows": len(final_rows),
        "primary_exact_agreement_count": primary_agree,
        "primary_disagreement_count": disputed,
        "output_dir": rel(paths["base"]),
    }, indent=2, sort_keys=True))


def synthetic_test(model_key: str) -> None:
    load_env_file()
    cfg = MODEL_CONFIGS[model_key]
    key = os.environ.get(cfg["api_key_env"])
    if not key:
        raise SystemExit(f"Missing environment variable: {cfg['api_key_env']}")
    client = build_client(model_key, key)
    text, raw = call_provider(model_key, client, INSTRUCTIONS_SOURCE.read_text(encoding="utf-8"), SYNTHETIC_PACKET, "alignment_packet_id")
    parsed = validate_alignment_output(text, SYNTHETIC_PACKET, "alignment_packet_id")
    print(json.dumps({
        "status": "fa1_synthetic_test_passed",
        "model_key": model_key,
        "model": cfg["model"],
        "cluster_count": SYNTHETIC_PACKET["cluster_count"],
        "labels_returned": len(parsed["labels"]),
        "usage": usage_record(raw, model_key),
    }, indent=2, sort_keys=True))


def self_test() -> None:
    valid = {"alignment_packet_id": "X", "cluster_count": 4, "clusters": [{"cluster_ref": f"K{i:03d}"} for i in range(1, 5)]}
    parsed = validate_alignment_output('{"alignment_packet_id":"X","alignment_code":"FAPI"}', valid, "alignment_packet_id")
    if [x["label"] for x in parsed["labels"]] != ["focal", "adjacent", "peripheral", "indeterminate"]:
        raise AssertionError("Label decoding failed")
    try:
        validate_alignment_output('{"alignment_packet_id":"X","alignment_code":"FAP"}', valid, "alignment_packet_id")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid alignment-code length was accepted")
    print(json.dumps({"status": "fa1_runner_self_test_passed"}, indent=2))


def status_primary(bundle_id: str, bundle_commit: str) -> None:
    pf = primary_preflight(bundle_id, bundle_commit)
    tasks, state = pf["tasks"], pf["state"]
    by_model = {}
    for mk in ("sol", "opus"):
        model_tasks = [t for t in tasks if t["model_key"] == mk]
        done = sum(t["task_id"] in state["completed"] for t in model_tasks)
        by_model[mk] = {"completed": done, "total": len(model_tasks), "remaining": len(model_tasks) - done, "cost_usd": round(state["model_costs"][mk], 6)}
    print(json.dumps({"completed_tasks": len(state["completed"]), "total_tasks": len(tasks), "by_model": by_model, "exhausted_tasks": sorted(state["exhausted"])}, indent=2, sort_keys=True))


def status_tiebreak(bundle_id: str, primary_commit: str, tiebreak_commit: str) -> None:
    result = validate_tiebreak(bundle_id, primary_commit, tiebreak_commit)
    print(json.dumps(result, indent=2, sort_keys=True))


def resolve_inflight(phase: str, bundle_id: str) -> None:
    paths = primary_paths(bundle_id) if phase == "primary" else tiebreak_paths(bundle_id)
    marker_path = paths["inflight"]
    attempts_path = paths["attempts"]
    if not marker_path.exists():
        raise SystemExit("No INFLIGHT.json exists for the selected phase.")
    marker = load_json(marker_path)
    row = {
        "schema_version": "au-e1-fa1-attempt-v1",
        "task_id": marker["task_id"],
        "model_key": marker["model_key"],
        "provider": MODEL_CONFIGS[marker["model_key"]]["provider"],
        "model_requested": MODEL_CONFIGS[marker["model_key"]]["model"],
        "attempt_index": marker["attempt_index"],
        "started_at": marker["started_at"],
        "finished_at": utc_now(),
        "request_sha256": marker["request_sha256"],
        "status": "orphaned_dispatch",
        "usage": {"input_tokens": None, "output_tokens": None, "conservative_cost_usd": None},
        "note": (
            "Process ended with this request in flight. Provider-side completion is unknown "
            "and no local semantic result exists. The orphan is preserved before retry."
        ),
    }
    append_jsonl(attempts_path, row)
    clear_marker(marker_path)
    print(json.dumps({"status": "inflight_preserved_for_retry", "phase": phase, "task_id": marker["task_id"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("self-test", help="Run local validation tests; no API calls")

    syn = sub.add_parser("synthetic-test", help="Run a synthetic API compatibility test")
    syn.add_argument("--model", required=True, choices=sorted(MODEL_CONFIGS))

    pre = sub.add_parser("preflight", help="Verify a signed generated packet bundle; no API calls")
    pre.add_argument("--bundle-id", required=True)
    pre.add_argument("--bundle-commit", required=True)

    can = sub.add_parser("primary-canary", help="Run/resume one largest-packet canary per primary rater")
    can.add_argument("--bundle-id", required=True)
    can.add_argument("--bundle-commit", required=True)

    pri = sub.add_parser("primary", help="Run/resume all Sol and Opus primary coding")
    pri.add_argument("--bundle-id", required=True)
    pri.add_argument("--bundle-commit", required=True)

    ps = sub.add_parser("primary-status", help="Read-only primary progress summary")
    ps.add_argument("--bundle-id", required=True)
    ps.add_argument("--bundle-commit", required=True)

    pv = sub.add_parser("primary-validate", help="Validate/rebuild primary code output")
    pv.add_argument("--bundle-id", required=True)
    pv.add_argument("--bundle-commit", required=True)

    prep = sub.add_parser("prepare-tiebreak", help="Build blinded tiebreak packets from frozen primary disagreements")
    prep.add_argument("--bundle-id", required=True)
    prep.add_argument("--bundle-commit", required=True)
    prep.add_argument("--primary-freeze-commit", required=True)

    tb = sub.add_parser("tiebreak", help="Run/resume Terra/Sonnet blinded tiebreak coding")
    tb.add_argument("--bundle-id", required=True)
    tb.add_argument("--bundle-commit", required=True)
    tb.add_argument("--primary-freeze-commit", required=True)
    tb.add_argument("--tiebreak-bundle-commit", required=True)

    ts = sub.add_parser("tiebreak-status", help="Validate/read tiebreak progress")
    ts.add_argument("--bundle-id", required=True)
    ts.add_argument("--primary-freeze-commit", required=True)
    ts.add_argument("--tiebreak-bundle-commit", required=True)

    fin = sub.add_parser("finalize", help="Deterministically reconcile primary and tiebreak labels")
    fin.add_argument("--bundle-id", required=True)
    fin.add_argument("--bundle-commit", required=True)
    fin.add_argument("--primary-freeze-commit", required=True)
    fin.add_argument("--tiebreak-bundle-commit", required=True)

    res = sub.add_parser("resolve-inflight", help="Preserve an ambiguous interrupted dispatch before retry")
    res.add_argument("--phase", required=True, choices=["primary", "tiebreak"])
    res.add_argument("--bundle-id", required=True)

    args = parser.parse_args()
    if args.command == "self-test":
        self_test()
    elif args.command == "synthetic-test":
        synthetic_test(args.model)
    elif args.command == "preflight":
        print(json.dumps(primary_preflight(args.bundle_id, args.bundle_commit)["result"], indent=2, sort_keys=True))
    elif args.command == "primary-canary":
        execute_primary("canary", args.bundle_id, args.bundle_commit)
    elif args.command == "primary":
        execute_primary("primary", args.bundle_id, args.bundle_commit)
    elif args.command == "primary-status":
        status_primary(args.bundle_id, args.bundle_commit)
    elif args.command == "primary-validate":
        print(json.dumps(validate_primary(args.bundle_id, args.bundle_commit, write_outputs=True), indent=2, sort_keys=True))
    elif args.command == "prepare-tiebreak":
        prepare_tiebreak(args.bundle_id, args.bundle_commit, args.primary_freeze_commit)
    elif args.command == "tiebreak":
        execute_tiebreak(args.bundle_id, args.bundle_commit, args.primary_freeze_commit, args.tiebreak_bundle_commit)
    elif args.command == "tiebreak-status":
        status_tiebreak(args.bundle_id, args.primary_freeze_commit, args.tiebreak_bundle_commit)
    elif args.command == "finalize":
        finalize(args.bundle_id, args.bundle_commit, args.primary_freeze_commit, args.tiebreak_bundle_commit)
    elif args.command == "resolve-inflight":
        resolve_inflight(args.phase, args.bundle_id)
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
