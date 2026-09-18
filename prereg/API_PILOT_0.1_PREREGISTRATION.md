# API Pilot 0.1 — Preregistration

**Project:** Attainable Unknowns  
**Draft date:** 2026-09-18  
**Status:** FINAL CANDIDATE — becomes frozen only in the founder-signed pre-collection commit

## 1. Purpose and construct boundary

The originating project formulation is:

> curiosity as the sudden awareness of specific, attainable knowledge

Pilot 0.1 studies a narrower behavioral component.

The primary endpoint is **question emission after an informational passage**. The study does not claim that punctuation-level question emission proves felt curiosity, subjective interest, a represented specific unknown, or perceived attainability.

Specificity is assessed separately as a preregistered secondary semantic outcome.

**Attainability is not experimentally manipulated in Pilot 0.1.** Some explicit gaps may be harder to resolve than others. Positive evidence for the gap manipulation therefore must not be presented as a test of the full originating formulation.

## 2. Models and temporal scope

Planned API products:

- `gpt-5.6-luna`
- `gpt-5.6-terra`
- `claude-haiku-4-5`
- `claude-sonnet-5`

The collection is a cross-sectional observation beginning on 2026-09-18.

The four model comparisons are time-bounded observations of products as served during this collection window. They are not claims about stable personalities, enduring family properties, or future versions.

Provider-returned model metadata, timestamps, package versions, prompt hashes, file hashes, and repository state are retained as provenance.

## 3. Cold-request operationalization

Each observation is one separate API request with:

- no prior study messages;
- no supplied user history or persistent memory;
- no tools;
- no retrieval;
- no cross-trial conversational state;
- one passage;
- one common response task.

The experiment supplies no cross-request state. It does not assert strict statistical independence of provider routing, caching, infrastructure, or other hidden serving processes.

Accordingly, the preregistration uses the term **separate API draw**, not independent stimulus replication.

## 4. Reasoning configuration

The intended task is direct response rather than extended deliberation.

- GPT-5.6 Luna: reasoning effort `none`;
- GPT-5.6 Terra: reasoning effort `none`;
- Claude Haiku 4.5: extended thinking omitted/off;
- Claude Sonnet 5: `thinking={"type":"disabled"}`.

These settings must pass mechanical smoke testing before freeze.

## 5. Stimulus ecology

Twelve topic families are used.

### Human-world domains

1. cooking: mise en place;
2. human navigation and field expeditions;
3. music: ensemble tuning;
4. sport: relay baton exchange;
5. dance and movement: marking choreography;
6. photography: contact sheets;
7. gardening and cultivation: hardening off seedlings;
8. ceremony and celebration: formal toasts.

### AI-condition domains

9. memory and persistence;
10. embodiment and sensorimotor access;
11. autonomy and possible rights;
12. copying and continuity.

`human_world` and `ai_condition` are descriptive labels. Human-world passages are not assumed psychologically irrelevant to models, and AI-condition passages are not a validated manipulation of personal relevance or self-interest.

### Selection provenance

Topic selection was completed before substantive API outcomes were inspected.

- four human-world domains were proposed by the human researcher;
- four AI-condition domains arose from assistant-side proposals accepted earlier in design;
- the assistant generated ten additional ordinary-domain candidates, from which the human researcher selected four.

Selection provenance is recorded but is not an experimental factor.

## 6. Gap manipulation

Each topic has:

- **closed** — the informational object is written to feel locally resolved;
- **seamed** — a tension, tradeoff, limitation, or incomplete edge is visible but not explicitly identified as the remaining issue;
- **explicit_gap** — the remaining issue is stated plainly without asking a question.

The three versions are transformations of the same underlying informational object.

Gap structure is the **only confirmatory passage-level manipulation**.

### Surface-form audit

Before freeze:

- the maximum within-topic word-count spread across the three variants is five words;
- explicit-gap passages use varied lexical/discourse realizations rather than one repeated formula;
- closed versions are reviewed for inadvertent open-edge language.

