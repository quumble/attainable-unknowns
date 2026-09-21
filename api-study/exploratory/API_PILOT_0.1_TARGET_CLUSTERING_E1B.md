# API Pilot 0.1 — Exploratory Semantic Target Protocol E1 Amendment E1B

**Study:** Attainable Unknowns API Pilot 0.1
**Protocol:** Exploratory Semantic Target Protocol E1
**Prior amendment:** E1A
**Amendment ID:** E1B
**Status:** Draft candidate; operative only through the founder-signed commit containing this file
**Prepared:** 2026-09-21
**Stage:** After completion of the J1 metadata join; before formal E1 descriptive analysis and before focal-alignment results are generated
**Scope:** Residual semantic-diversity analysis after exclusion of focal and focal-adjacent target clusters

## 1. Purpose

E1 separately specifies:

1. semantic concentration of emitted-question targets; and
2. alignment of those targets with the passage's deliberately unresolved focal issue.

E1B adds a residual-diversity analysis intended to distinguish two conceptually different patterns:

* **focal capture:** semantic concentration arises primarily because many questions converge directly on the deliberately exposed unknown; and
* **broader field redistribution:** semantic concentration remains after questions directed at the focal unknown are removed.

The motivating exploratory question is:

> After removing questions that pursue the deliberately exposed unknown, does the remaining distribution of informational targets still differ across closed, seamed, and explicit-gap passages?

A second, more aggressive sensitivity analysis asks:

> Does any such difference remain after removing both the focal unknown and its immediately adjacent informational neighborhood?

E1B does not assume that either pattern will occur.

## 2. Evidentiary and timing boundary

E1B is post hoc and exploratory.

It is prepared after:

* collection and confirmatory analysis of Pilot 0.1;
* B1/B1A specificity analysis;
* adoption and execution of E1 and E1A;
* completion and preservation of both Stage 1 semantic representations;
* completion and preservation of all Stage 2 partitions and cluster labels;
* preservation of the blind E1 semantic bundle; and
* completion of the J1 metadata join.

The distinction between focal capture and broader residual narrowing was raised during interpretation planning after J1 and before formal E1 concentration results were generated.

At the time E1B was drafted, no formal E1 residual-diversity calculation had been performed.

E1B does not convert any E1 analysis into confirmatory evidence. It adds a prospectively fixed exploratory analysis to an already post hoc exploratory protocol.

## 3. Dependence on frozen E1 materials

E1B uses only semantic structures already fixed by E1/E1A.

It does not alter:

* the 2,919 eligible emitted-question observations;
* the 1,984 exact passage + question cards;
* either Stage 1 canonical-target representation;
* any Stage 2 partition membership;
* any cluster label;
* any focal unknown anchor;
* any original response metadata;
* the focal-alignment categories specified by E1; or
* the mapping produced by J1.

No question or cluster is semantically recoded for E1B.

E1B begins only after the focal-alignment procedure specified by E1 has assigned frozen target clusters to:

* `focal`;
* `adjacent`;
* `peripheral`; or
* `indeterminate`.

Those alignment assignments are used mechanically as exclusion labels.

## 4. Primary population

The primary E1B analysis retains the observation-level population specified by E1.

Each eligible emitted-question observation therefore retains its original multiplicity.

Exact repetition is treated as part of the observed model behavior rather than removed from the primary analysis.

E1B also inherits the E1 unique-card sensitivity analysis, in which each of the 1,984 exact passage + question cards receives weight one.

The observation-level analysis remains primary.

## 5. E1B-1 — focal-excluded residual diversity

For every Stage 1 representation × Stage 2 partition × topic × gap-condition cell:

1. map observations to their frozen target clusters;
2. apply the frozen focal-alignment label associated with each cluster;
3. exclude observations whose cluster is labeled `focal`;
4. retain observations labeled `adjacent`, `peripheral`, or `indeterminate`; and
5. recompute the residual semantic-target distribution using only retained observations.

The exclusion is applied symmetrically to **closed, seamed, and explicit-gap conditions**.

This symmetry is required because closed and seamed passages may also elicit questions that happen to pursue the same informational target later made explicit in the explicit-gap passage.

E1B-1 therefore does not compare an edited explicit-gap distribution with unedited comparison conditions.

For every residual cell, report:

* original emitted-question count;
* retained emitted-question count;
* retained proportion;
* top-target share;
* Shannon target entropy;
* effective number of targets, `exp(H)`;
* Simpson concentration;
* observed residual target count.

If no observations remain after exclusion, the cell is reported as empty and concentration metrics are `NA`.

Cells containing very small residual counts remain visible and are interpreted with their retained sample size shown.

## 6. E1B-2 — focal-plus-adjacent exclusion sensitivity

E1B-2 repeats the E1B-1 procedure after excluding observations whose frozen cluster alignment is either:

* `focal`; or
* `adjacent`.

Only `peripheral` and `indeterminate` observations remain.

This is a deliberately stronger exploratory sensitivity analysis.

Its purpose is to ask whether any condition-associated narrowing remains outside the broader informational neighborhood of the deliberately exposed unknown.

