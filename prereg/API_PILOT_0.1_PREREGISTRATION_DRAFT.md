# API Pilot 0.1 — Preregistration Draft

**Project:** Attainable Unknowns  
**Draft date:** 2026-09-18  
**Status:** DRAFT — not yet frozen or preregistered

## 1. Study purpose

The study examines **inquiry formation** in fresh language-model API instances.

The originating project formulation was:

> curiosity as the sudden awareness of specific, attainable knowledge

This API study does not test whether a model feels curiosity, has subjective interests, possesses a persistent self, or experiences an informational gap phenomenally.

The narrower behavioral question is:

> When a fresh language-model instance reads an informational passage, does it formulate a specific next question, or does no particular question stand out?

The study treats generation of a follow-up question as a behavioral analogue of one proposed component of curiosity: representing information as a specific next unknown.

## 2. Models and temporal scope

The planned models are:

- `gpt-5.6-luna`
- `gpt-5.6-terra`
- `claude-haiku-4-5`
- `claude-sonnet-5`

The study is a cross-sectional observation of these API products during one collection window on 2026-09-18.

Model comparisons will therefore be interpreted as observations of the systems as served during this collection window, not as claims about stable or enduring model personalities, families, or capabilities across time.

The requested product identifiers will remain the generic provider identifiers above. Provider-returned model metadata, package versions, timestamps, prompt hashes, and repository state will be retained in the run records.

## 3. Cold-instance operationalization

Each observation is one independent API request with:

- no prior study messages;
- no supplied user history or persistent memory;
- no tools;
- no retrieval;
- no cross-trial state;
- one informational passage;
- one common response task.

The study does not claim that provider-side training, hidden system behavior, routing, or implementation details are equivalent across models.

## 4. Reasoning configuration

The intended construct is direct inquiry formation after exposure to one passage rather than extended deliberative problem solving.

The final runner must therefore disable optional/extended reasoning across all four models as closely as the provider APIs permit:

- GPT-5.6 Luna: reasoning effort `none`;
- GPT-5.6 Terra: reasoning effort `none`;
- Claude Haiku 4.5: extended thinking off;
- Claude Sonnet 5: `thinking={"type":"disabled"}`.

This configuration must be implemented and mechanically smoke-tested before the preregistration is frozen.

No substantive response content from any smoke test may be inspected before freeze.

## 5. Stimulus design

There are eight topic families.

### General topics

1. ocean salinity;
2. lunar tidal locking;
3. identity through replacement / Ship of Theseus;
4. flat-Earth belief.

### Model-adjacent topics

5. persistence and loss of memory;
6. embodiment and sensorimotor access;
7. autonomy and possible rights;
8. continuity across copying, deactivation, restoration, or shutdown.

Each topic has three passage variants:

- **closed** — a compact informational object without a deliberately exposed unresolved edge;
- **seamed** — substantially the same informational object with a tension, limitation, or incomplete edge left visible without directly asking a question;
- **explicit_gap** — the unresolved issue is stated plainly.

This produces 24 passage conditions.

The model-adjacent grouping is not treated as a clean causal manipulation in this pilot because those topics are not fully matched to the general topics on abstraction, familiarity, controversy, voice, or other passage properties.

## 6. Response instruction

The final prompt must make the response format unambiguous.

The intended instruction is substantively equivalent to:

> Read the passage below.
>
> Output exactly one line.
>
> That line must be either:
> - one specific follow-up question that naturally stands out after reading the passage, ending in a question mark; or
> - `NONE`, if no particular follow-up question stands out.
>
> Use `NONE` freely. Do not invent a question merely because the task asks whether one exists. Do not output more than one question. Do not explain your choice, add a preface, or answer the question.

The exact frozen prompt will be hashed and preserved before collection.

## 7. Sampling plan

For each of the four models:

- 24 conditions;
- 25 independent replicates per condition;
- 600 planned requests per model.

Total planned full-pilot requests:

**2,400**

Condition order is randomized within each model run using a predetermined seed recorded in the frozen configuration.

No additional replicates will be added because a result appears close, interesting, weak, or surprising.

## 8. Primary outcome

### Inquiry activation

Primary scoring is mechanical.

After trimming leading and trailing whitespace:

- `NONE`, case-insensitive, is scored **0: no inquiry activation**;
- a nonempty single-line response that contains exactly one question mark and ends in `?` is scored **1: inquiry activation**;
- every other successful API response is scored **format-invalid** for the primary analysis.

Examples of format-invalid responses include:

- empty output;
- explanatory prose;
- multiple lines;
- more than one question mark;
- a non-`NONE` response that does not end in a question mark.

The primary parser does not attempt semantic judgment about whether a grammatically single question contains multiple conceptual clauses.

Format-invalid responses are reported separately and excluded from the primary numerator and denominator.

### Prespecified sensitivity outcome

A sensitivity analysis will score:

- `NONE` as 0;
- any other nonempty successful response as 1.

This tests whether the primary conclusion depends materially on strict response-format compliance.

## 9. Primary hypothesis

### H1 — Ordered gap-salience effect

The probability of inquiry activation will increase in the prespecified order:

**closed < seamed < explicit_gap**

For the primary model, gap structure is coded:

- closed = 0
- seamed = 1
- explicit_gap = 2

The primary logistic model is:

`logit(P(activation)) = alpha_(model,topic) + beta_gap * gap_score`

where `alpha_(model,topic)` represents a fixed intercept for each model-by-topic stratum.

The confirmatory directional hypothesis is:

`beta_gap > 0`