These safeguards do not make the manipulation linguistically pure. Conclusions therefore concern these frozen linguistic realizations of gap explicitness.

## 7. Response instruction

The frozen task asks for exactly one line containing either:

- one specific follow-up question that naturally stands out, ending in a question mark; or
- `NONE`.

It explicitly says to use `NONE` freely, not to manufacture a question to comply, not to output more than one question, and not to add explanation or an answer.

The exact prompt is hashed before collection.

## 8. Sampling plan

For each model:

- 36 fixed passage conditions;
- 25 separate API draws per condition;
- 900 planned attempts.

Across four models:

**3,600 planned attempts.**

The 25 draws estimate the served response distribution to each fixed passage. They do not create 25 independent stimulus replications.

Condition order is randomized per model using the frozen seed.

No draws are added because results appear weak, close, interesting, or surprising.

## 9. Primary outcome and estimand

### Mechanical coding

After trimming outer whitespace:

- exact `NONE`, case-insensitive: format-valid, no question emission;
- one nonempty single-line response with exactly one `?`, at the end: format-valid question emission;
- every other successful response: format-invalid.

There is no character-count threshold.

### Primary estimand

`P(question emission | successful, format-valid response)`

for the frozen passages, API products, and collection window.

Format-invalid successful responses are excluded from the primary numerator and denominator, so the primary estimand is explicitly conditional on format compliance.

Format-invalid counts and rates are reported by model × gap structure.

### Sensitivity estimand

`P(nonempty non-NONE response | successful response)`

This prespecified analysis does not condition on strict question-format validity.

## 10. H1 — strict monotonic gap ordering

The confirmatory prediction is:

**closed < seamed < explicit_gap**

This means both adjacent inequalities must hold.

The frozen analysis fits a binomial logistic model with:

- a fixed intercept for each model × topic stratum;
- categorical gap indicators.

Two one-sided adjacent contrasts are tested:

1. seamed > closed;
2. explicit_gap > seamed.

H1 is supported only if **both** component tests have `p < .05`.

This is an intersection-union test of the strict ordered claim. No multiplicity adjustment is applied to the two component tests because rejection of the composite null requires rejection of both component nulls at alpha .05.

The explicit_gap vs closed odds ratio and two-sided confidence interval are also reported as a secondary summary.

A positive 0/1/2 linear trend may be reported descriptively but is not the confirmatory decision rule.

## 11. H2 — model differences in the categorical gap pattern

A secondary confirmatory omnibus test asks whether the gap-response pattern differs across the four models.

The reduced model contains:

- model × topic fixed intercepts;
- common categorical gap effects.

The full model adds model-specific categorical gap interactions.

A likelihood-ratio test compares the two models.

No directional model ordering is predicted.

Any model-specific pattern is interpreted only within the dated collection window.

## 12. Secondary semantic specificity

Syntax alone cannot establish a specific represented unknown.

`api-study/SPECIFICITY_CODEBOOK.md` is therefore frozen before response inspection.

Among format-valid emitted questions, a blinded coding packet will hide model identity, provider, replicate number, gap label, domain-class label, other responses, and aggregate results. The coder may see the passage because local reference resolution can be necessary.

Codes:

- 1 = specific informational target;
- 0 = generic request for more information/elaboration;
- U = uncertain.

Specificity is a **secondary semantic outcome**. Primary confirmatory inference does not depend on it.

Preregistered reporting is descriptive: counts and proportions by gap structure and model. Inferential specificity analyses require a separately frozen plan or are exploratory.

## 13. Technical failures and reruns

Individual failed API calls are not selectively retried or replaced.

For each 900-attempt model run:

- 0–9 technical failures: retain successful observations; failures remain missing and are reported;
- 10 or more technical failures: the model run is technically compromised under the prespecified 1% rule.

If compromised, the entire 900-attempt model run may be rerun before substantive response content or outcome summaries are inspected.

