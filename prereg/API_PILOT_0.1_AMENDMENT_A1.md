# API Pilot 0.1 — Post-Freeze Amendment A1

**Study:** Attainable Unknowns API Pilot 0.1
**Amendment ID:** A1
**Status:** Final reviewed amendment prepared for founder-signed adoption before substantive data inspection; the adoption commit supplies the authoritative timestamp
**Initial draft prepared (UTC):** 2026-09-18T21:10:55Z
**Revision prepared (UTC):** 2026-09-18T21:44:21Z
**Final review begun (UTC):** 2026-09-18T22:36:16Z
**Freeze this amends:** `prereg/API_PILOT_0.1_FREEZE_RECORD.json`, generated 2026-09-18T20:01:44Z from pre-freeze commit `6784ecbf11475367ccd14d46317fce27976f383b` and adopted in signed freeze commit `d24269a93fa25f61306145a68bd0f4ea896b3e01`
**Prepared for adoption by:** Bo Chesterton
**Analytic contributors:** claude-opus-5 (initial synthetic stress test and draft); OpenAI Codex/ChatGPT Work (independent review, corrections, and revised code)

---

## 1. Attestation

At the time the initial A1 draft was prepared:

- full-design collection had already begun under the frozen runner;
- at least one full-design model run had completed, Terra had been observed at approximately 750/900 attempts and still advancing earlier in the same outcome-blind collection period, and Sonnet had not yet begun pending this review;
- no substantive full-design response content or outcome summaries had been inspected; permitted technical monitoring included completed-record counts and file timestamps;
- no question-emission counts, rates, or response texts from any accepted run had been inspected;
- the defect this amendment addresses was identified from **simulated** outcome patterns run against the frozen analysis script, not from study data; and
- the initial analytic contributor was given the frozen repository but had not been informed of collection progress. That is why the first draft incorrectly stated that no full-design run had completed. The sentence was corrected before founder adoption; the substantive outcome-blindness claim is unchanged.

This amendment was therefore prepared blind to the study outcome. It is a post-freeze deviation under §14 of the preregistration and is disclosed rather than silently incorporated. Collection status is relevant to provenance, but completed collection alone does not reveal an outcome.

## 2. Nothing frozen is modified

`api-study/analyze_confirmatory.py` is **not edited**. Its SHA-256 in the freeze record remains valid.

This amendment adds one new file, `api-study/analyze_confirmatory_a1.py`, which imports the frozen module and retains the frozen manifest validation, stratified-MLE model, contrast arithmetic, and descriptive table. The only change on the frozen MLE reporting path is an overflow-safe exponential for odds ratios and their confidence limits. The frozen script's own estimable quantities are reported inside the amended output under `frozen_mle`; any frozen-fit exception is reported rather than allowed to erase the amended output.

## 3. Occasion for the amendment

Three defects were found in the frozen confirmatory analysis and initial A1 draft. The first two are triggered by **ceiling effects in question emission** — a plausible and arguably likely outcome of this design, since a passage that states its remaining issue plainly invites a follow-up question, and the prompt asks for exactly one. The third concerns test-specific detection of the same pathology.

### Defect 1 — the script aborts

`contrast()` computes `math.exp()` on the endpoints of the odds-ratio confidence interval. When a gap coefficient diverges, the upper endpoint overflows and the process raises `OverflowError: math range error` before `--output` is written. No results file is produced.

### Defect 2 — the predicted result is recorded as unsupported

If any gap level's pooled question-emission proportion reaches exactly 0 or 1, the stratified binomial GLM has quasi-complete separation on that level. The coefficient diverges, the standard error diverges with it, and the Wald z-statistic collapses toward zero.

The initial Opus review reported the following synthetic results using the frozen design and code (3,600 draws):

