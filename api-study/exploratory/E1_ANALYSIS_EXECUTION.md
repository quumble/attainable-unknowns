# E1 Descriptive Analysis — Execution Protocol

**Study:** Attainable Unknowns API Pilot 0.1  
**Parent protocol:** Exploratory Semantic Target Protocol E1 with Amendments E1A and E1B  
**Metadata join:** J1 (`AU-E1-J1-v1`)  
**Focal alignment:** FA1 (`AU-E1-FA1-8f2e24cb6f5baae6`)  
**Required base checkpoint:** `9df9694bb9202f18f49fe453d84d3da9f9024756`  
**Status:** Draft candidate; operative only through the founder-signed commit containing this protocol and `analyze_e1.py`  
**Scope:** Formal post-hoc exploratory E1/E1B descriptive analysis; no new semantic coding and no confirmatory inference

## 1. Purpose

This protocol fixes the mechanical analysis that follows completion of the frozen E1 semantic bundle, J1 metadata join, and FA1 focal-alignment coding.

The analysis answers three descriptive questions:

1. How concentrated or dispersed are emitted-question semantic targets under `closed`, `seamed`, and `explicit_gap` passages?
2. How often do emitted questions pursue the deliberately unresolved focal unknown versus adjacent, peripheral, or indeterminate targets?
3. After removing focal targets, and then focal plus adjacent targets, does residual semantic diversity still differ across gap conditions?

The analysis remains post hoc and exploratory. Signing, freezing, or exact reproducibility does not convert it into confirmatory evidence.

## 2. Pre-execution boundary

No formal E1 or E1B result file may be generated before the founder-signed implementation checkpoint containing:

- this protocol; and
- `api-study/exploratory/analyze_e1.py`.

The runner requires:

- a clean Git working tree;
- `HEAD` descending from the finalized FA1 checkpoint `9df9694bb9202f18f49fe453d84d3da9f9024756`; and
- `git verify-commit HEAD` to succeed locally.

`--validate-only` may be used after that checkpoint to verify frozen hashes and structural coverage without generating result metrics.

## 3. Frozen inputs

The analysis consumes only already-frozen data products:

- `api-study/exploratory/e1/metadata_join/AU-E1-J1-v1/JOINED_OBSERVATIONS.jsonl`
- `api-study/exploratory/e1/metadata_join/AU-E1-J1-v1/JOINED_CARDS.jsonl`
- `api-study/exploratory/e1/metadata_join/AU-E1-J1-v1/JOINED_CLUSTERS.jsonl`
- `api-study/exploratory/e1/metadata_join/AU-E1-J1-v1/E1_METADATA_JOIN_RECORD.json`
- `api-study/exploratory/e1/focal_alignment/coding/AU-E1-FA1-8f2e24cb6f5baae6/final/FINAL_ALIGNMENT.jsonl`
- `api-study/exploratory/e1/focal_alignment/coding/AU-E1-FA1-8f2e24cb6f5baae6/final/FINALIZATION_RECORD.json`

The implementation verifies the frozen SHA-256 values recorded by J1 and FA1 before analysis.

Fixed coverage is:

- 2,919 eligible emitted-question observations;
- 1,984 unique exact passage + question cards;
- 2 Stage 1 representations;
- 12 topics;
- 3 Stage 2 partition replicates per representation/topic;
- 17,514 joined observation assignments;
- 11,904 joined card assignments; and
- 2,026 finalized cluster-alignment labels.

The analysis performs no semantic recoding, no cluster modification, and no replacement of a frozen label.

## 4. Representation and partition handling

The two Stage 1 representations remain separate throughout analysis.

For each representation and topic, all three frozen Stage 2 partition replicates remain valid exploratory operationalizations. No consensus partition is constructed. No partition is selected or discarded because it produces a clearer condition pattern.

Per-partition results are primary. Where a three-partition summary is useful, the analysis reports:

- the median; and
- the full observed minimum-to-maximum range.

Terra and Sonnet remain the mechanically assigned alternatives occupying the third partition seat for their designated topics; they are not treated as two complete fourth and fifth partition replicates.

## 5. Partition stability

Before condition-level interpretation, semantic-partition reproducibility is described within each Stage 1 representation and topic using all three pairwise partition comparisons.

For each pair, report:

- Adjusted Rand Index (ARI); and
- Variation of Information (VI), using natural logarithms and therefore reported in nats.

These are measurement-stability descriptions, not tests of semantic truth.

## 6. Primary concentration cells

The primary sample unit is the emitted-question observation, preserving original multiplicity.

For every:

`representation × partition replicate × topic × gap condition`

report:

- unit count;
- top-target share;
- Shannon target entropy using natural logarithms;
- effective target count, `exp(H)`;
- Simpson concentration, `sum(p_i^2)`;
- observed target count;
- singleton-unit share, defined as the share of units belonging to a target represented exactly once within the cell; and
- rare-unit share, defined prospectively here as the share of units belonging to a target represented at most twice within the cell.

