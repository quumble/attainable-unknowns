# E1 Stage 2 — Fixed-Width Partition Encoding Correction P1D3

**Study:** Attainable Unknowns API Pilot 0.1  
**Parent protocol:** E1 with Amendment E1A  
**Parent Stage 2 execution protocol:** P1  
**Prior corrections:** P1D1, P1D2  
**Stage 2 bundle:** `AU-E1-S2-b021f4b9caf73dad`  
**Bundle anchor commit:** `435c01cb5971fd6b0487eaebfc7a8a5803311c06`  
**Frozen incomplete P1D2 execution commit:** `3c1dd0529fe8581f56fc290de9aed344a77f091a`  
**Status:** Post-canary technical serialization correction; operative only through the founder-signed implementation commit containing this record, the P1D3 output-encoding addendum, and the corrected runner  
**Date:** 2026-09-20

## 1. Trigger

P1D2 restarted Stage 2 from zero under a uniform assignment-vector
representation and a seven-canary gate.

Six of the seven P1D2 canaries completed structurally valid partitions.

The remaining canary, Sonnet P3 `R02-T04`, exhausted three P1D2 attempts. All
three provider responses ended normally (`end_turn`), remained well below the
64,000-token ceiling, and returned valid JSON assignment arrays that were too
short for the 230-target packet:

- attempt 1: 208 assignments;
- attempt 2: 211 assignments;
- attempt 3: 213 assignments.

The incomplete P1D2 canary execution was frozen at
`3c1dd0529fe8581f56fc290de9aed344a77f091a`.

No P1D2 semantic partition is carried forward into P1D3.

## 2. Provider-format investigation

Before choosing P1D3, synthetic-only probes were used to identify a
provider-neutral cardinality mechanism. No study packets, target text,
conditions, model metadata, or Stage 2 scientific results were used in these
probes.

### 2.1 Exact array cardinality

Anthropic rejected a 230-element exact-cardinality array schema using
`minItems = maxItems = 230` with HTTP 400. The returned error stated that
`minItems` values other than 0 or 1 are not supported.

Therefore P1D2's array representation could not receive equivalent
provider-side cardinality enforcement on the Anthropic paths.

### 2.2 One required property per target

A schema containing 230 required assignment properties was rejected by both
Claude Sonnet 5 and Claude Opus 5 with HTTP 400 because the compiled grammar
was too large.

Therefore a keyed-object representation was not adopted.

### 2.3 Fixed-width digit string

A compact schema constraining one string to exactly 690 decimal digits
(`^[0-9]{690}$`) was then tested for a 230-position synthetic task.

Claude Sonnet 5 returned the required 690-digit value successfully in all
three trials.

Claude Opus 5 refused a degenerate probe that requested the identical code
`001` at all 230 positions in all three trials. This established neither a
grammar rejection nor a cardinality failure because the requests compiled and
returned provider-level `refusal`.

A nondegenerate seven-cluster cyclic probe under the same 690-digit schema was
then run with Claude Opus 5. Opus returned the exact required 690-digit value
in all three trials.

These observations establish that the compact fixed-width grammar is accepted
and can be satisfied by both Anthropic Stage 2 models. They do not establish a
general explanation for the degenerate Opus refusal.

## 3. P1D3 encoding

P1D3 uses a single fixed-width assignment string for every provider and every
Stage 2 packet.

For a packet containing N targets:

- each target receives one three-digit decimal code;
- codes are emitted in exact input-target order;
- the final string therefore contains exactly `3 * N` digits;
- equal three-digit codes mean the targets belong to the same semantic cluster;
- different three-digit codes mean they belong to different semantic clusters.

The code values themselves are arbitrary labels. Any value from `000` through
`999` is permitted.

The largest Stage 2 packet contains 230 targets, so 1,000 available three-digit
labels exceed the maximum possible number of clusters.

## 4. Uniform constrained-output contract

The same JSON-schema representation is used for OpenAI and Anthropic paths.

For N input targets, the schema requires exactly:

```json
{
  "packet_id": "<copy exactly>",
  "assignment_code": "<exactly 3*N decimal digits>"
}
```

The `assignment_code` property uses the regular-expression constraint:

```text
^[0-9]{3N}$
```

with `3N` resolved to the packet-specific digit count before the API request.

The local validator independently verifies:

- exact root fields;
- exact packet identity;
- string type;
- exact `3 * N` character length;
- decimal digits only.

It then splits the string into consecutive three-character labels.

## 5. Deterministic canonicalization

After validation, arbitrary three-digit labels are canonicalized locally by
first occurrence:

- first distinct label encountered -> `C001`;
- next previously unseen label -> `C002`;
- and so on.

Targets are grouped under those canonical cluster IDs.

This operation is a pure relabeling. It cannot change which targets share a
cluster.

`PARTITIONS.jsonl` therefore retains the same downstream canonical
`packet_id` + `clusters` representation used by the prior executions.

## 6. Fresh execution lineage

P1D3 is a fresh 72-task Stage 2 execution in a new `P1D3` output directory.

The P1/P1D1 and P1D2 execution artifacts remain frozen provenance only. No
accepted partition from either predecessor execution is reused in the P1D3
scientific dataset.

Each P1D3 task receives the normal maximum of three P1D3 attempts.

All P1D3 attempt records carry:

- `execution_variant = "P1D3"`;
- `output_encoding = "fixed_width_triplet_string_v1"`.

The request fingerprint includes those execution settings.

## 7. Synthetic gate

Before P1D3 is signed for real-data execution, the runner's synthetic test is
expanded to a 230-target nondegenerate fixture so that each of the four model
paths is tested against the same maximum-size 690-digit output grammar.

All four paths must pass before signing the P1D3 implementation.

Synthetic outputs are not study data.

## 8. Real canary gate

P1D3 retains the seven-canary gate:

- Sol P1 `R01-T04`;
- Opus P2 `R02-T04`;
- Terra P3 `R01-T09`;
- Sonnet P3 `R02-T04`;
- Opus P2 `R02-T08`;
- Terra P3 `R01-T05`;
- Terra P3 `R02-T09`.

These include the original stress canaries plus the exact tasks that exposed
the predecessor serialization failures.

All seven must be structurally valid before the remaining 65 P1D3 tasks may
run.

A valid canary is final for P1D3 and is not repeated.

## 9. Model settings

P1D3 does not alter model identity, provider roster, reasoning/thinking,
effort, retry ceiling, or cost guards.

- Sol: `gpt-5.6-sol`, reasoning `low`, 16,000 output-token ceiling.
- Opus: `claude-opus-5`, adaptive thinking, effort `low`, 16,000 ceiling.
- Terra: `gpt-5.6-terra`, reasoning `low`, 16,000 ceiling.
- Sonnet: `claude-sonnet-5`, adaptive thinking, effort `low`, 64,000 ceiling.

The frozen semantic partition instructions and answer-space equivalence rule
remain unchanged. Only the output-encoding section is replaced at runtime by
the signed P1D3 encoding addendum.

## 10. Scientific status

P1D3 is a technical execution correction selected after observing structural
format failures and before inspecting downstream Stage 2 agreement,
concentration, entropy, model/gap, or focal-alignment results.

It does not alter:

- the semantic target definition;
- the blinded Stage 2 packets;
- the answer-space equivalence rule;
- the three-partition roster;
- model/gap blinding;
- the planned downstream exploratory metrics.

No failed predecessor output is manually repaired or promoted into the P1D3
dataset.