| simulated truth | frozen MLE, seamed > closed | frozen MLE, explicit > seamed | H1 |
|---|---|---|---|
| closed .89 / seamed .98 / explicit **1.00** | β=1.87, SE=0.23, p<.0001 | β=23.59, SE=16570.31, **p=.4994** | **not supported** |
| closed .89 / seamed **1.00** / explicit **1.00** | β=26.46, SE=27144.12, **p=.4996** | β=0.00, SE=38387.58, **p=.5000** | **not supported** |

The first row has the strict ordering H1 predicts, with the explicit-gap level at ceiling, and the frozen analysis returns p≈.5 and `h1_supported: false` — then crashes before writing it down.

`fit.converged` returned `True` in both degenerate cases, so convergence status is not a usable tripwire.

The initial review also reported simulations with 2/48 and 8/48 model × topic strata at all-ones where the frozen fit returned sensible estimates. These cases illustrate that some local saturation is tolerable; they do not establish that all partial separation patterns are safe.

### Defect 3 — one H1 flag cannot govern H2

The first A1 draft derived one separation flag from the common-gap H1 fit and used it to choose the estimator for both H1 and H2. Synthetic follow-up testing showed that this is insufficient. A model-specific gap cell can saturate and drive an H2 interaction coefficient and standard error toward infinity while the common-gap H1 fit remains well behaved. In one constructed case, the H1 diagnostic remained unflagged while an H2 interaction coefficient was approximately 24.5 with an SE of approximately 12,400.

A1 therefore diagnoses H1 and H2 separately. An H1 problem changes only the H1 estimator; an H2 problem changes only the H2 estimator.

## 4. The amendment

### 4.1 Numerical guard

Exponentials of estimates and CI endpoints are guarded. A non-finite or overflowing odds ratio is reported as JSON `null` instead of aborting the run. `log_odds_difference`, `standard_error`, `z` and `p` are computed by the frozen arithmetic, unchanged. Non-finite diagnostic values are serialized as JSON `null`, never nonstandard `NaN` or `Infinity`.

The `--expected-hashes` input may be either the flat three-key adapter expected by the frozen analyzer or `prereg/API_PILOT_0.1_FREEZE_RECORD.json` itself. When given the freeze record, A1 reads its optional UTF-8 BOM and deterministically extracts the config, passage-bank, and runner digests from `frozen_study_files_sha256`. This changes no validation rule.

### 4.2 Separate H1 and H2 flags (mechanical)

For each outcome, H1 and H2 receive separate estimability/separation flags.

The H1 flag is evaluated on the frozen common-gap fit and is raised if **any** of the following holds:

1. the GLM reports `converged is False`; or
2. `|β̂| ≥ 10` for `gap_seamed` or `gap_explicit`; or
3. `SE(β̂) ≥ 10` for `gap_seamed` or `gap_explicit`; or
4. the pooled observed outcome proportion for any gap level equals exactly 0.0 or exactly 1.0; or
5. any of the three required gap levels has zero observations in the relevant analysis set.

A fit exception, a missing or non-finite relevant coefficient/standard error, or a rank-deficient design also raises the flag. Rank deficiency cannot be repaired by the fallback and yields an indeterminate result.

The H2 flag is evaluated on the full frozen model × gap interaction design and uses the same convergence and numeric thresholds for all gap main-effect and model × gap interaction coefficients. It additionally flags if any pooled model × gap outcome proportion is exactly 0.0 or 1.0, or if any required model × gap cell has zero observations. H2 also requires a successfully converged reduced MLE fit for the frozen likelihood comparison.

Every criterion is a direction-blind diagnostic of **estimability**. The flag state, criteria fired, relevant coefficients and standard errors, pooled rates, missing required cells, and the count of degenerate stratum × gap cells are reported whether or not a flag is raised.

### 4.3 Fallback estimator — decision-bearing only when flagged

When a test's flag is raised, the decision-bearing estimator for that test becomes **Firth penalized likelihood** (Firth 1993), on the same design as the frozen analysis. H1 uses model × topic fixed intercepts plus common categorical gap indicators; H2 adds the frozen model × gap interactions.