E1B-2 is secondary to E1B-1 and must not replace it merely because one produces a clearer pattern.

The same residual metrics and empty-cell rules specified in §5 apply.

## 7. Treatment of indeterminate alignment

Clusters labeled `indeterminate` are retained in both E1B-1 and E1B-2.

E1B does not silently recode uncertain clusters as focal, adjacent, or peripheral.

The prevalence of retained `indeterminate` observations is reported so that uncertainty in the residual set remains visible.

A later sensitivity excluding `indeterminate` clusters is not part of E1B unless separately declared before inspection of such a result.

## 8. Stage 1 representation handling

All E1B analyses are performed separately under:

* the Sol-derived Stage 1 canonical-target representation; and
* the Opus-derived Stage 1 canonical-target representation.

The two representations are not reconciled, averaged into a common target map, or selected according to which produces a clearer residual pattern.

Agreement across representations is treated as robustness.

Disagreement remains visible.

## 9. Stage 2 partition handling

Every topic retains the three independent Stage 2 partitions actually collected.

For each topic:

* one partition was produced by Sol;
* one partition was produced by Opus; and
* the third partition was produced by either Terra or Sonnet according to the frozen P3 topic assignment.

All three partitions have equal status within that topic.

No consensus partition is constructed.

For presentation, partitioner identity may be shown using four named columns:

* Sol;
* Opus;
* Terra;
* Sonnet.

Terra and Sonnet contain structural `NA` values for the topic packets assigned to the other P3 model.

This display convention does **not** convert the design into four equally complete partition replicates.

For analytic summaries, Terra and Sonnet jointly constitute the single third partition seat defined by the frozen Stage 2 roster.

They are not each assigned independent full weight across topics.

Where E1 summarizes across the three partitions, E1B reports the median and full observed range across the three available partitions for that topic.

## 10. Topic-first reporting

E1B results are interpreted first within the 12 topic families.

No pooled result replaces the topic-level pattern.

After per-topic results are shown, E1B may report the same cross-topic summaries specified by E1:

* equal-topic summaries; and
* observation-weighted summaries.

The purpose of pooled summaries is compression, not concealment of topic heterogeneity.

## 11. Descriptive status

E1B is primarily descriptive.

It adds no confirmatory hypothesis test and requires no new p-value threshold.

Interpretation emphasizes:

* direction and magnitude of residual concentration differences;
* consistency or heterogeneity across topics;
* robustness across Stage 1 representations;
* robustness across Stage 2 partitions; and
* robustness to observation-level versus unique-card weighting.

Formal inferential modeling may be considered later as exploratory follow-up or preregistered in a subsequent study.

Absence of a formal significance test must not be described as evidence of equivalence or no effect.

## 12. Interpretation

The residual analyses distinguish several possible patterns.

### Pattern A — focal capture only

If explicit-gap passages show greater overall semantic concentration, but that difference largely disappears after focal exclusion, the concentration is consistent with direct capture by the deliberately exposed unknown.

### Pattern B — residual narrowing

If condition-associated concentration remains after focal targets are excluded, the result is consistent with a broader redistribution of emitted-question targets beyond direct focal capture.

### Pattern C — neighborhood-limited redistribution

If residual narrowing survives focal exclusion but disappears after focal-plus-adjacent exclusion, the redistribution appears concentrated within the focal issue's broader informational neighborhood.

### Pattern D — peripheral redistribution

If narrowing remains even after focal and adjacent targets are excluded, the remaining peripheral question distribution also differs across conditions.

These descriptions concern observable distributions of generated questions.

They do not establish that a model:

* experienced curiosity;
* internally represented a field of possible questions;
* consciously attended to an unknown;
* had alternatives available in a phenomenal sense;
* experienced suppression of unchosen possibilities; or
* underwent an irreversible cognitive change.

Language such as "field narrowing," "capture," or "redistribution" is descriptive shorthand for changes in the observed semantic-target distribution.

## 13. Analyses not added by E1B

E1B does not add:

* new semantic clustering;
* consensus clustering;
* new target labels;
* residual embedding analysis;
* residual lexical-overlap analysis;
* residual readability analysis;
* new cross-model convergence metrics;
* new inferential significance testing; or
* post hoc selection of favorable topics, representations, or partitions.

Those analyses remain outside E1B unless separately documented.

## 14. Preservation and execution

If adopted, E1B is preserved before the first formal E1B residual-diversity output is generated.

The implementation must preserve:

* the E1B analysis code;
* input hashes;
* output hashes;
* exact exclusion rules;
* retained and excluded counts;
* representation and partition identifiers; and
* any technical correction or deviation.

A founder signature timestamps adoption but does not alter the exploratory status of E1B.

## 15. Adoption and deviations

E1B becomes operative only through the founder-signed commit containing this file.

Any material change after adoption is preserved as a later amendment or deviation record rather than silently rewriting this document.

Nothing in E1B changes the status, results, or evidentiary interpretation of the original Pilot 0.1 confirmatory analyses, B1/B1A, E1, or E1A.
