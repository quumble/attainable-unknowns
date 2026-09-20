# E1 Stage 2 — Sonnet Output-Ceiling Correction P1D1

**Study:** Attainable Unknowns API Pilot 0.1  
**Parent protocol:** E1 with Amendment E1A  
**Parent Stage 2 execution protocol:** P1  
**Stage 2 bundle:** `AU-E1-S2-b021f4b9caf73dad`  
**Bundle anchor commit:** `435c01cb5971fd6b0487eaebfc7a8a5803311c06`  
**P1 implementation commit:** `63c1cea4614a2a4a7281424db9ddf968a9cd0ab2`  
**Status:** Post-canary technical correction; operative only through the founder-signed implementation commit containing this record and the corrected runner  
**Date:** 2026-09-20

## 1. Trigger

P1 required four real stress canaries before the unattended Stage 2 run.

Three canaries completed structurally valid partitions:

- Sol P1 `R01-T04`;
- Opus P2 `R02-T04`;
- Terra P3 `R01-T09`.

The Sonnet P3 canary `R02-T04` did not complete after the P1 maximum of
three attempts.

All three Sonnet attempts used the P1 16,000-token output ceiling and all three
reported exactly:

- input tokens: 21,488;
- output tokens: 16,000.

Observed terminal results were:

1. invalid JSON, empty/non-JSON visible response;
2. invalid JSON, empty/non-JSON visible response;
3. invalid JSON, unterminated string at visible JSON character 2,801.

Elapsed times were approximately 146.1, 133.6, and 132.2 seconds. Each attempt
cost approximately USD 0.202976 under the configured conservative pricing
calculation.

The three failed attempts remain preserved in the append-only attempt log.

## 2. Diagnosis

The observed failure mode is a binding technical output ceiling, not a semantic
adjudication failure.

Claude Sonnet 5 adaptive thinking and the visible response share the request's
`max_tokens` ceiling. The exact 16,000-token usage on all three attempts, together
with absent/truncated visible JSON, shows that the P1 ceiling was insufficient for
this large 230-target canary under the frozen adaptive-thinking / low-effort
configuration.

No Stage 2 clustering result from the failed Sonnet attempts is accepted.

## 3. Correction

Only the Sonnet Stage 2 execution path changes.

### 3.1 Sonnet maximum output tokens

For `claude-sonnet-5` Stage 2 partition calls:

- P1: `max_tokens = 16000`
- P1D1: `max_tokens = 64000`

The model remains `claude-sonnet-5`.

Thinking remains:

```json
{"type":"adaptive"}
```

Effort remains:

```json
{"effort":"low"}
```

The frozen Stage 2 instructions, structured-output schema, local validator,
packet contents, task roster, blinding, and semantic equivalence rule are
unchanged.

The 64,000-token value is a ceiling, not a target and not an expected output
length.

### 3.2 Other model paths

Sol, Opus, and Terra remain at their P1 16,000-token ceilings and otherwise retain
their signed P1 configurations.

The three already-valid P1 canaries remain final and are not rerun.

## 4. Attempt lineage

The three failed Sonnet P1 canary attempts are historical predecessor attempts.
They remain in `ATTEMPTS.jsonl` and remain included in cumulative observed-cost
reporting.

They do **not** consume the corrected P1D1 three-attempt ceiling.

Under P1D1, each Sonnet Stage 2 task receives a fresh maximum of three attempts
under the corrected 64,000-token ceiling.

Attempt records written after this correction carry an explicit
`execution_variant` field. Sonnet corrected attempts use `P1D1`; other model
paths retain the P1 execution lineage.

Request fingerprints include the execution variant and output-token ceiling so a
corrected request cannot be confused with a predecessor request having the same
packet and attempt index.

## 5. In-flight safety

The `INFLIGHT.json` marker and terminal-attempt reconciliation include execution
variant information.

This prevents an old P1 Sonnet terminal record from being mistaken for the
terminal result of a new P1D1 request with the same task ID and attempt index.

The existing bounded Windows marker-cleanup behavior is unchanged.

## 6. Canary gate

The unattended `run` command remains gated on four structurally valid canaries.

After this correction is signed:

1. static preflight is rerun against the signed P1D1 implementation;
2. a synthetic Sonnet test may be run to verify the corrected API path;
3. the real canary command resumes only the missing Sonnet canary under P1D1.

The full run remains prohibited until that corrected Sonnet canary is structurally
valid.

If the corrected Sonnet canary again reaches the 64,000-token ceiling without a
valid partition, execution stops for review rather than silently changing the
thinking configuration or granting further study attempts.

## 7. Cost guard

The Sonnet model-path stop limit remains USD 5 under P1.

The approximately USD 0.608928 already consumed by the three predecessor Sonnet
canary attempts remains included in cumulative observed Sonnet cost.

No cost history is reset by this correction.

## 8. Interpretive status

P1D1 is a technical execution correction made before any valid Sonnet Stage 2
partition existed and before the unattended Stage 2 run.

It does not alter the exploratory hypotheses, semantic target definition,
partitioning rule, blinded packets, partition roster, or downstream analysis
plan.

The failed predecessor outputs are not semantically inspected or repaired into
study results.