- H1 adjacent contrasts are tested by **one-sided penalized likelihood-ratio tests**. `seamed > closed` constrains β(seamed)=0; `explicit_gap > seamed` constrains β(explicit)=β(seamed). Each constrained fit is taken over the **full** design under a linear constraint, so the Jeffreys penalty is evaluated on the same information matrix in both fits and the statistic is compared with an asymptotic χ²₁ reference distribution; finite-sample calibration is not guaranteed.
- H2 is the corresponding penalized LR test of model-specific versus common categorical gap effects, df = 6.
- Reported Firth confidence intervals are Wald intervals and are descriptive only; the tests are likelihood-ratio tests.
- If any decision-bearing Firth full or constrained/reduced fit fails to converge, the affected confirmatory test is **indeterminate under A1**. Its p-value and decision are recorded as JSON `null`; unconverged numerical remnants do not determine a result.
- Firth convergence requires the unhalved parameter step to be below 1e-9 and the maximum absolute constrained score to be at most 1e-6, with a finite fit. A tiny step caused solely by step halving is insufficient. A singular full design, invalid information determinant, or non-finite/materially negative likelihood comparison cannot produce a confirmatory decision (LR values below -1e-7 are rejected; smaller negative roundoff is clipped to zero).
- If a required H1 gap level, or a required H2 model × gap cell, has zero observations, the affected test is likewise **indeterminate**. Bias reduction cannot identify a comparison for which the required observed group is absent.

**The decision rule is unchanged.** H1 remains an intersection-union test: supported only if both prespecified one-sided adjacent contrasts have p < .05, with no multiplicity correction. Alpha is unchanged at .05.

When a test's flag is **not** raised, the frozen stratified MLE governs and that test's decision is numerically and decision-identical to the frozen analysis.

### 4.4 Corroborating conditional permutation test — never decision-bearing

Each H1 adjacent contrast is additionally reported as a **stratified conditional permutation test with a Monte Carlo p-value**. Under the stated null, the test assumes that outcomes are exchangeable between the two compared gap conditions within each model × topic stratum. Conditioning on the stratum margin gives a hypergeometric null distribution for the group-A success count. The script samples that distribution 100,000 times with seed 91826 (the `order_seed` from `config.yaml`) rather than exhaustively enumerating it. Statistic: the mean across strata of (rate_A − rate_B). The plus-one Monte Carlo p-value is robust to cells at 0 or 1, but it is neither assumption-free nor an exhaustively enumerated exact p-value.

This is reported always, in flagged and unflagged analyses alike. It **never** determines whether H1 is supported. Its purpose is to provide a differently specified corroborating analysis, and a disagreement between the two is itself a reportable finding.

### 4.5 Applies identically to the sensitivity outcome

All of §4.1–§4.4 apply unchanged to the preregistered sensitivity estimand `P(nonempty non-NONE response | successful response)`.

### 4.6 Truncation diagnostic — never decision-bearing

Provider-reported output-limit stops are tabulated overall and by model × gap condition: Anthropic `stop_reason == "max_tokens"` and OpenAI `incomplete_details.reason == "max_output_tokens"`. OpenAI `status == "incomplete"` is also counted separately, retaining its reason; an incomplete response is not automatically classified as token-limit truncation. This diagnostic does not change the frozen parser, the primary denominator, or any confirmatory decision. It distinguishes token-limit truncation from ordinary format invalidity so that differential exclusion of longer questions can be assessed transparently.

## 5. Calibration evidence and its provenance

The following calibration table and seven-pattern comparison were supplied in the initial Opus draft. The underlying simulation harness and replicate outputs were not supplied with these two files, and this final review did not independently rerun the 400-dataset calibration. They are retained as contributor-reported evidence, not as a verified calibration of the revised switching procedure.

Opus reported 400 simulated null datasets at the full design size (4 models × 12 topics × 3 gap levels × 25 draws), all three gap levels generated at equal probability .60, topic-level logit SD 1.0. Nominal one-sided α = .05; Monte-Carlo SE at .05 is 0.011.