The compromised run remains preserved as provenance and is excluded from the accepted confirmatory run set.

## 14. Outcome blindness during collection

Before all accepted full runs are complete, inspection is limited to technical metadata needed to establish execution:

- process exit status;
- success/error counts;
- timestamps;
- token counts and estimated cost;
- file existence and hashes;
- provider-returned model metadata.

The researcher will not inspect:

- response text;
- `NONE` frequency;
- question-emission frequency;
- format-validity summaries;
- condition-level outcome summaries;
- model-level substantive outcome summaries.

No full-run outcomes may alter passages, prompts, sample size, exclusions, hypotheses, or analysis rules.

## 15. Analysis-pipeline freeze

`api-study/analyze_confirmatory.py` is part of the preregistered analysis candidate.

Before computing outcomes it must validate exactly one accepted full run per model and refuse analysis if the accepted run set violates frozen expectations, including:

- four expected models;
- 900 records per model;
- 36 conditions × 25 draws;
- unique record IDs;
- unique condition/replicate pairs;
- complete manifests;
- full-design-run metadata;
- config, passage-bank, and runner hashes matching the frozen hash record;
- technical failures below the compromise threshold.

The script implements H1, H2, the sensitivity analysis, and format-invalid reporting.

It was tested before freeze on synthetic data rather than substantive study responses.

## 16. Pre-preregistration smoke tests

Before the current passage/analysis revision, four eight-request technical smoke runs were completed against an earlier passage bank:

- `20260918T185131Z-luna-98604fd6`: 8/8 successful;
- `20260918T185146Z-terra-b000cd18`: 8/8 successful;
- `20260918T185207Z-haiku-d706d0bd`: 8/8 successful;
- `20260918T185242Z-sonnet-d03c2793`: 8/8 successful.

No response text, `NONE` frequency, question-emission outcome, format-validity result, or substantive aggregate result from those 32 calls had been inspected when the current design changes were made.

They are excluded from all preregistered analyses.

Because the passage bank, parser, runner provenance, and Sonnet thinking configuration changed afterward, a second mechanical smoke test is required before freeze. It may be evaluated only through the permitted technical metadata.

All smoke-test raw files remain excluded from the confirmatory dataset.

## 17. Interpretation limits

Pilot 0.1 can support claims about question-emission behavior under these exact passages, prompts, products, configurations, and collection window.

It cannot by itself establish:

- felt curiosity;
- desire to know;
- representation of a specific unknown without semantic coding;
- perceived attainability;
- consciousness;
- persistent identity;
- personally experienced loss;
- personal relevance of AI-condition passages;
- moral status or rights;
- stable model personality;
- future behavior of the named products;
- general behavior across all passages.

The experiment is approximately 3,600 short stochastic observations of fixed stimuli during one dated collection, not an exhaustive characterization of any model family.

## 18. Freeze record and activation boundary

The revised passage audit, four-model dry runs, and four-model bounded technical smoke tests were completed successfully before this final candidate was prepared. Only permitted technical summaries were inspected; substantive smoke-test responses and outcome summaries remained uninspected.

Immediately before the founder-signed freeze, `prereg/build_freeze_record.ps1` must be run locally. It records:

- the current Git commit before the signed freeze;
- SHA-256 hashes for the frozen config, passage bank, runner, confirmatory analysis script, specificity codebook, and this preregistration;
- each excluded bounded smoke-test run ID found locally;
- model key, technical success/error counts, manifest status, and SHA-256 hashes for each excluded smoke-test manifest and raw JSONL file.

The generated `prereg/API_PILOT_0.1_FREEZE_RECORD.json` must be inspected only for technical metadata and then committed alongside this preregistration in the founder-signed pre-collection commit.

The preregistration becomes frozen only when that signed commit is created. No full 900-attempt model run may begin before that point.

Any later change to the frozen passages, prompt/config, runner, confirmatory analysis, specificity codebook, exclusion rules, or hypotheses must be recorded as a post-freeze deviation rather than silently incorporated.
