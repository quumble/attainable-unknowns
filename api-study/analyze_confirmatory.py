#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2, norm

EXPECTED_MODELS = {"luna", "terra", "haiku", "sonnet"}
EXPECTED_GAPS = {"closed", "seamed", "explicit_gap"}
EXPECTED_TOPICS = 12
EXPECTED_CONDITIONS = 36
EXPECTED_DRAWS_PER_CONDITION = 25
EXPECTED_ATTEMPTS_PER_MODEL = 900
ALPHA = 0.05


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_records_path(manifest_path: Path, records_file: str) -> Path:
    candidate = Path(records_file)
    if candidate.exists():
        return candidate
    sibling = manifest_path.parent / candidate.name
    if sibling.exists():
        return sibling
    raise ValueError(f"records file not found for {manifest_path}: {records_file}")


def validate_manifests(
    manifest_paths: list[Path],
    expected_hashes: dict[str, str],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    if len(manifest_paths) != 4:
        raise ValueError("exactly four accepted full-run manifests are required")

    manifests: list[dict[str, Any]] = []
    all_records: list[dict[str, Any]] = []
    seen_models: set[str] = set()
    seen_record_ids: set[str] = set()

    for manifest_path in manifest_paths:
        m = load_json(manifest_path)
        model = m.get("model_key")
        if model not in EXPECTED_MODELS:
            raise ValueError(f"unexpected model_key in {manifest_path}: {model}")
        if model in seen_models:
            raise ValueError(f"duplicate accepted full run for model: {model}")
        seen_models.add(model)

        if m.get("status") != "complete":
            raise ValueError(f"manifest is not complete: {manifest_path}")
        if m.get("full_design_run") is not True:
            raise ValueError(f"manifest is not a full-design run: {manifest_path}")
        if int(m.get("planned_requests", -1)) != EXPECTED_ATTEMPTS_PER_MODEL:
            raise ValueError(f"wrong planned_requests in {manifest_path}")
        if int(m.get("full_design_requests", -1)) != EXPECTED_ATTEMPTS_PER_MODEL:
            raise ValueError(f"wrong full_design_requests in {manifest_path}")

        for key in ("config_sha256", "passages_sha256", "runner_sha256"):
            observed = m.get(key)
            expected = expected_hashes.get(key)
            if not expected:
                raise ValueError(f"expected hash file is missing {key}")
            if observed != expected:
                raise ValueError(f"{key} mismatch in {manifest_path}: {observed} != {expected}")

        records_path = resolve_records_path(
            manifest_path,
            str(m.get("records_file", "")),
        )
        observed_records_hash = sha256(records_path)
        if observed_records_hash != m.get("records_sha256"):
            raise ValueError(f"records SHA-256 mismatch: {records_path}")

        rows: list[dict[str, Any]] = []
        with records_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                row["_source_manifest"] = str(manifest_path)
                row["_source_records"] = str(records_path)
                row["_line"] = line_no
                rows.append(row)

        if len(rows) != EXPECTED_ATTEMPTS_PER_MODEL:
            raise ValueError(f"expected 900 records for {model}, found {len(rows)}")

        run_id = m.get("run_id")
        pairs: set[tuple[str, int]] = set()
        condition_counts: dict[str, int] = {}
        errors = 0
        topics: set[str] = set()
        gaps: set[str] = set()

        for row in rows:
            if row.get("run_id") != run_id:
                raise ValueError(f"run_id mismatch in {records_path} line {row['_line']}")
            if row.get("model_key") != model:
                raise ValueError(f"model_key mismatch in {records_path} line {row['_line']}")
            rid = row.get("record_id")
            if not rid or rid in seen_record_ids:
                raise ValueError(f"missing or duplicate record_id: {rid}")
            seen_record_ids.add(rid)

            condition = row.get("condition_id")
            replicate = row.get("replicate")
            if not condition or not isinstance(replicate, int):
                raise ValueError(
                    f"missing condition_id/replicate in {records_path} line {row['_line']}"
                )
            pair = (condition, replicate)
            if pair in pairs:
                raise ValueError(f"duplicate condition/replicate pair for {model}: {pair}")
            pairs.add(pair)
            condition_counts[condition] = condition_counts.get(condition, 0) + 1

            topic = row.get("topic_id")
            gap = row.get("gap_structure")
            if not topic or gap not in EXPECTED_GAPS:
                raise ValueError(
                    f"invalid topic/gap metadata in {records_path} line {row['_line']}"
                )
            topics.add(topic)
            gaps.add(gap)

            status = row.get("status")
            if status == "error":
                errors += 1
            elif status == "success":
                if not isinstance(row.get("format_valid"), bool):
                    raise ValueError(
                        f"success row missing boolean format_valid in {records_path} line {row['_line']}"
                    )
                if not isinstance(row.get("sensitivity_activation"), bool):
                    raise ValueError(
                        f"success row missing boolean sensitivity_activation in {records_path} line {row['_line']}"
                    )
            else:
                raise ValueError(
                    f"unexpected row status in {records_path} line {row['_line']}: {status}"
                )

        if len(condition_counts) != EXPECTED_CONDITIONS:
            raise ValueError(
                f"expected 36 conditions for {model}, found {len(condition_counts)}"
            )
        if any(n != EXPECTED_DRAWS_PER_CONDITION for n in condition_counts.values()):
            bad = {
                k: v for k, v in condition_counts.items()
                if v != EXPECTED_DRAWS_PER_CONDITION
            }
            raise ValueError(f"wrong draws per condition for {model}: {bad}")
        if len(topics) != EXPECTED_TOPICS or gaps != EXPECTED_GAPS:
            raise ValueError(f"topic/gap coverage is incomplete for {model}")
        if errors != int(m.get("error_requests", -1)):
            raise ValueError(f"manifest error count mismatch for {model}")
        if errors >= 10:
            raise ValueError(
                f"{model} has {errors} technical failures and is compromised "
                "by the preregistered >=1% rule"
            )
        if len(rows) - errors != int(m.get("successful_requests", -1)):
            raise ValueError(f"manifest success count mismatch for {model}")

        m["_manifest_path"] = str(manifest_path)
        m["_records_path"] = str(records_path)
        manifests.append(m)
        all_records.extend(rows)

    if seen_models != EXPECTED_MODELS:
        raise ValueError(
            f"accepted runs must contain exactly {sorted(EXPECTED_MODELS)}"
        )

    return pd.DataFrame(all_records), manifests


def build_design(
    df: pd.DataFrame,
    outcome_col: str,
) -> tuple[np.ndarray, np.ndarray, list[str], pd.DataFrame]:
    work = df.copy()
    work["stratum"] = (
        work["model_key"].astype(str) + "::" + work["topic_id"].astype(str)
    )
    work["gap_seamed"] = (
        work["gap_structure"] == "seamed"
    ).astype(float)
    work["gap_explicit"] = (
        work["gap_structure"] == "explicit_gap"
    ).astype(float)

    strata = pd.get_dummies(
        work["stratum"],
        prefix="stratum",
        drop_first=True,
        dtype=float,
    )
    x = pd.concat([
        pd.Series(1.0, index=work.index, name="const"),
        strata,
        work[["gap_seamed", "gap_explicit"]],
    ], axis=1)
    y = work[outcome_col].astype(float).to_numpy()
    return y, x.to_numpy(dtype=float), list(x.columns), work


def fit_reduced(df: pd.DataFrame, outcome_col: str):
    y, x, names, work = build_design(df, outcome_col)
    fit = sm.GLM(y, x, family=sm.families.Binomial()).fit()
    return fit, names, work


def contrast(
    fit,
    names: list[str],
    weights: dict[str, float],
    alternative: str = "two-sided",
) -> dict[str, Any]:
    w = np.zeros(len(names), dtype=float)
    for name, value in weights.items():
        w[names.index(name)] = value
    estimate = float(w @ fit.params)
    variance = float(w @ fit.cov_params() @ w)
    se = math.sqrt(max(variance, 0.0))
    z = estimate / se if se > 0 else (
        math.inf if estimate > 0
        else -math.inf if estimate < 0
        else 0.0
    )
    if alternative == "greater":
        p = float(norm.sf(z))
    elif alternative == "less":
        p = float(norm.cdf(z))
    else:
        p = float(2 * norm.sf(abs(z)))
    lo = estimate - 1.959963984540054 * se
    hi = estimate + 1.959963984540054 * se
    return {
        "log_odds_difference": estimate,
        "standard_error": se,
        "odds_ratio": math.exp(estimate),
        "odds_ratio_ci95": [math.exp(lo), math.exp(hi)],
        "z": z,
        "p": p,
        "alternative": alternative,
    }


def h1_results(
    df: pd.DataFrame,
    outcome_col: str,
) -> tuple[dict[str, Any], Any, list[str], pd.DataFrame]:
    fit, names, work = fit_reduced(df, outcome_col)
    seam_vs_closed = contrast(
        fit,
        names,
        {"gap_seamed": 1.0},
        alternative="greater",
    )
    explicit_vs_seam = contrast(
        fit,
        names,
        {"gap_explicit": 1.0, "gap_seamed": -1.0},
        alternative="greater",
    )
    explicit_vs_closed = contrast(
        fit,
        names,
        {"gap_explicit": 1.0},
        alternative="two-sided",
    )
    supported = bool(
        seam_vs_closed["p"] < ALPHA
        and explicit_vs_seam["p"] < ALPHA
    )
    result = {
        "alpha": ALPHA,
        "decision_rule": (
            "H1 is supported only if both prespecified one-sided adjacent "
            "contrasts have p < alpha. This is an intersection-union test; "
            "no multiplicity correction is applied to the two component tests."
        ),
        "seamed_gt_closed": seam_vs_closed,
        "explicit_gt_seamed": explicit_vs_seam,
        "explicit_vs_closed_secondary": explicit_vs_closed,
        "h1_supported": supported,
    }
    return result, fit, names, work


def h2_model_interaction(
    df: pd.DataFrame,
    outcome_col: str,
) -> dict[str, Any]:
    reduced, reduced_names, work = fit_reduced(df, outcome_col)
    x_reduced = pd.DataFrame(
        reduced.model.exog,
        columns=reduced_names,
        index=work.index,
    )
    model_dummies = pd.get_dummies(
        work["model_key"],
        prefix="model",
        drop_first=True,
        dtype=float,
    )
    interaction_cols: dict[str, pd.Series] = {}
    for mcol in model_dummies.columns:
        interaction_cols[f"{mcol}:gap_seamed"] = (
            model_dummies[mcol] * work["gap_seamed"]
        )
        interaction_cols[f"{mcol}:gap_explicit"] = (
            model_dummies[mcol] * work["gap_explicit"]
        )
    interactions = pd.DataFrame(interaction_cols, index=work.index)
    x_full = pd.concat([x_reduced, interactions], axis=1)
    y = work[outcome_col].astype(float).to_numpy()
    full = sm.GLM(
        y,
        x_full.to_numpy(dtype=float),
        family=sm.families.Binomial(),
    ).fit()

    lr = max(0.0, 2.0 * (full.llf - reduced.llf))
    df_diff = int(round(full.df_model - reduced.df_model))
    p = float(chi2.sf(lr, df_diff)) if df_diff > 0 else float("nan")
    return {
        "test": (
            "likelihood-ratio comparison of common categorical gap effects "
            "vs model-specific categorical gap effects"
        ),
        "lr_statistic": lr,
        "df": df_diff,
        "p": p,
        "alpha": ALPHA,
    }


def descriptive_table(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    grouped = df.groupby(["model_key", "gap_structure"], dropna=False)
    for (model, gap), g in grouped:
        success = g[g["status"] == "success"]
        valid = success[success["format_valid"] == True]  # noqa: E712
        emitted = valid[
            (valid["parsed_none"] != True)  # noqa: E712
            & valid["parsed_question"].notna()
        ]
        sensitivity_n = int(
            (success["sensitivity_activation"] == True).sum()  # noqa: E712
        )
        rows.append({
            "model_key": model,
            "gap_structure": gap,
            "attempts": int(len(g)),
            "successes": int(len(success)),
            "format_valid_successes": int(len(valid)),
            "format_invalid_successes": int(len(success) - len(valid)),
            "format_invalid_rate_successes": (
                None
                if len(success) == 0
                else float((len(success) - len(valid)) / len(success))
            ),
            "question_emissions": int(len(emitted)),
            "question_emission_rate_valid_successes": (
                None
                if len(valid) == 0
                else float(len(emitted) / len(valid))
            ),
            "sensitivity_non_none": sensitivity_n,
            "sensitivity_non_none_rate_successes": (
                None
                if len(success) == 0
                else float(sensitivity_n / len(success))
            ),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and run the preregistered Attainable Unknowns "
            "confirmatory analyses."
        )
    )
    parser.add_argument(
        "manifests",
        nargs=4,
        type=Path,
        help="Exactly four accepted full-run manifest JSON files, one per model.",
    )
    parser.add_argument(
        "--expected-hashes",
        required=True,
        type=Path,
        help=(
            "Frozen JSON containing config_sha256, passages_sha256, "
            "and runner_sha256."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("api-study/data/analysis/confirmatory-results.json"),
    )
    args = parser.parse_args()

    expected_hashes = load_json(args.expected_hashes)
    records, manifests = validate_manifests(
        args.manifests,
        expected_hashes,
    )

    successes = records[records["status"] == "success"].copy()
    primary = successes[successes["format_valid"] == True].copy()  # noqa: E712
    primary["question_emission"] = (
        (primary["parsed_none"] != True)  # noqa: E712
        & primary["parsed_question"].notna()
    ).astype(int)
    successes["sensitivity_outcome"] = (
        successes["sensitivity_activation"].astype(bool).astype(int)
    )

    h1, _, _, _ = h1_results(primary, "question_emission")
    h2 = h2_model_interaction(primary, "question_emission")
    sensitivity_h1, _, _, _ = h1_results(
        successes,
        "sensitivity_outcome",
    )
    sensitivity_h2 = h2_model_interaction(
        successes,
        "sensitivity_outcome",
    )

    result = {
        "analysis_version": "api-pilot-0.1-preregistered-candidate",
        "expected_hashes": expected_hashes,
        "accepted_runs": [
            {
                "model_key": m["model_key"],
                "run_id": m["run_id"],
                "manifest_path": m["_manifest_path"],
                "records_path": m["_records_path"],
                "successful_requests": m["successful_requests"],
                "error_requests": m["error_requests"],
                "records_sha256": m["records_sha256"],
            }
            for m in sorted(manifests, key=lambda x: x["model_key"])
        ],
        "validation": {
            "attempted_records": int(len(records)),
            "successful_records": int(len(successes)),
            "primary_format_valid_records": int(len(primary)),
            "format_invalid_successes": int(len(successes) - len(primary)),
        },
        "descriptive_by_model_gap": descriptive_table(records),
        "primary_estimand": (
            "P(question emission | successful, format-valid response) "
            "for the frozen passages and API draws"
        ),
        "h1_primary_intersection_union": h1,
        "h2_secondary_model_by_gap": h2,
        "sensitivity_any_nonempty_non_none": {
            "estimand": (
                "P(nonempty non-NONE response | successful response)"
            ),
            "h1": sensitivity_h1,
            "h2": sensitivity_h2,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "complete",
        "output": str(args.output),
        "attempted_records": len(records),
        "primary_format_valid_records": len(primary),
        "h1_supported": h1["h1_supported"],
        "h2_p": h2["p"],
    }, indent=2))


if __name__ == "__main__":
    main()