| test | empirical type-I at .05 | at .10 | median p |
|---|---|---|---|
| frozen MLE, seamed > closed | .060 | .098 | .519 |
| Firth PLR, seamed > closed | .058 | .098 | .519 |
| permutation, seamed > closed | .048 | .087 | .543 |
| frozen MLE, explicit > seamed | .040 | .102 | .518 |
| Firth PLR, explicit > seamed | .040 | .102 | .518 |
| permutation, explicit > seamed | .035 | .085 | .547 |
| frozen MLE, H2 (df=6) | .062 | .105 | .430 |
| Firth PLR, H2 (df=6) | .058 | .098 | .441 |

The reported estimates are close to nominal in this particular simulation setting. They do not establish error control across ceiling patterns, missingness patterns, or the revised estimator-selection rule. The chi-square tests remain asymptotic.

Opus also reported agreement away from the ceiling: across seven non-degenerate outcome patterns spanning strong-positive, null and reversed orderings, Firth point estimates differed from the frozen MLE by under 5% of the coefficient and the two never disagreed about H1 at α = .05. Under the saturated pattern in §3 row 1, the amendment flags, switches to Firth, and returns β=3.51, p=6.0×10⁻⁶ for `explicit > seamed` — recovering the result the frozen script reported as p=.4994. Under §3 row 2, where two levels are both saturated, Firth reports strong support for `seamed > closed` and no evidence for `explicit > seamed`, so H1 is correctly not supported; the permutation test agrees.

### Final-review implementation checks

The revised wrapper was checked using synthetic data only. Targeted cases covered ordinary full-design data (frozen-MLE quantities identical), common ceiling separation, H2-only separation, all-one and all-zero outcomes, missing gap levels, an empty primary analysis set, forced Firth nonconvergence, singular design rejection, and a stalled line search with a large remaining score. The stalled fit correctly remains nonconverged. Provider metadata tests distinguish output-token limits from other incomplete responses. A four-manifest, 3,600-record synthetic command-line run checks validation, freeze-record input, and JSON output. These are implementation checks, not an independent type-I error calibration. Test environment: Python 3.12, statsmodels 0.15.0, NumPy 2.5.3, pandas 3.0.6, SciPy 1.18.1.

## 6. What this amendment does not change

- the construct, the mechanical primary endpoint, or the interpretation boundary;
- the primary estimand or the sensitivity estimand;
- H1, H2, the strict ordering claim, the intersection-union rule, or α;
- the passages, prompts, system prompt, reasoning configuration, replicate count, or sample size;
- the format-validity parser or the mechanical coding rules;
- the exclusion rules, including the ≥10 technical-failure compromise rule;
- `SPECIFICITY_CODEBOOK.md` or the blinded specificity coding procedure;
- the requirement that exactly four accepted full-design runs, one per model, pass manifest and SHA-256 validation.

## 7. Reporting additions (not decision-bearing)

- `empty_successful_responses`: the count of successful API responses whose text is empty after trimming. These parse as format-invalid and leave the primary denominator; they are currently indistinguishable in the summary from substantive format violations.
- `truncation_diagnostics`: provider-reported output-limit stops overall and by model × gap condition, with the provider reason retained.
- Separate H1 and H2 diagnostics and governing-estimator fields, so separation confined to the interaction model cannot be masked by a healthy common-gap fit.
- Explicit `estimable`/`indeterminate` states; JSON `null` replaces any decision that would otherwise rely on a nonconverged decision-bearing Firth fit or a comparison with a required empty group.
- The output retains the frozen-MLE results alongside the Firth and conditional-permutation results in every run, flagged or not. If a frozen fit raises, its exception is retained in the output rather than terminating the amended analysis.

## 8. Recorded but not amended

These were identified in the same review and are **not** changed by this amendment. They are recorded here so they are on the record before data inspection.

