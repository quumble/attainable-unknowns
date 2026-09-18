#!/usr/bin/env python3
"""Attainable Unknowns API Pilot 0.1 — confirmatory analysis under Amendment A1.

This script does NOT replace the frozen analysis. It imports `analyze_confirmatory`
and runs the frozen validation, stratified-MLE model, and descriptive table.
Frozen contrast exponentials are guarded in memory for reporting. It adds, per Amendment A1 (2026-09-18T21:10:55Z):

  1. a numerical guard so a divergent odds-ratio CI cannot abort the run;
  2. separate mechanical estimability/separation diagnostics for H1 and H2;
  3. a prespecified fallback estimator (Firth penalized likelihood) that becomes
     decision-bearing for each test only when that test's flag is raised;
  4. a prespecified corroborating stratified conditional permutation test with
     a Monte Carlo p-value on the two H1 adjacent contrasts, reported always,
     decision-bearing never.

When a test's flag is not raised, its decision is numerically and
decision-identical to the frozen analysis. If a required gap level is absent, or
if a decision-bearing Firth fit does not converge, that test is indeterminate.

Usage (from repo root):
  python api-study/analyze_confirmatory_a1.py <4 manifests> --expected-hashes <json>
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2

import analyze_confirmatory as frozen

AMENDMENT = "A1"
AMENDMENT_UTC = "2026-09-18T21:10:55Z"
REVISION_UTC = "2026-09-18T21:44:21Z"
FINAL_REVIEW_UTC = "2026-09-18T22:36:16Z"
ALPHA = frozen.ALPHA

# Amendment A1 separation-flag thresholds. These are diagnostics of estimability
# only: direction-blind thresholds, not a test of the predicted ordering.
ABS_BETA_FLAG = 10.0
SE_FLAG = 10.0

PERMUTATIONS = 100_000
PERM_SEED = 91826  # config.yaml order_seed, reused for continuity


def load_expected_hashes(path: Path) -> dict[str, str]:
    """Accept either the frozen flat adapter or the signed freeze record.

    The PowerShell-generated freeze record can carry a UTF-8 BOM and nests the
    three manifest-validation hashes under `frozen_study_files_sha256`.
    Normalizing that document is deterministic and does not inspect outcomes.
    """
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    required = ("config_sha256", "passages_sha256", "runner_sha256")
    if all(document.get(key) for key in required):
        return {key: str(document[key]) for key in required}

    frozen_files = document.get("frozen_study_files_sha256")
    if not isinstance(frozen_files, dict):
        raise ValueError(
            "expected-hashes input must be either a flat hash object or the "
            "API Pilot 0.1 freeze record"
        )
    mapping = {
        "config_sha256": "api-study/config.yaml",
        "passages_sha256": "api-study/passages.json",
        "runner_sha256": "api-study/run.py",
    }
    normalized = {key: frozen_files.get(source) for key, source in mapping.items()}
    missing = [key for key, value in normalized.items() if not value]
    if missing:
        raise ValueError(f"freeze record is missing required hashes: {missing}")
    return {key: str(value) for key, value in normalized.items()}


# --------------------------------------------------------------------------
# 1. numerical guard
# --------------------------------------------------------------------------

def safe_exp(x: float) -> float | None:
    """exp() that reports instead of raising. None serialises as JSON null."""
    try:
        if not math.isfinite(x):
            return None
        if x > 709.0:
            return None
        if x < -745.0:
            return 0.0
        return math.exp(x)
    except OverflowError:
        return None


def json_safe(value: Any) -> Any:
    """Keep diagnostic NaN/Infinity values from producing nonstandard JSON."""
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (float, np.floating)) and not math.isfinite(value):
        return None
    return value


def guarded_contrast(fit, names, weights, alternative="two-sided"):
    """Frozen `contrast` with the exponentials guarded.

    log_odds_difference, standard_error, z and p are computed exactly as in the
    frozen script. Only odds_ratio / odds_ratio_ci95 may become null.
    """
    from scipy.stats import norm

    w = np.zeros(len(names), dtype=float)
    for name, value in weights.items():
        w[names.index(name)] = value
    estimate = float(w @ fit.params)
    variance = float(w @ fit.cov_params() @ w)
    se = math.sqrt(max(variance, 0.0))
    z = estimate / se if se > 0 else (
        math.inf if estimate > 0 else -math.inf if estimate < 0 else 0.0
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
        "odds_ratio": safe_exp(estimate),
        "odds_ratio_ci95": [safe_exp(lo), safe_exp(hi)],
        "z": z,
        "p": p,
        "alternative": alternative,
    }


# --------------------------------------------------------------------------
# 2. estimability and separation diagnostics
# --------------------------------------------------------------------------

def _group_label(value: Any) -> str:
    if isinstance(value, tuple):
        return "::".join(str(v) for v in value)
    return str(value)


def separation_diagnostics(
    fit,
    names: list[str],
    work: pd.DataFrame,
    outcome_col: str,
    *,
    test: str,
    effect_names: list[str],
    rate_group_cols: list[str],
    expected_groups: list[tuple[str, ...]],
    fit_error: str | None = None,
) -> dict[str, Any]:
    """Mechanical, direction-blind diagnostics for one confirmatory test.

    H1 and H2 require separate diagnostics because model-specific separation
    can occur only after the H2 interaction terms are added.
    """
    betas: dict[str, float | None] = {}
    ses: dict[str, float | None] = {}
    converged: bool | None = None
    if fit is not None:
        cov = np.asarray(fit.cov_params())
        params = np.asarray(fit.params)
        for name in effect_names:
            if name not in names:
                betas[name] = None
                ses[name] = None
                continue
            i = names.index(name)
            beta = float(params[i])
            variance = float(cov[i, i])
            betas[name] = beta if math.isfinite(beta) else None
            ses[name] = (
                float(math.sqrt(max(variance, 0.0)))
                if math.isfinite(variance) else None
            )
        converged = bool(getattr(fit, "converged", True))

    grouped = (
        work.groupby(rate_group_cols, dropna=False)[outcome_col]
        .agg(["mean", "count"])
    )
    rates = {_group_label(k): float(v["mean"]) for k, v in grouped.iterrows()}
    counts = {_group_label(k): int(v["count"]) for k, v in grouped.iterrows()}
    expected_labels = {_group_label(g) for g in expected_groups}
    missing_groups = sorted(expected_labels - set(rates))
    saturated_groups = sorted(
        k for k, v in rates.items() if v in (0.0, 1.0)
    )

    by_stratum = work.groupby(["stratum", "gap_structure"])[outcome_col].mean()
    degenerate_cells = int(((by_stratum == 0.0) | (by_stratum == 1.0)).sum())

    reasons: list[str] = []
    if fit is not None:
        design = np.asarray(fit.model.exog)
        if np.linalg.matrix_rank(design) < design.shape[1]:
            reasons.append("design_matrix_rank_deficient")
    if fit_error is not None:
        reasons.append("mle_fit_failed")
    if converged is False:
        reasons.append("glm_did_not_converge")
    if any(v is None for v in betas.values()):
        reasons.append("gap_effect_coefficient_missing_or_nonfinite")
    if any(v is None for v in ses.values()):
        reasons.append("gap_effect_standard_error_missing_or_nonfinite")
    if any(v is not None and abs(v) >= ABS_BETA_FLAG for v in betas.values()):
        reasons.append(f"gap_effect_coefficient_abs_ge_{ABS_BETA_FLAG:g}")
    if any(v is not None and v >= SE_FLAG for v in ses.values()):
        reasons.append(f"gap_effect_standard_error_ge_{SE_FLAG:g}")
    if saturated_groups:
        reasons.append("required_rate_group_saturated_at_0_or_1")
    if missing_groups:
        reasons.append("required_rate_group_has_zero_observations")

    return {
        "test": test,
        "mle_fit_error": fit_error,
        "converged": converged,
        "gap_effect_coefficients": betas,
        "gap_effect_standard_errors": ses,
        "rate_group_columns": rate_group_cols,
        "rate_by_required_group": rates,
        "observations_by_required_group": counts,
        "saturated_required_groups": saturated_groups,
        "missing_required_groups": missing_groups,
        "coverage_complete": not missing_groups,
        "degenerate_stratum_by_gap_cells": degenerate_cells,
        "total_observed_stratum_by_gap_cells": int(len(by_stratum)),
        "separation_or_estimability_flag": bool(reasons),
        # Retained as an alias for readers of the first A1 draft.
        "separation_flag": bool(reasons),
        "flag_reasons": reasons,
        "thresholds": {
            "abs_beta": ABS_BETA_FLAG,
            "standard_error": SE_FLAG,
        },
    }


def h2_mle_fit_for_diagnostics(
    work: pd.DataFrame,
    names: list[str],
    x: np.ndarray,
    outcome_col: str,
) -> tuple[Any, list[str], np.ndarray]:
    """Refit the frozen H2 full interaction design so it can be diagnosed."""
    model_dummies = pd.get_dummies(
        work["model_key"], prefix="model", drop_first=True, dtype=float
    )
    interaction_names: list[str] = []
    interaction_columns: list[np.ndarray] = []
    for mcol in model_dummies.columns:
        interaction_names.extend([
            f"{mcol}:gap_seamed",
            f"{mcol}:gap_explicit",
        ])
        interaction_columns.extend([
            model_dummies[mcol].to_numpy() * work["gap_seamed"].to_numpy(),
            model_dummies[mcol].to_numpy() * work["gap_explicit"].to_numpy(),
        ])
    interactions = np.column_stack(interaction_columns)
    x_full = np.hstack([x, interactions])
    y = work[outcome_col].astype(float).to_numpy()
    fit = sm.GLM(y, x_full, family=sm.families.Binomial()).fit()
    return fit, names + interaction_names, x_full


# --------------------------------------------------------------------------
# 3. Firth penalized likelihood
# --------------------------------------------------------------------------

def _sigmoid(eta: np.ndarray) -> np.ndarray:
    return np.clip(1.0 / (1.0 + np.exp(-np.clip(eta, -700, 700))), 1e-12, 1 - 1e-12)


def firth_penalized_loglik(x: np.ndarray, y: np.ndarray, beta: np.ndarray) -> float:
    mu = _sigmoid(x @ beta)
    ll = float(np.sum(y * np.log(mu) + (1.0 - y) * np.log(1.0 - mu)))
    a = x * np.sqrt(mu * (1.0 - mu))[:, None]
    sign, logdet = np.linalg.slogdet(a.T @ a)
    if sign <= 0 or not np.isfinite(logdet):
        return -math.inf
    return ll + 0.5 * float(logdet)


def firth_fit(x: np.ndarray, y: np.ndarray, m: np.ndarray | None = None,
              max_iter: int = 500, tol: float = 1e-9) -> dict[str, Any]:
    """Firth (1993) penalized-likelihood logistic fit with step halving.

    `m` is an optional p x q linear map expressing a constraint, beta = m @ theta.
    The Jeffreys penalty is always evaluated on the FULL design `x`, so penalized
    log-likelihoods of nested constrained fits are directly comparable and the
    penalized LR statistic uses an asymptotic chi-square reference distribution.
    Refitting a smaller design with its own penalty would change the comparison.
    """
    p = x.shape[1]
    if not p or np.linalg.matrix_rank(x) < p:
        raise ValueError("Firth full design is empty or rank deficient")
    if m is None:
        m = np.eye(p)
    q = m.shape[1]
    theta = np.zeros(q)
    beta = m @ theta
    current = firth_penalized_loglik(x, y, beta)
    converged = False
    iteration = 0
    for iteration in range(max_iter):
        mu = _sigmoid(x @ beta)
        w = mu * (1.0 - mu)
        a = x * np.sqrt(w)[:, None]
        fisher = a.T @ a
        finv_full = np.linalg.pinv(fisher)
        h = np.einsum("ij,jk,ik->i", a, finv_full, a)
        score = m.T @ (x.T @ (y - mu + h * (0.5 - mu)))
        info = m.T @ fisher @ m
        step = np.linalg.pinv(info) @ score
        factor = 1.0
        improved = False
        for _ in range(40):
            candidate = theta + factor * step
            value = firth_penalized_loglik(x, y, m @ candidate)
            if np.isfinite(value) and value >= current - 1e-12:
                improved = True
                break
            factor *= 0.5
        if not improved:
            break
        theta, current = candidate, value
        beta = m @ theta
        # A tiny step after severe halving is not evidence of a stationary fit.
        if np.max(np.abs(step)) < tol and np.max(np.abs(score)) <= 1e-6:
            converged = True
            break
    mu = _sigmoid(x @ beta)
    w = mu * (1.0 - mu)
    a = x * np.sqrt(w)[:, None]
    info = m.T @ (a.T @ a) @ m
    cov = m @ np.linalg.pinv(info) @ m.T
    h = np.einsum("ij,jk,ik->i", a, np.linalg.pinv(a.T @ a), a)
    final_score = m.T @ (x.T @ (y - mu + h * (0.5 - mu)))
    score_max_abs = float(np.max(np.abs(final_score)))
    converged = bool(converged and np.isfinite(current)
                     and np.all(np.isfinite(beta))
                     and np.all(np.isfinite(cov))
                     and score_max_abs <= 1e-6)
    return {
        "beta": beta,
        "theta": theta,
        "cov": cov,
        "penalized_loglik": float(current),
        "converged": bool(converged),
        "iterations": int(iteration + 1),
        "score_max_abs": score_max_abs,
    }


def constraint_drop(p: int, idx: int) -> np.ndarray:
    """Map for beta[idx] == 0."""
    return np.delete(np.eye(p), idx, axis=1)


def constraint_equal(p: int, i: int, j: int) -> np.ndarray:
    """Map for beta[i] == beta[j]."""
    m = np.delete(np.eye(p), [i, j], axis=1)
    col = np.zeros((p, 1))
    col[i, 0] = 1.0
    col[j, 0] = 1.0
    return np.hstack([m, col])


def checked_plr(full: dict[str, Any], null: dict[str, Any]) -> float | None:
    if not (full["converged"] and null["converged"]):
        return None
    statistic = 2.0 * (full["penalized_loglik"] - null["penalized_loglik"])
    if not math.isfinite(statistic) or statistic < -1e-7:
        raise ValueError("Invalid penalized likelihood comparison")
    return max(0.0, statistic)


def firth_contrast(x_full: np.ndarray, m_null: np.ndarray, y: np.ndarray,
                   names: list[str], weights: dict[str, float],
                   label: str) -> dict[str, Any]:
    """One-sided penalized likelihood-ratio test of a single linear contrast."""
    full = firth_fit(x_full, y)
    null = firth_fit(x_full, y, m=m_null)
    w = np.zeros(len(names), dtype=float)
    for name, value in weights.items():
        w[names.index(name)] = value
    estimate = float(w @ full["beta"])
    se = float(math.sqrt(max(float(w @ full["cov"] @ w), 0.0)))
    fits_converged = bool(full["converged"] and null["converged"])
    plr = checked_plr(full, null)
    if plr is None:
        p = None
    else:
        two_sided = float(chi2.sf(plr, 1))
        p = 0.5 * two_sided if estimate > 0 else 1.0 - 0.5 * two_sided
    lo = estimate - 1.959963984540054 * se
    hi = estimate + 1.959963984540054 * se
    return {
        "contrast": label,
        "penalized_log_odds_difference": estimate,
        "wald_standard_error": se,
        "odds_ratio": safe_exp(estimate),
        "odds_ratio_ci95_wald": [safe_exp(lo), safe_exp(hi)],
        "penalized_lr_statistic": plr,
        "df": 1,
        "p": float(p) if p is not None else None,
        "alternative": "greater",
        "full_converged": full["converged"],
        "null_converged": null["converged"],
        "full_score_max_abs": full["score_max_abs"],
        "null_score_max_abs": null["score_max_abs"],
        "decision_status": "estimable" if fits_converged else "indeterminate",
        "indeterminate_reason": (
            None if fits_converged
            else "one_or_more_decision_bearing_firth_fits_did_not_converge"
        ),
    }


def firth_h1(work: pd.DataFrame, names: list[str], x: np.ndarray,
             outcome_col: str) -> dict[str, Any]:
    missing_levels = sorted(
        set(frozen.EXPECTED_GAPS) - set(work["gap_structure"].astype(str))
    )
    if missing_levels:
        return {
            "estimator": "Firth penalized likelihood (Firth 1993), penalized LR tests",
            "alpha": ALPHA,
            "decision_status": "indeterminate",
            "indeterminate_reason": "one_or_more_gap_levels_have_zero_observations",
            "missing_gap_levels": missing_levels,
            "seamed_gt_closed": None,
            "explicit_gt_seamed": None,
            "explicit_vs_closed_secondary": None,
            "h1_supported": None,
        }

    y = work[outcome_col].astype(float).to_numpy()
    p = x.shape[1]
    i_s, i_e = names.index("gap_seamed"), names.index("gap_explicit")

    # seamed > closed  :  constrain beta_seamed = 0
    seam_vs_closed = firth_contrast(
        x, constraint_drop(p, i_s), y, names,
        {"gap_seamed": 1.0}, "seamed_gt_closed"
    )

    # explicit > seamed :  constrain beta_explicit = beta_seamed
    explicit_vs_seam = firth_contrast(
        x, constraint_equal(p, i_s, i_e), y, names,
        {"gap_explicit": 1.0, "gap_seamed": -1.0}, "explicit_gt_seamed"
    )

    full = firth_fit(x, y)
    w = np.zeros(len(names))
    w[i_e] = 1.0
    est = float(w @ full["beta"])
    se = float(math.sqrt(max(float(w @ full["cov"] @ w), 0.0)))
    p_seam = seam_vs_closed["p"]
    p_explicit = explicit_vs_seam["p"]
    decision_estimable = p_seam is not None and p_explicit is not None
    supported = (
        bool(p_seam < ALPHA and p_explicit < ALPHA)
        if decision_estimable else None
    )
    return {
        "estimator": "Firth penalized likelihood (Firth 1993), penalized LR tests",
        "alpha": ALPHA,
        "decision_rule": (
            "Identical intersection-union rule to the frozen analysis: H1 is "
            "supported only if both prespecified one-sided adjacent contrasts "
            "have p < alpha. No multiplicity correction."
        ),
        "seamed_gt_closed": seam_vs_closed,
        "explicit_gt_seamed": explicit_vs_seam,
        "explicit_vs_closed_secondary": {
            "penalized_log_odds_difference": est,
            "wald_standard_error": se,
            "odds_ratio": safe_exp(est),
            "odds_ratio_ci95_wald": [
                safe_exp(est - 1.959963984540054 * se),
                safe_exp(est + 1.959963984540054 * se),
            ],
        },
        "decision_status": "estimable" if decision_estimable else "indeterminate",
        "indeterminate_reason": (
            None if decision_estimable
            else "one_or_more_decision_bearing_firth_fits_did_not_converge"
        ),
        "h1_supported": supported,
    }


def firth_h2(work: pd.DataFrame, names: list[str], x: np.ndarray,
             outcome_col: str) -> dict[str, Any]:
    expected_cells = {
        (model, gap)
        for model in frozen.EXPECTED_MODELS
        for gap in frozen.EXPECTED_GAPS
    }
    observed_cells = set(zip(
        work["model_key"].astype(str),
        work["gap_structure"].astype(str),
    ))
    missing_cells = sorted(
        f"{model}::{gap}" for model, gap in expected_cells - observed_cells
    )
    if missing_cells:
        return {
            "test": (
                "penalized likelihood-ratio comparison of common categorical gap "
                "effects vs model-specific categorical gap effects (Firth)"
            ),
            "penalized_lr_statistic": None,
            "df": 6,
            "p": None,
            "alpha": ALPHA,
            "full_converged": None,
            "reduced_converged": None,
            "decision_status": "indeterminate",
            "indeterminate_reason": "one_or_more_model_by_gap_cells_have_zero_observations",
            "missing_model_by_gap_cells": missing_cells,
        }

    y = work[outcome_col].astype(float).to_numpy()
    model_dummies = pd.get_dummies(
        work["model_key"], prefix="model", drop_first=True, dtype=float
    )
    cols = []
    for mcol in model_dummies.columns:
        cols.append(model_dummies[mcol].to_numpy() * work["gap_seamed"].to_numpy())
        cols.append(model_dummies[mcol].to_numpy() * work["gap_explicit"].to_numpy())
    interactions = np.column_stack(cols)
    x_full = np.hstack([x, interactions])
    p_full = x_full.shape[1]
    df_diff = int(interactions.shape[1])
    # reduced = all interaction coefficients constrained to zero, penalty still
    # evaluated on the full design
    m_reduced = np.eye(p_full)[:, : p_full - df_diff]
    reduced = firth_fit(x_full, y, m=m_reduced)
    full = firth_fit(x_full, y)
    fits_converged = bool(full["converged"] and reduced["converged"])
    plr = checked_plr(full, reduced)
    return {
        "test": (
            "penalized likelihood-ratio comparison of common categorical gap "
            "effects vs model-specific categorical gap effects (Firth)"
        ),
        "penalized_lr_statistic": plr,
        "df": df_diff,
        "p": float(chi2.sf(plr, df_diff)) if plr is not None else None,
        "alpha": ALPHA,
        "full_converged": full["converged"],
        "reduced_converged": reduced["converged"],
        "full_score_max_abs": full["score_max_abs"],
        "reduced_score_max_abs": reduced["score_max_abs"],
        "decision_status": "estimable" if fits_converged else "indeterminate",
        "indeterminate_reason": (
            None if fits_converged
            else "one_or_more_decision_bearing_firth_fits_did_not_converge"
        ),
    }


# --------------------------------------------------------------------------
# 4. stratified conditional permutation (corroborating, never decision-bearing)
# --------------------------------------------------------------------------

def permutation_contrast(work: pd.DataFrame, outcome_col: str,
                         level_a: str, level_b: str,
                         permutations: int = PERMUTATIONS,
                         seed: int = PERM_SEED) -> dict[str, Any]:
    """One-sided stratified conditional permutation test of P(A) > P(B).

    Within each model x topic stratum the outcome labels of the two gap
    conditions are exchangeable under the null. Conditioning on the stratum
    margin gives a hypergeometric null distribution for the group-A success
    count. The reported p-value is estimated with prespecified Monte Carlo
    sampling from that distribution; it is not an exhaustively enumerated
    exact p-value.
    """
    sub = work[work["gap_structure"].isin([level_a, level_b])]
    cells = sub.groupby(["stratum", "gap_structure"])[outcome_col].agg(["sum", "count"])
    na, ka, nb, kb = [], [], [], []
    for stratum, g in cells.groupby(level=0):
        try:
            sa, ca = g.loc[(stratum, level_a)]
            sb, cb = g.loc[(stratum, level_b)]
        except KeyError:
            continue
        if ca == 0 or cb == 0:
            continue
        ka.append(float(sa)); na.append(int(ca))
        kb.append(float(sb)); nb.append(int(cb))
    if not na:
        return {"error": "no usable strata", "p": None}

    ka = np.array(ka); kb = np.array(kb)
    na = np.array(na); nb = np.array(nb)
    observed = float(np.mean(ka / na - kb / nb))

    total_k = (ka + kb).astype(int)
    total_n = na + nb
    rng = np.random.default_rng(seed)
    draw = rng.hypergeometric(
        ngood=total_k,
        nbad=total_n - total_k,
        nsample=na,
        size=(permutations, len(na)),
    )
    stats = np.mean(draw / na - (total_k - draw) / nb, axis=1)
    p = float((1 + int(np.sum(stats >= observed - 1e-12))) / (permutations + 1))
    return {
        "contrast": f"{level_a}_gt_{level_b}",
        "statistic": "mean over model x topic strata of (rate_A - rate_B)",
        "observed": observed,
        "strata_used": int(len(na)),
        "monte_carlo_draws": int(permutations),
        "seed": int(seed),
        "p": p,
        "p_value_method": (
            "plus-one Monte Carlo p-value from the stratified conditional "
            "hypergeometric null"
        ),
        "exchangeability_assumption": (
            "Within each model x topic stratum, outcomes are exchangeable "
            "between the two compared gap conditions under the null."
        ),
        "alternative": "greater",
    }


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------

def analyse_outcome(df: pd.DataFrame, outcome_col: str) -> dict[str, Any]:
    # Frozen MLE path, with only the exponentials guarded. H1 and H2 are
    # captured separately so one failed fit cannot prevent a report.
    original_contrast = frozen.contrast
    frozen.contrast = guarded_contrast
    mle_h1 = None
    mle_h2 = None
    h1_fit = None
    h1_names: list[str] = []
    work: pd.DataFrame | None = None
    h1_mle_error: str | None = None
    h2_mle_error: str | None = None
    try:
        try:
            mle_h1, h1_fit, h1_names, work = frozen.h1_results(df, outcome_col)
        except Exception as exc:  # report rather than lose the output file
            h1_mle_error = f"{type(exc).__name__}: {exc}"
        try:
            mle_h2 = frozen.h2_model_interaction(df, outcome_col)
        except Exception as exc:  # report rather than lose the output file
            h2_mle_error = f"{type(exc).__name__}: {exc}"
    finally:
        frozen.contrast = original_contrast

    # Build the common design independently if frozen H1 failed before return.
    design_error: str | None = None
    try:
        _, x, design_names, design_work = frozen.build_design(df, outcome_col)
        if work is None:
            work = design_work
        if not h1_names:
            h1_names = design_names
    except Exception as exc:
        design_error = f"{type(exc).__name__}: {exc}"
        x = np.empty((0, 0), dtype=float)
        work = df.copy()

    if "stratum" not in work.columns:
        work["stratum"] = (
            work.get("model_key", pd.Series(dtype=str)).astype(str)
            + "::"
            + work.get("topic_id", pd.Series(dtype=str)).astype(str)
        )

    h1_effect_names = ["gap_seamed", "gap_explicit"]
    h1_diagnostics = separation_diagnostics(
        h1_fit,
        h1_names,
        work,
        outcome_col,
        test="H1 common gap effects",
        effect_names=h1_effect_names,
        rate_group_cols=["gap_structure"],
        expected_groups=[(gap,) for gap in sorted(frozen.EXPECTED_GAPS)],
        fit_error=h1_mle_error or design_error,
    )

    h2_fit = None
    h2_names: list[str] = []
    h2_design_error: str | None = design_error
    if design_error is None:
        try:
            h2_fit, h2_names, _ = h2_mle_fit_for_diagnostics(
                work, h1_names, x, outcome_col
            )
        except Exception as exc:
            h2_design_error = f"{type(exc).__name__}: {exc}"
    h2_effect_names = [
        name for name in h2_names
        if name in h1_effect_names or ":gap_" in name
    ]
    h2_diagnostics = separation_diagnostics(
        h2_fit,
        h2_names,
        work,
        outcome_col,
        test="H2 model-specific gap effects",
        effect_names=h2_effect_names,
        rate_group_cols=["model_key", "gap_structure"],
        expected_groups=[
            (model, gap)
            for model in sorted(frozen.EXPECTED_MODELS)
            for gap in sorted(frozen.EXPECTED_GAPS)
        ],
        fit_error=h2_design_error or h2_mle_error,
    )
    if h1_fit is None or not bool(getattr(h1_fit, "converged", False)):
        h2_diagnostics["flag_reasons"].append("h2_reduced_mle_failed_or_not_converged")
        h2_diagnostics["separation_flag"] = True
        h2_diagnostics["separation_or_estimability_flag"] = True

    try:
        firth_h1_result = firth_h1(work, h1_names, x, outcome_col)
    except Exception as exc:
        firth_h1_result = {
            "estimator": "Firth penalized likelihood (Firth 1993), penalized LR tests",
            "decision_status": "indeterminate",
            "indeterminate_reason": f"firth_analysis_error: {type(exc).__name__}: {exc}",
            "h1_supported": None,
        }
    try:
        firth_h2_result = firth_h2(work, h1_names, x, outcome_col)
    except Exception as exc:
        firth_h2_result = {
            "test": (
                "penalized likelihood-ratio comparison of common categorical gap "
                "effects vs model-specific categorical gap effects (Firth)"
            ),
            "decision_status": "indeterminate",
            "indeterminate_reason": f"firth_analysis_error: {type(exc).__name__}: {exc}",
            "p": None,
        }

    perms = {
        "seamed_gt_closed": permutation_contrast(
            work, outcome_col, "seamed", "closed"
        ),
        "explicit_gt_seamed": permutation_contrast(
            work, outcome_col, "explicit_gap", "seamed"
        ),
    }

    h1_flagged = h1_diagnostics["separation_or_estimability_flag"]
    h2_flagged = h2_diagnostics["separation_or_estimability_flag"]
    h1_governing_name = (
        "firth_penalized_likelihood" if h1_flagged
        else "frozen_stratified_mle"
    )
    h2_governing_name = (
        "firth_penalized_likelihood" if h2_flagged
        else "frozen_stratified_mle"
    )
    governing_h1 = firth_h1_result if h1_flagged else mle_h1
    governing_h2 = firth_h2_result if h2_flagged else mle_h2
    h1_supported = (
        governing_h1.get("h1_supported")
        if isinstance(governing_h1, dict) else None
    )
    h2_p = (
        governing_h2.get("p")
        if isinstance(governing_h2, dict) else None
    )

    return {
        "separation_diagnostics": {
            "h1": h1_diagnostics,
            "h2": h2_diagnostics,
        },
        "governing_estimators": {
            "h1": h1_governing_name,
            "h2": h2_governing_name,
        },
        "h1_decision_status": (
            "indeterminate" if h1_supported is None
            else "supported" if bool(h1_supported)
            else "not_supported"
        ),
        "h1_supported_governing": (
            bool(h1_supported) if h1_supported is not None else None
        ),
        "h2_decision_status": "estimable" if h2_p is not None else "indeterminate",
        "h2_p_governing": h2_p,
        "frozen_mle": {
            "h1": mle_h1,
            "h1_error": h1_mle_error,
            "h2": mle_h2,
            "h2_error": h2_mle_error,
        },
        "firth_fallback": {"h1": firth_h1_result, "h2": firth_h2_result},
        "permutation_corroboration": perms,
    }


def truncation_diagnostics(successes: pd.DataFrame) -> dict[str, Any]:
    """Tabulate provider-reported output-limit truncation without recoding it."""
    rows: list[dict[str, Any]] = []
    for _, row in successes.iterrows():
        raw = row.get("raw_response")
        raw = raw if isinstance(raw, dict) else {}
        provider = str(row.get("provider", ""))
        reason: str | None = None
        incomplete = False
        token_limit = False
        if provider == "anthropic" and raw.get("stop_reason") == "max_tokens":
            reason = "anthropic_stop_reason_max_tokens"
            token_limit = True
        elif provider == "openai":
            details = raw.get("incomplete_details")
            details = details if isinstance(details, dict) else {}
            if raw.get("status") == "incomplete":
                incomplete = True
                detail_reason = details.get("reason") or "unspecified"
                reason = f"openai_status_incomplete:{detail_reason}"
            elif details.get("reason") == "max_output_tokens":
                reason = "openai_incomplete_reason_max_output_tokens"
            token_limit = details.get("reason") == "max_output_tokens"
        rows.append({
            "model_key": row.get("model_key"),
            "gap_structure": row.get("gap_structure"),
            "truncated": token_limit,
            "incomplete": incomplete,
            "truncation_reason": reason,
        })

    audit = pd.DataFrame(rows)
    if audit.empty:
        return {
            "definition": "provider metadata indicates an output-token-limit stop",
            "successful_responses": 0,
            "truncated_responses": 0,
            "openai_incomplete_responses": 0,
            "truncation_rate": None,
            "by_model_gap": [],
            "reason_counts": {},
            "decision_bearing": False,
        }

    by_model_gap: list[dict[str, Any]] = []
    for (model, gap), group in audit.groupby(["model_key", "gap_structure"]):
        n = int(len(group))
        truncated = int(group["truncated"].sum())
        by_model_gap.append({
            "model_key": model,
            "gap_structure": gap,
            "successful_responses": n,
            "truncated_responses": truncated,
            "openai_incomplete_responses": int(group["incomplete"].sum()),
            "truncation_rate": truncated / n if n else None,
        })
    reason_counts = {
        str(k): int(v)
        for k, v in audit.loc[audit["truncation_reason"].notna(), "truncation_reason"]
        .value_counts()
        .to_dict()
        .items()
    }
    total = int(len(audit))
    truncated_total = int(audit["truncated"].sum())
    return {
        "definition": "provider metadata indicates an output-token-limit stop",
        "successful_responses": total,
        "truncated_responses": truncated_total,
        "openai_incomplete_responses": int(audit["incomplete"].sum()),
        "truncation_rate": truncated_total / total if total else None,
        "by_model_gap": by_model_gap,
        "reason_counts": reason_counts,
        "decision_bearing": False,
        "note": (
            "This diagnostic does not alter frozen parsing or denominators. "
            "It distinguishes provider-reported truncation from ordinary "
            "format invalidity for interpretation and sensitivity reporting."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Attainable Unknowns API Pilot 0.1 confirmatory analysis under "
            "Amendment A1 (separation-robust)."
        )
    )
    parser.add_argument("manifests", nargs=4, type=Path)
    parser.add_argument("--expected-hashes", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("api-study/data/analysis/confirmatory-results-a1.json"),
    )
    args = parser.parse_args()

    expected_hashes = load_expected_hashes(args.expected_hashes)
    records, manifests = frozen.validate_manifests(args.manifests, expected_hashes)

    successes = records[records["status"] == "success"].copy()
    primary = successes[successes["format_valid"] == True].copy()  # noqa: E712
    primary["question_emission"] = (
        (primary["parsed_none"] != True)  # noqa: E712
        & primary["parsed_question"].notna()
    ).astype(int)
    successes["sensitivity_outcome"] = (
        successes["sensitivity_activation"].astype(bool).astype(int)
    )

    primary_block = analyse_outcome(primary, "question_emission")
    sensitivity_block = analyse_outcome(successes, "sensitivity_outcome")

    # A1 reporting addition: truncation / empty-response audit
    text = successes.get("response_text")
    empty_successes = (
        int((text.fillna("").astype(str).str.strip() == "").sum())
        if text is not None else None
    )

    result = {
        "analysis_version": "api-pilot-0.1-amendment-a1",
        "amendment": {
            "id": AMENDMENT,
            "initial_draft_utc": AMENDMENT_UTC,
            "corrected_revision_utc": REVISION_UTC,
            "final_review_utc": FINAL_REVIEW_UTC,
            "supersedes_for_decision": "analyze_confirmatory.py",
            "frozen_source_unchanged": True,
            "frozen_contrast_exponentials_guarded_in_memory": True,
            "note": (
                "Frozen validation, stratified MLE and descriptive table are "
                "executed by importing the frozen module. H1 and H2 are diagnosed "
                "separately; each decision changes only when its own mechanical "
                "estimability/separation flag is raised."
            ),
        },
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
            "empty_successful_responses": empty_successes,
        },
        "truncation_diagnostics": truncation_diagnostics(successes),
        "descriptive_by_model_gap": frozen.descriptive_table(records),
        "primary_estimand": (
            "P(question emission | successful, format-valid response) "
            "for the frozen passages and API draws"
        ),
        "primary_outcome": primary_block,
        "sensitivity_any_nonempty_non_none": {
            "estimand": "P(nonempty non-NONE response | successful response)",
            **sensitivity_block,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(json_safe(result), indent=2, sort_keys=True,
                   default=str, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "complete",
        "output": str(args.output),
        "attempted_records": int(len(records)),
        "primary_format_valid_records": int(len(primary)),
        "h1_separation_or_estimability_flag": primary_block["separation_diagnostics"]["h1"]["separation_or_estimability_flag"],
        "h1_flag_reasons": primary_block["separation_diagnostics"]["h1"]["flag_reasons"],
        "h2_separation_or_estimability_flag": primary_block["separation_diagnostics"]["h2"]["separation_or_estimability_flag"],
        "h2_flag_reasons": primary_block["separation_diagnostics"]["h2"]["flag_reasons"],
        "governing_estimators": primary_block["governing_estimators"],
        "h1_decision_status": primary_block["h1_decision_status"],
        "h1_supported": primary_block["h1_supported_governing"],
        "h2_decision_status": primary_block["h2_decision_status"],
        "h2_p": primary_block["h2_p_governing"],
    }, indent=2))


if __name__ == "__main__":
    main()