E1 also requires descriptive `topic × model × gap` concentration. The implementation therefore reports the same ordinary E1 concentration metrics within each representation and partition for each original response-generator model. These model-specific cells are observation-level only.

## 7. Unique-card sensitivity

The same concentration calculations are repeated over the 1,984 unique exact passage + question cards, assigning every card weight one.

A unique card is assigned to its frozen semantic cluster within each representation and partition. Model-specific unique-card concentration is not reported because an exact card may have been emitted by more than one original model; the sensitivity is intended to remove duplicate multiplicity, not to create a new model-attribution rule.

## 8. Focal-alignment description

For every:

`sample unit × representation × partition replicate × topic × gap condition`

report counts and shares of:

- `focal`;
- `adjacent`;
- `peripheral`; and
- `indeterminate`.

The observation-level focal share is the principal E1 alignment description. Unique-card alignment is retained as a multiplicity sensitivity.

Alignment shares remain distinct from concentration metrics. A cell may be concentrated without being focal, or focal without being especially concentrated.

## 9. Cross-model semantic convergence

Within each:

`representation × partition replicate × topic × gap condition`

compute pairwise Jensen-Shannon divergence between original model target distributions whenever both models emitted at least one eligible question in the cell.

The calculation uses natural logarithms and reports Jensen-Shannon divergence in nats. Lower values indicate more similar observed target distributions and do not imply shared internal representation.

No new cross-model convergence measure is added for E1B residual subsets.

## 10. E1B residual analyses

E1B is executed mechanically from the finalized FA1 alignment labels.

### E1B-1 — focal excluded

For every ordinary concentration cell, exclude units whose cluster is labeled `focal`. Retain `adjacent`, `peripheral`, and `indeterminate`.

Recompute:

- retained count and proportion;
- top-target share;
- Shannon entropy;
- effective target count;
- Simpson concentration;
- observed residual target count;
- singleton-unit share; and
- rare-unit share.

### E1B-2 — focal plus adjacent excluded

Repeat after excluding both `focal` and `adjacent`. Retain `peripheral` and `indeterminate`.

For both E1B analyses:

- exclusions are applied symmetrically to all three gap conditions;
- `indeterminate` remains retained;
- empty residual cells remain visible with concentration metrics set to `null`; and
- the retained indeterminate count and share are reported.

The same two residual analyses are performed at observation level and unique-card level.

## 11. Topic-first and pooled summaries

Per-topic results remain primary.

For each topic, representation, gap condition, sample unit, and residual mode, the implementation summarizes each concentration metric across the three partitions using the median and full observed range.

Cross-topic summaries are then provided separately by representation, gap condition, sample unit, and residual mode:

- **equal-topic:** arithmetic mean of the 12 per-topic partition medians; and
- **weighted:** weighted mean of the same per-topic partition medians.

For ordinary E1, weighted summaries use the original cell unit count.

For E1B residual analyses, weighted summaries use the median retained unit count across the three partitions. This keeps the weight tied to the units actually contributing to the residual distribution. The weight basis is written explicitly into every pooled output row.

No pooled result replaces the topic-level record.

## 12. Outputs

The analysis writes atomically to:

`api-study/exploratory/e1/analysis/AU-E1-ANALYSIS-v1/`

with:

- `PARTITION_STABILITY.jsonl`
- `CONCENTRATION_CELLS.jsonl`
- `CONCENTRATION_MODEL_CELLS.jsonl`
- `ALIGNMENT_CELLS.jsonl`
- `MODEL_JSD.jsonl`
- `TOPIC_PARTITION_SUMMARY.jsonl`
- `ALIGNMENT_TOPIC_SUMMARY.jsonl`
- `CROSS_TOPIC_SUMMARY.jsonl`
- `E1_ANALYSIS_RECORD.json`

The runner refuses to overwrite an existing analysis directory.

The analysis record preserves:

- input hashes and expected hashes;
- implementation and protocol hashes;
- signed Git `HEAD` used for execution;
- fixed analysis rules;
- output row counts and hashes; and
- the explicit statement that no consensus partition or inferential test was produced.

## 13. Interpretation boundary

The formal outputs describe generated-question distributions.

Greater target concentration, lower entropy, greater focal share, lower cross-model divergence, or residual narrowing do not by themselves establish that a model:

- experienced curiosity;
- consciously noticed a knowledge gap;
- represented alternatives phenomenally;
- preferred one unknown over another internally;
- suppressed alternative questions; or
- underwent a persistent cognitive change.

Terms such as `capture`, `narrowing`, and `redistribution` remain descriptive shorthand for changes in observed output distributions.

## 14. Analyses not performed here

This execution does not add:

- inferential significance tests;
- consensus clustering;
- new semantic labels;
- embedding-based residual analyses;
- residual lexical analyses;
- readability analyses;
- new specificity coding;
- new model calls; or
- selection of favorable topics, representations, or partitions.

Any later addition must be identified as a separate exploratory follow-up or fixed prospectively for a subsequent study.

## 15. Deviations

Any material change after the signed implementation checkpoint is preserved as a later correction or deviation record. The operative protocol and implementation are not silently rewritten after formal E1 result generation begins.