1. **Retry and pacing versus the ≥10 failure rule.** `run.py` builds both API clients with `max_retries=0` and issues 900 sequential requests with no pacing. A single rate-limit burst can produce ten or more technical failures and compromise a model run under §13 of the preregistration. This is an operational property of the frozen runner, not of the analysis. Changing it changes `runner_sha256`, which the confirmatory analysis pins across all four manifests — so mixed runner versions would fail the frozen validator. A change would require a separately disclosed protocol decision; it would not erase the evidentiary value of existing runs. A1 leaves the runner unchanged.
2. **Sampling temperature is not recorded.** Neither provider call sets it, and the manifest does not capture the provider default in force during the collection window. The "served response distribution" claim should be read with that gap noted.
3. **Within-condition dependence is not modeled.** The GLM treats all format-valid draws as independent Bernoulli observations with 25 draws sharing each passage. Sharing a fixed stimulus does not by itself establish residual dependence, but the independence assumption remains relevant. A model × condition-clustered variance analysis could be considered separately as a sensitivity; A1 does not add it. The conditional permutation analysis in §4.4 relies on its own within-stratum exchangeability assumption and is not described as solving the clustering question.
4. **Truncation does not change frozen parsing.** The frozen parser does not use provider stop metadata. A truncated successful response may be format-invalid and leave the primary denominator, or may still satisfy the mechanical question/`NONE` format and remain in it. A1 adds the non-decision-bearing diagnostic in §4.6 so its rate and distribution are visible before the primary result is interpreted; it does not post hoc recode or restore those responses.
5. **Freeze-record digests are line-ending dependent.** The six SHA-256 values in `API_PILOT_0.1_FREEZE_RECORD.json` are digests of the CRLF working-tree forms. A checkout or archive carrying LF produces different digests for text that differs only in line endings. The frozen files were verified against the freeze record under CRLF normalization and match. Independent verifiers should be told which form to hash.

## 9. Files

| file | status | SHA-256 (LF) | SHA-256 (CRLF) |
|---|---|---|---|
| `api-study/analyze_confirmatory.py` | unchanged, frozen | `00f1e6ee36235ea4360d0236275311762371ea22d9c937e0b35ce14bd895c677` | `b98602d95c2aee47d2e5b35caa1bb858569996dce917898115b17cca25464d9d` |
| `api-study/analyze_confirmatory_a1.py` | added by this amendment | `7136399082d60f5dc11d7c0fad58278645a67cb5fcb45f399c9fced4b18ae094` | `2b117be21a17481c6b5ed034a019f396bcc78a462f33b8e7e5a231a93fe41019` |

The CRLF column is the value to expect from a Windows working tree; the LF column from a git archive or a non-normalizing checkout. Record whichever form your freeze builder hashes.

## 10. Invocation

```powershell
python .\api-study\analyze_confirmatory_a1.py `
  .\api-study\data\raw\<luna>.manifest.json `
  .\api-study\data\raw\<terra>.manifest.json `
  .\api-study\data\raw\<haiku>.manifest.json `
  .\api-study\data\raw\<sonnet>.manifest.json `
  --expected-hashes .\prereg\API_PILOT_0.1_FREEZE_RECORD.json
```

Requires `numpy`, `pandas`, `scipy`, and `statsmodels`. Run from the repository root or from within `api-study` so the frozen analyzer is importable.

After collection and adoption, retain the guarded frozen-MLE results or fit errors under `frozen_mle`. A separate invocation of the original script remains possible with a flat three-key hash adapter; the original script does not accept the nested freeze record directly. Do not invoke either analyzer before all accepted runs are complete.

---

**Initial blind draft prepared:** 2026-09-18T21:10:55Z  
**Corrected blind revision prepared:** 2026-09-18T21:44:21Z  
**Founder adoption/signature:** To be evidenced by the founder-signed commit adopting this file and its paired script; no signature is asserted by this draft text.
