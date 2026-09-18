#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import random
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "config.yaml"
DEFAULT_PASSAGES = HERE / "passages.json"
DEFAULT_OUTPUT = HERE / "data" / "raw"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git_state() -> dict[str, Any]:
    def run(*args: str) -> str | None:
        p = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
        return p.stdout.strip() if p.returncode == 0 else None
    status = run("status", "--porcelain")
    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(status) if status is not None else None}

def load_env_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))

def flatten_conditions(bank: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for topic in bank["topics"]:
        for gap_structure, passage in topic["variants"].items():
            out.append({
                "condition_id": f"{topic['topic_id']}__{gap_structure}",
                "topic_id": topic["topic_id"],
                "topic_label": topic["label"],
                "domain_class": topic["domain_class"],
                "selection_provenance": topic["selection_provenance"],
                "abstraction": topic["abstraction"],
                "voice": topic["voice"],
                "epistemic_friction": topic["epistemic_friction"],
                "gap_structure": gap_structure,
                "passage": passage,
            })
    return out

def make_prompt(instruction: str, passage: str) -> str:
    return f"{instruction.rstrip()}\n\nPASSAGE:\n{passage.strip()}"

def parse_output(text: str) -> dict[str, Any]:
    raw = text.strip()
    none = raw.upper() == "NONE"
    question_valid = bool(
        raw
        and not none
        and "\n" not in raw
        and len(raw) <= 500
        and raw.endswith("?")
        and raw.count("?") == 1
    )
    return {
        "parsed_none": none,
        "parsed_question": raw if question_valid else None,
        "format_valid": bool(none or question_valid),
        "sensitivity_activation": bool(raw and not none),
    }

def call_openai(api_key: str, cfg: dict[str, Any], system: str, prompt: str) -> tuple[str, dict[str, Any]]:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, max_retries=0)
    kwargs: dict[str, Any] = {
        "model": cfg["model"],
        "instructions": system,
        "input": prompt,
        "max_output_tokens": int(cfg.get("max_output_tokens", 80)),
    }
    if cfg.get("reasoning_effort"):
        kwargs["reasoning"] = {"effort": cfg["reasoning_effort"]}
    response = client.responses.create(**kwargs)
    return response.output_text, response.model_dump(mode="json")

def call_anthropic(api_key: str, cfg: dict[str, Any], system: str, prompt: str) -> tuple[str, dict[str, Any]]:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key, max_retries=0)
    kwargs: dict[str, Any] = {
        "model": cfg["model"],
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": int(cfg.get("max_output_tokens", 80)),
    }
    if cfg.get("thinking"):
        kwargs["thinking"] = cfg["thinking"]
    response = client.messages.create(**kwargs)
    text = "".join(block.text for block in response.content if block.type == "text")
    return text, response.model_dump(mode="json")

CALLERS = {"openai": call_openai, "anthropic": call_anthropic}