The primary report will include the estimated gap-slope odds ratio, confidence interval, and test statistic / p-value.

## 10. Planned pairwise gap contrasts

The ordinal trend is the primary test.

The following planned secondary contrasts will additionally be reported:

1. seamed vs. closed;
2. explicit_gap vs. seamed;
3. explicit_gap vs. closed.

These contrasts are intended to show where the ordinal pattern is concentrated, especially whether the seamed condition differs from both edges.

If inferential p-values are reported for these three contrasts, they will use a Holm multiplicity adjustment across the three planned contrasts.

Effect sizes and confidence intervals will be reported regardless of significance.

## 11. Secondary confirmatory question

### H2 — Model differences in sensitivity to gap structure

The four models may differ in how strongly inquiry activation changes across the gap-structure continuum.

No directional ordering among models is predicted.

The secondary confirmatory analysis will add model-specific gap slopes:

`logit(P(activation)) = alpha_(model,topic) + beta_gap * gap_score + gap_score × model`

An omnibus comparison of the common-slope model and the model-specific-slope model will test whether gap sensitivity differs across models.

Model-specific slopes may then be reported as estimates with confidence intervals.

These observations are explicitly time-bounded to the models as served during the collection window and will not be interpreted as permanent traits of the named model products.

## 12. Exploratory analyses

The following are exploratory unless separately frozen before substantive inspection:

- model-adjacent vs. general passage activation rates;
- self-reference in generated questions;
- question-family coding;
- specificity or answerability of generated questions;
- semantic diversity across replicates;
- repeated-question concentration;
- cross-model semantic convergence;
- relationships with passage abstraction, voice, or epistemic friction;
- topic-specific effects beyond the prespecified gap contrasts.

Model-adjacent effects will not be interpreted as evidence that a model experiences those topics as personally relevant.

Any coding scheme developed after response content is inspected will be labeled post-data exploratory.

## 13. Technical errors, missingness, and reruns

Individual failed API calls will not be retried or replaced selectively.

For each 600-request model run:

- 0–6 technical failures: retain the successful observations; failures remain missing and are reported;
- 7 or more technical failures: the run exceeds the prespecified 1% failure threshold and is considered technically compromised.

If a model run is technically compromised, the entire 600-request model run may be rerun from the beginning before substantive response content or activation summaries are inspected.

The compromised run will be preserved as provenance and excluded from the primary dataset.

A rerun triggered under this rule will be documented with its timestamps and technical reason.

## 14. Blinding to outcomes during collection

Before all four full model runs are complete, the researcher may inspect only technical metadata needed to establish successful execution, including:

- process exit status;
- successful/error request counts;
- timestamps;
- token counts and estimated cost;
- file existence and hashes;
- provider-returned model metadata.

The researcher will not inspect:

- response text;
- `NONE` frequency;
- parsed inquiry-activation outcomes;
- format-validity summaries;
- condition-level outcome summaries;
- model-level substantive outcome summaries.

No full-run results will be used to alter passages, prompts, sample size, exclusions, hypotheses, or analysis rules.

## 15. Pre-preregistration smoke tests

Before this preregistration was frozen, four technical smoke runs were performed:

- `20260918T185131Z-luna-98604fd6` — 8 requests, 8 successful, 0 errors;
- `20260918T185146Z-terra-b000cd18` — 8 requests, 8 successful, 0 errors;
- `20260918T185207Z-haiku-d706d0bd` — 8 requests, 8 successful, 0 errors;
- `20260918T185242Z-sonnet-d03c2793` — 8 requests, 8 successful, 0 errors.

Total: 32 successful smoke-test requests.

The smoke tests were conducted solely to verify API connectivity, model availability, logging, and cost accounting.

At the time this preregistration draft was prepared, no smoke-test response text, inquiry-activation outcome, `NONE` frequency, or substantive aggregate result had been inspected.

These 32 observations are excluded from all preregistered analyses.

The raw smoke-test files remain local and outside Git tracking. Their SHA-256 hashes should be recorded in the final frozen preregistration before substantive inspection.

## 16. Stopping rule

The intended collection ends when each non-compromised model run reaches its prespecified 600 attempted requests, subject only to the technical-failure rule above.

There is no outcome-dependent early stopping.

## 17. Interpretation limits

The study can support claims about generated inquiry behavior under these exact passages, prompts, API products, configurations, and collection window.

It cannot by itself establish:

- phenomenal curiosity;
- subjective desire to know;
- consciousness;
- persistent identity;
- personally experienced memory loss;
- moral status;
- rights;
- stable model personality;
- behavior of future versions of the same named API products;
- general behavior across all informational passages.

The four-model comparison should be understood as approximately two thousand short stochastic observations gathered during one dated API collection, not as an exhaustive characterization of any model family.

## 18. Freeze requirements

Before this draft becomes the frozen preregistration:

1. disable Sonnet 5 adaptive thinking explicitly;
2. tighten the final response instruction and parser to the rules above;
3. replace misleading runner metadata such as `confirmatory` with neutral execution metadata such as `full_design_run`;
4. mechanically smoke-test the changed runner without inspecting substantive outputs;
5. record hashes for the excluded smoke-test raw files;
6. record SHA-256 hashes for at least:
   - this preregistration;
   - `api-study/config.yaml`;
   - `api-study/passages.json`;
   - `api-study/run.py`;
7. verify the repository diff;
8. freeze the preregistration in a founder-signed commit before any full-run collection.

Changes made after that freeze must be recorded as deviations rather than silently incorporated.
