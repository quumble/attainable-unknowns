#!/usr/bin/env python3
"""Audit all reachable Git objects before making Attainable Unknowns public.

This is a release-safety check, not a proof that no sensitive information exists.
It scans every blob reachable from every local/refetched ref for several common
credential formats and inventories lower-risk public-release metadata such as
absolute paths, email addresses, and provider response identifiers.

Run from the repository root after `git fetch --all --prune`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

MAX_SCAN_BYTES = 30 * 1024 * 1024

HIGH_PATTERNS = {
    "openai_api_key": re.compile(rb"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b"),
    "anthropic_api_key": re.compile(rb"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
    "github_token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b"),
    "aws_access_key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "private_key_pem": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "basic_auth_url": re.compile(rb"https?://[^\s/:@]+:[^\s/@]+@"),
}

# Generic assignment catches secrets that do not use a provider-specific prefix.
# Obvious placeholders and environment-variable names are filtered later.
GENERIC_EQUALS_ASSIGNMENT = re.compile(
    rb"(?i)\b(api[_-]?key|secret|access[_-]?token|auth[_-]?token|password)\b\s*=\s*[\"']?([^\s\"'`,;}{]{16,})"
)
# Colon syntax is restricted to quoted mapping/JSON keys so Python control flow such as
# `if not api_key:` cannot be mistaken for a secret assignment.
GENERIC_MAPPING_ASSIGNMENT = re.compile(
    rb"(?i)[\"'](api[_-]?key|secret|access[_-]?token|auth[_-]?token|password)[\"']\s*:\s*[\"']([^\"']{16,})[\"']"
)

WARN_PATTERNS = {
    "windows_absolute_path": re.compile(rb"\b[A-Za-z]:\\[^\r\n\"']+"),
    "unix_home_path": re.compile(rb"/(?:Users|home)/[^/\s\"']+/[^\r\n\"']+"),
    "email_address": re.compile(rb"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "openai_response_id": re.compile(rb"\bresp_[A-Za-z0-9_-]{12,}\b"),
    "openai_message_id": re.compile(rb"\bmsg_[A-Za-z0-9_-]{12,}\b"),
}

PLACEHOLDER_VALUES = {
    b"OPENAI_API_KEY",
    b"ANTHROPIC_API_KEY",
    b"API_KEY",
    b"YOUR_API_KEY",
    b"REDACTED",
    b"CHANGEME",
    b"PLACEHOLDER",
}

SAFE_BLINDING_NAMES = {
    "UNBLINDING_KEY.json",
    "E1_STAGE1_PRIVATE_KEY.json",
    "E1_STAGE2_PRIVATE_KEY.json",
    "FA1_PRIVATE_KEY.json",
    "TIEBREAK_PRIVATE_KEY.json",
}

SUSPECT_NAME_RE = re.compile(r"(^|/)(\.env(?:\..*)?|.*(?:credential|secret|password).*)$", re.I)
PEM_KEY_NAME_RE = re.compile(r"\.(?:pem|p12|pfx|key)$", re.I)


def git(*args: str, input_bytes: bytes | None = None, check: bool = True) -> bytes:
    proc = subprocess.run(
        ["git", *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace").strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def repo_root() -> Path:
    out = git("rev-parse", "--show-toplevel").decode().strip()
    return Path(out)


def all_objects() -> list[tuple[str, str]]:
    lines = git("rev-list", "--objects", "--all").decode("utf-8", "replace").splitlines()
    objects: list[tuple[str, str]] = []
    for line in lines:
        if not line:
            continue
        parts = line.split(" ", 1)
        objects.append((parts[0], parts[1] if len(parts) == 2 else ""))
    return objects


def object_meta(shas: list[str]) -> dict[str, tuple[str, int]]:
    payload = ("\n".join(shas) + "\n").encode()
    out = git("cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)", input_bytes=payload)
    meta: dict[str, tuple[str, int]] = {}
    for line in out.decode().splitlines():
        sha, typ, size = line.split()
        meta[sha] = (typ, int(size))
    return meta


def read_blobs(blobs: list[tuple[str, str, int]]):
    proc = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin is not None and proc.stdout is not None
    try:
        for sha, path, size in blobs:
            proc.stdin.write((sha + "\n").encode())
            proc.stdin.flush()
            header = proc.stdout.readline().decode("ascii", "replace").strip()
            parts = header.split()
            if len(parts) < 3 or parts[0] != sha or parts[1] != "blob":
                raise RuntimeError(f"Unexpected cat-file header for {sha}: {header}")
            actual_size = int(parts[2])
            data = proc.stdout.read(actual_size)
            newline = proc.stdout.read(1)
            if newline != b"\n":
                raise RuntimeError(f"Malformed cat-file stream after {sha}")
            yield sha, path, actual_size, data
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        proc.terminate()
        proc.wait(timeout=5)


def likely_binary(data: bytes) -> bool:
    sample = data[:8192]
    return b"\x00" in sample


def short_hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()[:12]


def commits_for_object(sha: str) -> list[str]:
    out = git("log", "--all", "--find-object=" + sha, "--format=%H", "--max-count=4", check=False)
    return [x for x in out.decode().splitlines() if x]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, help="Write a sanitized JSON summary")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    root = repo_root()
    os.chdir(root)

    status = git("status", "--porcelain=v1").decode().splitlines()
    if status and not args.allow_dirty:
        print("FAIL: working tree is not clean. Commit/stash release files or rerun with --allow-dirty for a provisional scan.")
        for line in status[:20]:
            print("  " + line)
        return 3

    head = git("rev-parse", "HEAD").decode().strip()
    refs = git("for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes", "refs/tags").decode().splitlines()
    branches = git("for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes").decode().splitlines()
    emails = sorted(set(x for x in git("log", "--all", "--format=%ae%n%ce").decode("utf-8", "replace").splitlines() if x))

    obj_rows = all_objects()
    meta = object_meta([sha for sha, _ in obj_rows])
    blob_rows = [(sha, path, meta[sha][1]) for sha, path in obj_rows if meta.get(sha, (None, 0))[0] == "blob"]

    high: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    name_warnings: list[dict[str, str]] = []
    scanned_blobs = 0
    scanned_bytes = 0
    skipped_large = []
    skipped_binary = 0

    for sha, path, size in blob_rows:
        name = Path(path).name if path else ""
        if name not in SAFE_BLINDING_NAMES and (SUSPECT_NAME_RE.search(path) or PEM_KEY_NAME_RE.search(path)):
            name_warnings.append({"path": path, "object": sha})
        if size > MAX_SCAN_BYTES:
            skipped_large.append({"path": path, "object": sha, "bytes": size})

    scan_rows = [r for r in blob_rows if r[2] <= MAX_SCAN_BYTES]
    for sha, path, size, data in read_blobs(scan_rows):
        if likely_binary(data):
            skipped_binary += 1
            continue
        scanned_blobs += 1
        scanned_bytes += size

        for label, rx in HIGH_PATTERNS.items():
            for m in rx.finditer(data):
                high.append({
                    "kind": label,
                    "path": path,
                    "object": sha,
                    "match_hash": short_hash(m.group(0)),
                })

        for m in list(GENERIC_EQUALS_ASSIGNMENT.finditer(data)) + list(GENERIC_MAPPING_ASSIGNMENT.finditer(data)):
            value = m.group(2).strip().strip(b"\"'")
            upper = value.upper()
            if upper in PLACEHOLDER_VALUES or upper.endswith(b"_API_KEY") or upper.endswith(b"_TOKEN"):
                continue
            # Source-code expressions that *retrieve* a secret are not secret values.
            # Examples in this repository include:
            #   api_key = os.environ.get(cfg["api_key_env"])
            #   api_key = os.getenv("OPENAI_API_KEY")
            if re.match(rb"os\.(?:environ\.get|getenv)\(", value):
                continue
            if re.match(rb"(?:os\.)?environ\[", value):
                continue
            # Passing a variable through an SDK constructor is also not a literal secret.
            if value in {b"api_key", b"secret", b"access_token", b"auth_token", b"password"}:
                continue
            # Long hex digests and Git SHAs are routine in this repository and not credentials.
            if re.fullmatch(rb"[0-9a-fA-F]{32,128}", value):
                continue
            high.append({
                "kind": "generic_secret_assignment",
                "path": path,
                "object": sha,
                "match_hash": short_hash(value),
            })

        for label, rx in WARN_PATTERNS.items():
            count = len(rx.findall(data))
            if count:
                warnings.append({"kind": label, "path": path, "object": sha, "count": count})

    # De-duplicate by kind/path/object/hash without ever printing secret material.
    dedup_high = []
    seen = set()
    for item in high:
        key = (item["kind"], item["path"], item["object"], item["match_hash"])
        if key not in seen:
            seen.add(key)
            item["example_commits"] = commits_for_object(str(item["object"]))
            dedup_high.append(item)
    high = dedup_high

    warn_counts = Counter(str(x["kind"]) for x in warnings)
    non_main = [
        b for b in branches
        if b not in {"main", "origin", "origin/main", "origin/HEAD"} and not b.endswith("/HEAD")
    ]

    print(f"Repository: {root}")
    print(f"HEAD: {head}")
    print(f"Refs inventoried: {len(refs)}")
    print(f"Reachable blobs: {len(blob_rows)}")
    print(f"Text blobs scanned: {scanned_blobs} ({scanned_bytes:,} bytes)")
    print(f"Binary blobs skipped: {skipped_binary}")
    print(f"Oversize blobs skipped: {len(skipped_large)}")
    print(f"High-confidence credential findings: {len(high)}")
    print(f"Suspicious credential-like filenames: {len(name_warnings)}")
    print(f"Non-main branch refs: {len(non_main)}")
    for b in non_main:
        print(f"  BRANCH: {b}")
    print(f"Commit author/committer email addresses exposed by public history: {len(emails)}")
    for email in emails:
        print(f"  EMAIL: {email}")
    for kind, count in sorted(warn_counts.items()):
        print(f"Metadata warning {kind}: {count} blob(s)")

    if name_warnings:
        print("Credential-like filenames (inspect manually):")
        for item in name_warnings[:30]:
            print(f"  {item['path']} [{item['object'][:12]}]")

    if high:
        print("HIGH-CONFIDENCE FINDINGS (values intentionally redacted):")
        for item in high[:50]:
            commits = ",".join(str(x)[:12] for x in item.get("example_commits", [])) or "unknown"
            print(f"  {item['kind']}: {item['path']} object={str(item['object'])[:12]} value_sha256={item['match_hash']} commits={commits}")

    report = {
        "schema_version": "au-public-release-audit-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "head": head,
        "refs_inventoried": len(refs),
        "reachable_blobs": len(blob_rows),
        "text_blobs_scanned": scanned_blobs,
        "text_bytes_scanned": scanned_bytes,
        "binary_blobs_skipped": skipped_binary,
        "oversize_blobs_skipped": len(skipped_large),
        "high_confidence_credential_findings": len(high),
        "suspicious_credential_like_filenames": len(name_warnings),
        "non_main_branch_refs": non_main,
        "commit_email_address_count": len(emails),
        "metadata_warning_blob_counts": dict(sorted(warn_counts.items())),
        "result": "pass" if not high else "fail",
        "note": "Secret values and email addresses are intentionally omitted from this report. Console output inventories commit emails for explicit public-release review.",
    }
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Sanitized report written: {args.report}")

    return 0 if not high else 2


if __name__ == "__main__":
    raise SystemExit(main())