def rough_tokens(text: str) -> int:
    return max(1, (len(text) + 2) // 3)

def budget_estimate(config: dict[str, Any], model_cfg: dict[str, Any], conditions: list[dict[str, Any]]) -> dict[str, Any]:
    reps = int(config["replicates"])
    system = config["system_prompt"]
    instruction = config["user_instruction"]
    input_tokens = sum(rough_tokens(system + "\n" + make_prompt(instruction, c["passage"])) for c in conditions) * reps
    output_tokens = len(conditions) * reps * int(config.get("max_output_tokens", 80))
    estimated = input_tokens / 1_000_000 * float(model_cfg["input_per_million"]) + output_tokens / 1_000_000 * float(model_cfg["output_per_million"])
    return {
        "planned_requests": len(conditions) * reps,
        "conservative_input_tokens": input_tokens,
        "conservative_output_tokens": output_tokens,
        "conservative_cost_usd": round(estimated, 4),
        "stop_limit_usd": float(model_cfg["stop_limit_usd"]),
        "passes": estimated <= float(model_cfg["stop_limit_usd"]),
    }

def usage_cost(provider: str, raw: dict[str, Any], cfg: dict[str, Any]) -> tuple[int | None, int | None, float | None]:
    try:
        usage = raw.get("usage") or {}
        inp = usage.get("input_tokens")
        out = usage.get("output_tokens")
        if inp is None or out is None:
            return inp, out, None
        cost = inp / 1_000_000 * float(cfg["input_per_million"]) + out / 1_000_000 * float(cfg["output_per_million"])
        return int(inp), int(out), float(cost)
    except Exception:
        return None, None, None

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Attainable Unknowns inquiry-formation API pilot.")
    parser.add_argument("--model", required=True, choices=["luna", "terra", "haiku", "sonnet"])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--passages", type=Path, default=DEFAULT_PASSAGES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stop-after", type=int, help="Debug only; stops after N randomized requests.")
    args = parser.parse_args()

    load_env_file()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    model_cfg = dict(config["models"][args.model])
    model_cfg["max_output_tokens"] = int(config.get("max_output_tokens", 80))
    provider = model_cfg["provider"]
    bank = json.loads(args.passages.read_text(encoding="utf-8"))
    conditions = flatten_conditions(bank)

    estimate = budget_estimate(config, model_cfg, conditions)
    if not estimate["passes"]:
        raise SystemExit("Conservative preflight exceeds configured stop limit; refusing to run.")

    work = [(c, r) for c in conditions for r in range(1, int(config["replicates"]) + 1)]
    rng = random.Random(int(config["order_seed"]) + ["luna", "terra", "haiku", "sonnet"].index(args.model))
    rng.shuffle(work)
    full_design_run = args.stop_after is None
    if args.stop_after is not None:
        work = work[:args.stop_after]

    summary = {
        "model_key": args.model,
        "provider": provider,
        "model": model_cfg["model"],
        "conditions": len(conditions),
        "replicates": int(config["replicates"]),
        "planned_requests": len(work),
        "full_design_requests": estimate["planned_requests"],
        "full_design_run": full_design_run,
        "passages_sha256": sha256(args.passages),
        "config_sha256": sha256(args.config),
        "budget_preflight": estimate,
    }
    if args.dry_run:
        print(json.dumps(summary, indent=2))
        return

    api_key = os.environ.get(model_cfg["api_key_env"])
    if not api_key:
        raise SystemExit(f"Missing environment variable: {model_cfg['api_key_env']}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{args.model}-{uuid.uuid4().hex[:8]}"
    partial = args.output_dir / f"{run_id}.partial.jsonl"
    final = args.output_dir / f"{run_id}.jsonl"
    manifest_path = args.output_dir / f"{run_id}.manifest.json"

    manifest = {
        **summary,
        "run_id": run_id,
        "started_at": utc_now(),
        "status": "running",
        "git": git_state(),
        "python": sys.version,
        "platform": platform.platform(),
        "packages": {},
        "model_config_without_secret": model_cfg,
        "pricing_snapshot": config.get("pricing_snapshot"),
    }
    for pkg in ("openai", "anthropic", "PyYAML"):
        try:
            manifest["packages"][pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            pass
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    successful = errors = 0
    cumulative_estimated_cost = 0.0
    system = config["system_prompt"]
    instruction = config["user_instruction"]

    with partial.open("a", encoding="utf-8", newline="\n", buffering=1) as handle:
        for sequence, (condition, replicate) in enumerate(work, start=1):
            prompt = make_prompt(instruction, condition["passage"])
            before = time.monotonic()
            base = {
                "record_id": str(uuid.uuid4()),
                "run_id": run_id,
                "sequence": sequence,
                "replicate": replicate,
                "model_key": args.model,
                "provider": provider,
                "model_requested": model_cfg["model"],
                **condition,
                "system_prompt": system,
                "user_prompt": prompt,
                "started_at": utc_now(),
            }
            try:
                text, raw = CALLERS[provider](api_key, model_cfg, system, prompt)
                parsed = parse_output(text)
                inp, out, estimated_cost = usage_cost(provider, raw, model_cfg)
                if estimated_cost is not None:
                    cumulative_estimated_cost += estimated_cost
                record = {
                    **base,
                    "status": "success",
                    "response_text": text,
                    **parsed,
                    "input_tokens": inp,
                    "output_tokens": out,
                    "estimated_cost_usd": estimated_cost,
                    "raw_response": raw,
                }
                successful += 1
            except Exception as exc:
                record = {**base, "status": "error", "error_type": type(exc).__name__, "error": str(exc)}
                errors += 1

            record["finished_at"] = utc_now()
            record["elapsed_seconds"] = round(time.monotonic() - before, 6)
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

            if cumulative_estimated_cost > float(model_cfg["stop_limit_usd"]):
                raise SystemExit(
                    f"Observed token-based cost estimate exceeded stop limit "
                    f"({cumulative_estimated_cost:.4f} > {model_cfg['stop_limit_usd']:.2f}); partial file preserved."
                )

    partial.replace(final)
    manifest.update({
        "finished_at": utc_now(),
        "status": "complete",
        "successful_requests": successful,
        "error_requests": errors,
        "records_file": str(final),
        "records_sha256": sha256(final),
        "observed_token_cost_estimate_usd": round(cumulative_estimated_cost, 6),
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for path in (final, manifest_path):
        path.with_suffix(path.suffix + ".sha256").write_text(f"{sha256(path)}  {path.name}\n", encoding="utf-8")

    print(json.dumps({
        "run_id": run_id,
        "successful": successful,
        "errors": errors,
        "estimated_cost_usd": round(cumulative_estimated_cost, 6),
        "output": str(final),
    }, indent=2))

if __name__ == "__main__":
    main()
