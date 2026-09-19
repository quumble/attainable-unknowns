#!/usr/bin/env python3
"""Run E1A Stage 1 dual canonical-target representations (Sol / Opus).

The runner is intentionally conservative:
- verifies the frozen E1A and Stage 1 corpus checkpoints;
- sends exactly one blinded card per request;
- carries no conversational state across cards;
- preserves every provider response or technical failure;
- never retries a structurally valid semantic output;
- stops on the first API error or structurally invalid returned output;
- supports transparent resume through an append-only attempt log;
- detects ambiguous interrupted in-flight calls instead of silently duplicating them.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
E1_DIR = ROOT / "api-study" / "exploratory"

E1A_PROTOCOL = E1_DIR / "API_PILOT_0.1_TARGET_CLUSTERING_E1A.md"
RUNNER_PROCEDURE = E1_DIR / "E1_STAGE1_RUNNER_PROCEDURE.md"

PACKET_ID = "AU-E1-S1-cad71b8ce8fe0866"
PACKET_DIR = E1_DIR / "e1" / "generated" / PACKET_ID
MASTER_PACKET = PACKET_DIR / "blinded" / "STAGE1_MASTER_PACKET.json"
INSTRUCTIONS = PACKET_DIR / "blinded" / "STAGE1_CANONICALIZATION_INSTRUCTIONS.md"
INPUT_MANIFEST = PACKET_DIR / "blinded" / "STAGE1_INPUT_MANIFEST.json"

OUTPUT_ROOT = E1_DIR / "e1" / "stage1_outputs" / PACKET_ID

EXPECTED_E1A_COMMIT = "084245d39e90eb98d76c98e22cc4be88d6c9be2f"
EXPECTED_CORPUS_COMMIT = "15dbac07a615938464b03f5fa3e2539aed3ef8c1"

EXPECTED_MASTER_SHA256 = "841143587590d14e5cfc5ebbe00261be664cf5a7021935973a0ddf62bc9ae966"
EXPECTED_INSTRUCTIONS_SHA256 = "f3688a2638f410a0e0071b6916131b371b9de470a82df6455d20c7f1e2b608b0"
EXPECTED_MANIFEST_SHA256 = "24c75d46699c13dc1fedb757ec2320d07b4d46c7a9fa04ceca88463e6295f8af"
EXPECTED_CARDS = 1984

MAX_ATTEMPTS_PER_CARD = 3

MODEL_CONFIGS: dict[str, dict[str, Any]] = {
    "sol": {
        "provider": "openai",
        "model": "gpt-5.6-sol",
        "api_key_env": "OPENAI_API_KEY",
        "reasoning_effort": "none",
        "max_output_tokens": 160,
        "input_per_million": 4.00,
        "output_per_million": 20.00,
        "stop_limit_usd": 15.00,
    },
    "opus": {
        "provider": "anthropic",
        "model": "claude-opus-5",
        "api_key_env": "ANTHROPIC_API_KEY",
        "thinking": {"type": "disabled"},
        "max_output_tokens": 160,
        "input_per_million": 5.00,
        "output_per_million": 25.00,
        "stop_limit_usd": 20.00,
    },
}

SYNTHETIC_CARD = {
    "card_id": "SYNTHETIC-E1-0001",
    "passage": (
        "A field notebook records the date, location, and weather for each observation. "
        "The entries are later compared to see whether similar conditions recur."
    ),
    "question": "Which weather condition recurred most often across the recorded observations?",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


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


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = canonical_json(value) + "\n"
    with path.open("a", encoding="utf-8", newline="\n", buffering=1) as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


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


def load_env_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def verify_frozen_inputs() -> list[dict[str, str]]:
    expected = (
        (MASTER_PACKET, EXPECTED_MASTER_SHA256),
        (INSTRUCTIONS, EXPECTED_INSTRUCTIONS_SHA256),
        (INPUT_MANIFEST, EXPECTED_MANIFEST_SHA256),
    )
    for path, digest in expected:
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256_file(path)
        if observed != digest:
            raise ValueError(
                f"Frozen input hash mismatch for {rel(path)}: expected {digest}, observed {observed}"
            )
        if not committed_blob_matches_worktree(EXPECTED_CORPUS_COMMIT, path):
            raise ValueError(
                f"Working frozen input differs from corpus checkpoint: {rel(path)}"
            )

    packet = load_json(MASTER_PACKET)
    if packet.get("packet_id") != PACKET_ID:
        raise ValueError("Stage 1 packet ID mismatch")
    cards = packet.get("cards")
    if not isinstance(cards, list) or len(cards) != EXPECTED_CARDS:
        raise ValueError(f"Expected {EXPECTED_CARDS} cards")

    seen: set[str] = set()
    cleaned: list[dict[str, str]] = []
    for index, card in enumerate(cards, start=1):
        if not isinstance(card, dict):
            raise ValueError(f"Card {index} is not an object")
        if set(card) != {"card_id", "passage", "question"}:
            raise ValueError(f"Card {index} contains unexpected fields: {sorted(card)}")
        card_id = card["card_id"]
        passage = card["passage"]
        question = card["question"]
        if not all(isinstance(x, str) and x for x in (card_id, passage, question)):
            raise ValueError(f"Card {index} has an empty/non-string visible field")
        if card_id in seen:
            raise ValueError(f"Duplicate card_id: {card_id}")
        seen.add(card_id)
        cleaned.append(
            {"card_id": card_id, "passage": passage, "question": question}
        )
    return cleaned


def verify_checkpoints(implementation_ref: str | None = None) -> dict[str, str]:
    e1a = verify_signed_commit(EXPECTED_E1A_COMMIT, "E1A commit")
    corpus = verify_signed_commit(EXPECTED_CORPUS_COMMIT, "Stage 1 corpus commit")

    if e1a != EXPECTED_E1A_COMMIT:
        raise ValueError("Resolved E1A commit differs from frozen E1A SHA")
    if corpus != EXPECTED_CORPUS_COMMIT:
        raise ValueError("Resolved corpus commit differs from frozen corpus SHA")

    if not committed_blob_matches_worktree(e1a, E1A_PROTOCOL):
        raise ValueError("Working E1A protocol differs from signed E1A commit")

    result = {"e1a_commit": e1a, "corpus_commit": corpus}

    if implementation_ref is not None:
        impl = verify_signed_commit(implementation_ref, "Stage 1 runner implementation commit")
        for ancestor, name in ((e1a, "E1A"), (corpus, "corpus checkpoint")):
            if git("merge-base", "--is-ancestor", ancestor, impl).returncode != 0:
                raise ValueError(f"{name} {ancestor} is not an ancestor of implementation {impl}")
        for path in (Path(__file__).resolve(), RUNNER_PROCEDURE):
            if not path.is_file():
                raise FileNotFoundError(path)
            if not committed_blob_matches_worktree(impl, path):
                raise ValueError(
                    f"Working implementation file differs from signed commit {impl}: {rel(path)}"
                )
        result["implementation_commit"] = impl

    return result


def rough_tokens(text: str) -> int:
    return max(1, (len(text) + 2) // 3)


def budget_estimate(cards: list[dict[str, str]], representation: str) -> dict[str, Any]:
    cfg = MODEL_CONFIGS[representation]
    system = INSTRUCTIONS.read_text(encoding="utf-8")
    input_tokens = sum(
        rough_tokens(system + "\n" + canonical_json(card))
        for card in cards
    )
    output_tokens = len(cards) * int(cfg["max_output_tokens"])
    cost = (
        input_tokens / 1_000_000 * float(cfg["input_per_million"])
        + output_tokens / 1_000_000 * float(cfg["output_per_million"])
    )
    return {
        "planned_cards": len(cards),
        "conservative_input_tokens": input_tokens,
        "conservative_output_tokens": output_tokens,
        "conservative_cost_usd": round(cost, 4),
        "stop_limit_usd": float(cfg["stop_limit_usd"]),
        "passes": cost <= float(cfg["stop_limit_usd"]),
    }


def build_client(representation: str, api_key: str):
    cfg = MODEL_CONFIGS[representation]
    if cfg["provider"] == "openai":
        from openai import OpenAI
        return OpenAI(api_key=api_key, max_retries=0)
    if cfg["provider"] == "anthropic":
        import anthropic
        return anthropic.Anthropic(api_key=api_key, max_retries=0)
    raise ValueError(cfg["provider"])


def call_provider(
    representation: str,
    client: Any,
    system: str,
    card: dict[str, str],
) -> tuple[str, dict[str, Any]]:
    cfg = MODEL_CONFIGS[representation]
    payload = canonical_json(card)

    if cfg["provider"] == "openai":
        response = client.responses.create(
            model=cfg["model"],
            instructions=system,
            input=payload,
            max_output_tokens=int(cfg["max_output_tokens"]),
            reasoning={"effort": cfg["reasoning_effort"]},
        )
        return response.output_text, response.model_dump(mode="json")

    if cfg["provider"] == "anthropic":
        response = client.messages.create(
            model=cfg["model"],
            system=system,
            messages=[{"role": "user", "content": payload}],
            max_tokens=int(cfg["max_output_tokens"]),
            thinking=cfg["thinking"],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        return text, response.model_dump(mode="json")

    raise ValueError(cfg["provider"])


def parse_canonical_output(raw_text: str, expected_card_id: str) -> dict[str, Any]:
    text = raw_text.strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Response is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("Response JSON is not an object")
    if set(value) != {"card_id", "canonical_target", "uncertain"}:
        raise ValueError(f"Response keys are not exact: {sorted(value)}")
    if value["card_id"] != expected_card_id:
        raise ValueError(
            f"card_id mismatch: expected {expected_card_id}, got {value['card_id']!r}"
        )
    if not isinstance(value["canonical_target"], str) or not value["canonical_target"].strip():
        raise ValueError("canonical_target must be a nonempty string")
    if not isinstance(value["uncertain"], bool):
        raise ValueError("uncertain must be a JSON boolean")
    return {
        "card_id": expected_card_id,
        "canonical_target": value["canonical_target"].strip(),
        "uncertain": value["uncertain"],
    }


def extract_usage(raw: dict[str, Any], representation: str) -> dict[str, Any]:
    cfg = MODEL_CONFIGS[representation]
    usage = raw.get("usage") or {}
    inp = usage.get("input_tokens")
    out = usage.get("output_tokens")
    result: dict[str, Any] = {
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


def run_dir(representation: str) -> Path:
    return OUTPUT_ROOT / representation


def paths_for(representation: str) -> dict[str, Path]:
    base = run_dir(representation)
    return {
        "base": base,
        "attempts": base / "ATTEMPTS.jsonl",
        "targets": base / "CANONICAL_TARGETS.jsonl",
        "manifest": base / "RUN_MANIFEST.json",
        "inflight": base / "INFLIGHT.json",
    }


def read_attempts(path: Path) -> list[dict[str, Any]]:
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
                raise ValueError(f"Corrupt attempt log line {line_number}") from exc
            rows.append(row)
    return rows


def derive_state(
    attempts: list[dict[str, Any]],
    cards_by_id: dict[str, dict[str, str]],
) -> tuple[dict[str, dict[str, Any]], dict[str, int], float]:
    completed: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {}
    cumulative_cost = 0.0

    for row in attempts:
        card_id = row.get("card_id")
        if card_id not in cards_by_id:
            raise ValueError(f"Attempt log contains unknown card_id: {card_id}")
        counts[card_id] = counts.get(card_id, 0) + 1
        c = row.get("usage", {}).get("conservative_cost_usd")
        if isinstance(c, (int, float)):
            cumulative_cost += float(c)
        if row.get("status") == "valid":
            parsed = row.get("parsed")
            if not isinstance(parsed, dict):
                raise ValueError(f"Valid attempt lacks parsed object: {card_id}")
            if card_id in completed:
                raise ValueError(f"More than one valid semantic output exists for {card_id}")
            completed[card_id] = parsed
    return completed, counts, cumulative_cost


def write_targets(
    path: Path,
    cards: list[dict[str, str]],
    completed: dict[str, dict[str, Any]],
    representation: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for card in cards:
            card_id = card["card_id"]
            if card_id not in completed:
                continue
            out = {
                "card_id": card_id,
                "canonical_target": completed[card_id]["canonical_target"],
                "uncertain": completed[card_id]["uncertain"],
                "representation": representation,
            }
            handle.write(canonical_json(out) + "\n")


def package_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for pkg in ("openai", "anthropic"):
        try:
            out[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            pass
    return out


def manifest_base(
    representation: str,
    checkpoints: dict[str, str],
    budget: dict[str, Any],
) -> dict[str, Any]:
    cfg = MODEL_CONFIGS[representation]
    return {
        "schema_version": "au-e1a-stage1-run-v1",
        "study": "Attainable Unknowns API Pilot 0.1",
        "protocol_id": "E1",
        "amendment_id": "E1A",
        "packet_id": PACKET_ID,
        "representation": representation,
        "provider": cfg["provider"],
        "model_requested": cfg["model"],
        "model_config_without_secret": cfg,
        "e1a_commit": checkpoints["e1a_commit"],
        "corpus_commit": checkpoints["corpus_commit"],
        "implementation_commit": checkpoints.get("implementation_commit"),
        "runner_path": rel(Path(__file__).resolve()),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "procedure_path": rel(RUNNER_PROCEDURE),
        "procedure_sha256": sha256_file(RUNNER_PROCEDURE),
        "master_packet_path": rel(MASTER_PACKET),
        "master_packet_sha256": sha256_file(MASTER_PACKET),
        "instructions_path": rel(INSTRUCTIONS),
        "instructions_sha256": sha256_file(INSTRUCTIONS),
        "input_manifest_path": rel(INPUT_MANIFEST),
        "input_manifest_sha256": sha256_file(INPUT_MANIFEST),
        "budget_preflight": budget,
        "python": sys.version,
        "platform": platform.platform(),
        "packages": package_versions(),
        "pricing_snapshot": {
            "date": "2026-09-19",
            "currency": "USD",
            "units": "per_million_tokens",
            "note": "Conservative estimate ignores any provider cache discounts.",
        },
        "max_attempts_per_card": MAX_ATTEMPTS_PER_CARD,
    }


def write_manifest(
    representation: str,
    checkpoints: dict[str, str],
    budget: dict[str, Any],
    attempts: list[dict[str, Any]],
    completed: dict[str, dict[str, Any]],
    cumulative_cost: float,
    status: str,
    started_at: str | None = None,
    detail: str | None = None,
) -> None:
    p = paths_for(representation)
    base = manifest_base(representation, checkpoints, budget)
    existing = load_json(p["manifest"]) if p["manifest"].exists() else {}
    doc = {
        **base,
        "started_at": existing.get("started_at") or started_at or utc_now(),
        "updated_at": utc_now(),
        "status": status,
        "attempt_records": len(attempts),
        "valid_cards": len(completed),
        "remaining_cards": EXPECTED_CARDS - len(completed),
        "conservative_observed_cost_usd": round(cumulative_cost, 6),
        "attempts_sha256": sha256_file(p["attempts"]) if p["attempts"].exists() else None,
        "targets_sha256": sha256_file(p["targets"]) if p["targets"].exists() else None,
        "detail": detail,
    }
    if status == "complete":
        doc["finished_at"] = utc_now()
    write_json(p["manifest"], doc)


def preflight(representation: str, implementation_commit: str | None) -> dict[str, Any]:
    checkpoints = verify_checkpoints(implementation_commit)
    cards = verify_frozen_inputs()
    budget = budget_estimate(cards, representation)
    if not budget["passes"]:
        raise RuntimeError(
            f"Conservative budget exceeds stop limit for {representation}: {budget}"
        )

    p = paths_for(representation)
    attempts = read_attempts(p["attempts"])
    cards_by_id = {card["card_id"]: card for card in cards}
    completed, counts, cumulative_cost = derive_state(attempts, cards_by_id)

    over_attempt = [
        card_id for card_id, count in counts.items() if count > MAX_ATTEMPTS_PER_CARD
    ]
    if over_attempt:
        raise ValueError(f"Attempt ceiling already exceeded: {over_attempt[:5]}")

    return {
        "representation": representation,
        "model": MODEL_CONFIGS[representation]["model"],
        "provider": MODEL_CONFIGS[representation]["provider"],
        "cards": cards,
        "checkpoints": checkpoints,
        "budget": budget,
        "completed": completed,
        "attempt_counts": counts,
        "cumulative_cost": cumulative_cost,
        "inflight_exists": p["inflight"].exists(),
        "output_directory": rel(p["base"]),
    }


def synthetic_test(representation: str) -> None:
    load_env_file()
    cfg = MODEL_CONFIGS[representation]
    api_key = os.environ.get(cfg["api_key_env"])
    if not api_key:
        raise SystemExit(f"Missing environment variable: {cfg['api_key_env']}")
    system = INSTRUCTIONS.read_text(encoding="utf-8")
    client = build_client(representation, api_key)
    raw_text, raw = call_provider(representation, client, system, SYNTHETIC_CARD)
    parsed = parse_canonical_output(raw_text, SYNTHETIC_CARD["card_id"])
    usage = extract_usage(raw, representation)
    print(
        json.dumps(
            {
                "status": "synthetic_test_passed",
                "representation": representation,
                "model": cfg["model"],
                "raw_text": raw_text,
                "parsed": parsed,
                "usage": usage,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def resolve_inflight(representation: str, action: str) -> None:
    p = paths_for(representation)
    if not p["inflight"].exists():
        raise SystemExit("No INFLIGHT.json exists; nothing to resolve.")
    if action != "retry":
        raise ValueError(action)

    marker = load_json(p["inflight"])
    record = {
        "schema_version": "au-e1a-stage1-attempt-v1",
        "representation": representation,
        "provider": MODEL_CONFIGS[representation]["provider"],
        "model_requested": MODEL_CONFIGS[representation]["model"],
        "card_id": marker["card_id"],
        "attempt_index": marker["attempt_index"],
        "status": "orphaned_dispatch",
        "started_at": marker["started_at"],
        "finished_at": utc_now(),
        "request_sha256": marker["request_sha256"],
        "note": (
            "A prior process ended while this request was in flight, so provider-side "
            "completion is unknown and no local semantic output is available. The orphan "
            "is preserved and the card may be retried under the frozen attempt ceiling."
        ),
        "usage": {
            "input_tokens": None,
            "output_tokens": None,
            "conservative_cost_usd": None,
        },
    }
    append_jsonl(p["attempts"], record)
    p["inflight"].unlink()
    print(json.dumps({"status": "inflight_resolved_for_retry", "card_id": marker["card_id"]}, indent=2))


def run_real(representation: str, implementation_commit: str) -> None:
    load_env_file()
    state = preflight(representation, implementation_commit)
    p = paths_for(representation)

    if state["inflight_exists"]:
        raise SystemExit(
            f"{rel(p['inflight'])} exists from an interrupted request. "
            f"Do not silently repeat it. Run resolve-inflight --representation {representation} "
            "--action retry, inspect the preserved record, then resume."
        )

    cfg = MODEL_CONFIGS[representation]
    api_key = os.environ.get(cfg["api_key_env"])
    if not api_key:
        raise SystemExit(f"Missing environment variable: {cfg['api_key_env']}")

    cards: list[dict[str, str]] = state["cards"]
    cards_by_id = {card["card_id"]: card for card in cards}
    checkpoints = state["checkpoints"]
    budget = state["budget"]
    system = INSTRUCTIONS.read_text(encoding="utf-8")
    client = build_client(representation, api_key)

    started = utc_now()

    while True:
        attempts = read_attempts(p["attempts"])
        completed, counts, cumulative_cost = derive_state(attempts, cards_by_id)
        write_targets(p["targets"], cards, completed, representation)

        if len(completed) == EXPECTED_CARDS:
            write_manifest(
                representation, checkpoints, budget, attempts, completed,
                cumulative_cost, "complete", started_at=started
            )
            print(
                json.dumps(
                    {
                        "status": "complete",
                        "representation": representation,
                        "valid_cards": len(completed),
                        "attempt_records": len(attempts),
                        "conservative_observed_cost_usd": round(cumulative_cost, 6),
                        "targets": rel(p["targets"]),
                        "manifest": rel(p["manifest"]),
                    },
                    indent=2,
                )
            )
            return

        next_card = next(card for card in cards if card["card_id"] not in completed)
        card_id = next_card["card_id"]
        attempt_index = counts.get(card_id, 0) + 1
        if attempt_index > MAX_ATTEMPTS_PER_CARD:
            write_manifest(
                representation, checkpoints, budget, attempts, completed,
                cumulative_cost, "blocked_attempt_ceiling", started_at=started,
                detail=f"{card_id} exhausted {MAX_ATTEMPTS_PER_CARD} preserved attempts without a valid output.",
            )
            raise SystemExit(
                f"{card_id} exhausted the frozen attempt ceiling. Stop; do not silently retry."
            )

        if cumulative_cost >= float(cfg["stop_limit_usd"]):
            write_manifest(
                representation, checkpoints, budget, attempts, completed,
                cumulative_cost, "stopped_budget", started_at=started,
                detail="Observed conservative token-cost estimate reached stop limit.",
            )
            raise SystemExit("Observed conservative cost estimate reached stop limit.")

        request_payload = canonical_json(next_card)
        request_sha = sha256_text(system + "\n" + request_payload)
        marker = {
            "representation": representation,
            "card_id": card_id,
            "attempt_index": attempt_index,
            "started_at": utc_now(),
            "request_sha256": request_sha,
        }
        write_json(p["inflight"], marker)

        before = time.monotonic()
        base = {
            "schema_version": "au-e1a-stage1-attempt-v1",
            "representation": representation,
            "provider": cfg["provider"],
            "model_requested": cfg["model"],
            "card_id": card_id,
            "attempt_index": attempt_index,
            "started_at": marker["started_at"],
            "request_sha256": request_sha,
            "visible_card": next_card,
        }

        try:
            raw_text, raw = call_provider(representation, client, system, next_card)
            usage = extract_usage(raw, representation)
            try:
                parsed = parse_canonical_output(raw_text, card_id)
            except Exception as exc:
                record = {
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
                append_jsonl(p["attempts"], record)
                p["inflight"].unlink(missing_ok=True)

                attempts = read_attempts(p["attempts"])
                completed, _, cumulative_cost = derive_state(attempts, cards_by_id)
                write_targets(p["targets"], cards, completed, representation)
                write_manifest(
                    representation, checkpoints, budget, attempts, completed,
                    cumulative_cost, "aborted_invalid_output", started_at=started,
                    detail=f"Structurally invalid returned output for {card_id}; preserved and stopped.",
                )
                raise SystemExit(
                    f"Structurally invalid output for {card_id}. Preserved. "
                    "No semantic judgment was made; inspect before resuming."
                )

            record = {
                **base,
                "status": "valid",
                "finished_at": utc_now(),
                "elapsed_seconds": round(time.monotonic() - before, 6),
                "raw_text": raw_text,
                "parsed": parsed,
                "usage": usage,
                "raw_provider_response": raw,
            }
            append_jsonl(p["attempts"], record)
            p["inflight"].unlink(missing_ok=True)

        except SystemExit:
            raise
        except BaseException as exc:
            record = {
                **base,
                "status": "api_error",
                "finished_at": utc_now(),
                "elapsed_seconds": round(time.monotonic() - before, 6),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "usage": {
                    "input_tokens": None,
                    "output_tokens": None,
                    "conservative_cost_usd": None,
                },
            }
            append_jsonl(p["attempts"], record)
            p["inflight"].unlink(missing_ok=True)

            attempts = read_attempts(p["attempts"])
            completed, _, cumulative_cost = derive_state(attempts, cards_by_id)
            write_targets(p["targets"], cards, completed, representation)
            write_manifest(
                representation, checkpoints, budget, attempts, completed,
                cumulative_cost, "aborted_api_error", started_at=started,
                detail=f"API error on {card_id}; preserved and stopped.",
            )
            raise


def validate(representation: str, implementation_commit: str | None) -> None:
    state = preflight(representation, implementation_commit)
    cards = state["cards"]
    p = paths_for(representation)
    attempts = read_attempts(p["attempts"])
    completed, counts, cost = derive_state(
        attempts, {card["card_id"]: card for card in cards}
    )
    write_targets(p["targets"], cards, completed, representation)

    status = "complete" if len(completed) == EXPECTED_CARDS else "incomplete"
    result = {
        "status": status,
        "representation": representation,
        "model": MODEL_CONFIGS[representation]["model"],
        "expected_cards": EXPECTED_CARDS,
        "valid_cards": len(completed),
        "remaining_cards": EXPECTED_CARDS - len(completed),
        "attempt_records": len(attempts),
        "cards_with_more_than_one_attempt": sum(v > 1 for v in counts.values()),
        "maximum_attempts_for_any_card": max(counts.values(), default=0),
        "uncertain_true": sum(bool(v["uncertain"]) for v in completed.values()),
        "conservative_observed_cost_usd": round(cost, 6),
        "attempts_sha256": sha256_file(p["attempts"]) if p["attempts"].exists() else None,
        "targets_sha256": sha256_file(p["targets"]) if p["targets"].exists() else None,
        "inflight_exists": p["inflight"].exists(),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight", help="Verify frozen inputs/checkpoints and estimate cost; no API calls")
    pre.add_argument("--representation", required=True, choices=sorted(MODEL_CONFIGS))
    pre.add_argument("--implementation-commit")

    syn = sub.add_parser("synthetic-test", help="Send one synthetic fixture card; no study card is used")
    syn.add_argument("--representation", required=True, choices=sorted(MODEL_CONFIGS))

    run = sub.add_parser("run", help="Run/resume one real Stage 1 representation")
    run.add_argument("--representation", required=True, choices=sorted(MODEL_CONFIGS))
    run.add_argument("--implementation-commit", required=True)

    val = sub.add_parser("validate", help="Validate/rebuild one representation from the append-only attempt log")
    val.add_argument("--representation", required=True, choices=sorted(MODEL_CONFIGS))
    val.add_argument("--implementation-commit")

    res = sub.add_parser(
        "resolve-inflight",
        help="Preserve an ambiguous interrupted dispatch and permit a transparent retry",
    )
    res.add_argument("--representation", required=True, choices=sorted(MODEL_CONFIGS))
    res.add_argument("--action", required=True, choices=["retry"])

    args = parser.parse_args()

    if args.command == "preflight":
        state = preflight(args.representation, args.implementation_commit)
        printable = {k: v for k, v in state.items() if k not in {"cards", "completed", "attempt_counts"}}
        printable["valid_cards_existing"] = len(state["completed"])
        printable["attempt_records_existing"] = sum(state["attempt_counts"].values())
        print(json.dumps(printable, indent=2, sort_keys=True))
    elif args.command == "synthetic-test":
        synthetic_test(args.representation)
    elif args.command == "run":
        run_real(args.representation, args.implementation_commit)
    elif args.command == "validate":
        validate(args.representation, args.implementation_commit)
    elif args.command == "resolve-inflight":
        resolve_inflight(args.representation, args.action)
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
