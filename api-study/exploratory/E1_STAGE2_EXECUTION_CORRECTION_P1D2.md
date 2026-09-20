# E1 Stage 2 — Assignment-Vector Restart Correction P1D2

**Study:** Attainable Unknowns API Pilot 0.1  
**Parent protocol:** E1 with Amendment E1A  
**Parent Stage 2 execution protocol:** P1  
**Prior correction:** P1D1  
**Stage 2 bundle:** `AU-E1-S2-b021f4b9caf73dad`  
**Bundle anchor commit:** `435c01cb5971fd6b0487eaebfc7a8a5803311c06`  
**P1D1 implementation commit:** `84359ce38146baab2a1638753fb064a5aa79fb4e`  
**Incomplete P1/P1D1 execution anchor:** `c83f55cb0ad44e26f75848018c1a2360093294b0`  
**Status:** Post-run technical serialization correction and uniform restart; operative only through the founder-signed implementation commit containing this record, the P1D2 output-encoding addendum, and the P1D2 runner  
**Date:** 2026-09-20

## 1. Trigger

After the four P1/P1D1 stress canaries passed, the Stage 2 execution completed
62 of 72 required partitions before ending incomplete.

Three tasks exhausted the three-attempt ceiling:

- Opus P2 `R02-T08`;
- Terra P3 `R01-T05`;
- Terra P3 `R02-T09`.

The Terra path then circuit-broke, leaving seven additional Terra tasks
unattempted.

The incomplete execution, including 87 attempt records, 62 valid partitions,
and its run manifest, was frozen before this correction at
`c83f55cb0ad44e26f75848018c1a2360093294b0`.

## 2. Observed failure mode

The exhausted tasks did not show output-token truncation.

Observed structural failures were:

- Opus `R02-T08`: all three attempts returned 171 assignments for a 172-target
  packet;
- Terra `R02-T09`: attempts returned 219, 218, and 221 assignments for a
  220-target packet;
- Terra `R01-T05`: two attempts had complete target coverage but failed only the
  arbitrary cluster-order serialization rule; the remaining attempt returned
  155 assignments for a 159-target packet.

Provider responses were otherwise completed and well below the applicable
output-token ceilings.

## 3. Diagnosis

The observed failures implicate the cluster-centric serialization contract,
not the semantic equivalence rule itself.

The semantic task is to partition every target exactly once. P1 required the
model also to reproduce opaque target IDs inside nested cluster lists and to
serialize arbitrary cluster labels in first-occurrence order. Those bookkeeping
requirements can fail independently of semantic partition membership.

The complete-coverage Terra responses that failed only cluster ordering make
this distinction directly visible: membership had passed every earlier local
coverage check, while only arbitrary output ordering failed.

No failed predecessor output is accepted, repaired, or selected after the fact.

## 4. Uniform restart decision

P1D2 does **not** splice corrected tasks into the 62 accepted P1/P1D1
partitions.

Instead, all 72 Stage 2 partitions are rerun from the same frozen blinded packet
bundle under one uniform corrected serialization contract.

The P1/P1D1 execution remains immutable provenance and is superseded for final
Stage 2 partition analysis.

This restart occurs before inspection of downstream Stage 2 concentration,
agreement, gap, model, focal-alignment, or treatment-pattern results.

## 5. Assignment-vector output encoding

The semantic partitioning task is unchanged.

For P1D2, the model returns one integer cluster label for each target in exact
input order rather than reconstructing target IDs inside nested cluster lists.

Example for five targets:

```json
{
  "packet_id": "EXAMPLE",
  "assignments": [1, 1, 2, 3, 2]
}
```

Targets at positions i and j belong to the same semantic cluster if and only if
the corresponding integers are equal.

Integer values are arbitrary labels. They carry no semantic meaning and need not
be consecutive.

## 6. Deterministic local canonicalization

After exact structural validation, the runner converts the assignment vector to
the study's existing canonical `clusters` representation.

Labels are renumbered by first occurrence:

- first distinct label -> `C001`;
- next previously unseen label -> `C002`;
- and so on.

Input target IDs are then mechanically grouped under those canonical IDs.

This operation changes no semantic membership. It only canonicalizes arbitrary
labels and ordering.

Therefore downstream partition calculations continue to consume the same
canonical `packet_id` + `clusters` structure as originally planned.

## 7. Structured-output enforcement

For both providers, the structured-output schema requires a root object
containing `packet_id` and an integer `assignments` array and no additional root
properties.

For OpenAI model paths, the schema additionally uses `minItems` and `maxItems`
equal to the packet target count.

For Anthropic model paths, exact assignment count is enforced by the local
validator rather than relying on provider-specific optional array-length schema
support.

The local validator always verifies exact packet identity, exact assignment
count, and integer labels before deterministic canonicalization.

The frozen parent semantic instructions are unchanged. At runtime, only the
parent `Cluster IDs` / `Output` serialization sections are replaced by the
signed P1D2 output-encoding addendum.

## 8. Fresh execution namespace and attempt ceilings

P1D2 writes to a fresh output directory:

`api-study/exploratory/e1/stage2/partitions/AU-E1-S2-b021f4b9caf73dad/P1D2`

No P1/P1D1 attempt record is read as P1D2 execution state.

Every one of the 72 P1D2 tasks therefore begins with a fresh maximum of three
attempts under the corrected serialization contract.

Every P1D2 request carries:

- `execution_variant = "P1D2"`;
- `output_encoding = "assignment_vector_v1"`;

in its technical provenance and request fingerprint.

The predecessor execution costs remain preserved in the frozen predecessor
manifest. P1D2 cost guards apply to the fresh restart itself.

## 9. Recovery-focused canary gate

Before the remaining P1D2 roster may run, seven ordinary study partitions must
complete structurally valid outputs:

Original large-packet canaries:

- Sol P1 `R01-T04`;
- Opus P2 `R02-T04`;
- Terra P3 `R01-T09`;
- Sonnet P3 `R02-T04`.

Failure-reproduction canaries:

- Opus P2 `R02-T08`;
- Terra P3 `R01-T05`;
- Terra P3 `R02-T09`.

These seven canaries are part of the fresh 72-task P1D2 execution and count as
their final partitions if valid.

The full-run command refuses to start until all seven are valid.

## 10. Model settings

No model, reasoning/thinking, effort, pricing, or model-path cost-guard setting
changes in P1D2.

- Sol: `gpt-5.6-sol`, reasoning `low`, 16,000 output-token ceiling;
- Opus: `claude-opus-5`, adaptive thinking, effort `low`, 16,000 ceiling;
- Terra: `gpt-5.6-terra`, reasoning `low`, 16,000 ceiling;
- Sonnet: `claude-sonnet-5`, adaptive thinking, effort `low`, 64,000 ceiling as
  established by P1D1.

## 11. Pre-execution checks

Because the structured-output contract changes for all four model paths, P1D2
requires fresh synthetic tests of Sol, Opus, Terra, and Sonnet before real
canaries are launched.

Synthetic outputs are not study data.

## 12. Scientific status

P1D2 is a post-run technical correction to serialization and execution hygiene.
It does not change:

- the semantic target definition;
- the frozen blinded Stage 2 packets;
- the answer-space equivalence rule;
- the three-partition roster;
- representation/model/gap blinding;
- model assignments to partition replicates;
- the exploratory downstream analysis plan.

The final Stage 2 partition dataset will come entirely from the fresh P1D2
72-task execution, while P1/P1D1 remains preserved as superseded provenance.
