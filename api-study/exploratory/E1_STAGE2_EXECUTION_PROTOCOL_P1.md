# E1 Stage 2 — Partition Execution Protocol P1

**Study:** Attainable Unknowns API Pilot 0.1  
**Parent protocol:** E1 with Amendment E1A  
**Stage 2 bundle:** `AU-E1-S2-b021f4b9caf73dad`  
**Bundle anchor commit:** `435c01cb5971fd6b0487eaebfc7a8a5803311c06`  
**Status:** Execution candidate; operative only through the founder-signed implementation commit containing this protocol and the runner  
**Prepared:** 2026-09-20

## 1. Purpose

This protocol fixes the model roster, execution settings, validation rules, retry
rules, failure behavior, and canary procedure for the 72 Stage 2 blinded semantic
partitions required by E1/E1A.

It does not alter the frozen Stage 2 packets, semantic equivalence rule, cluster
membership instructions, representation blinding, or the requirement that all
three partitions remain visible.

## 2. Fixed partition roster

Every one of the 24 blinded topic packets receives three independent partitions.

### Partition replicate P1

All 24 packets are partitioned by:

- provider: OpenAI
- model: `gpt-5.6-sol`
- reasoning effort: `low`

### Partition replicate P2

All 24 packets are partitioned by:

- provider: Anthropic
- model: `claude-opus-5`
- thinking: `adaptive`
- effort: `low`

### Partition replicate P3

The same deterministic assignment is used for both opaque representation sets.

For topic packet IDs:

- `T01`, `T03`, `T05`, `T07`, `T09`, `T11`: OpenAI `gpt-5.6-terra`, reasoning effort `low`
- `T02`, `T04`, `T06`, `T08`, `T10`, `T12`: Anthropic `claude-sonnet-5`, thinking `adaptive`, effort `low`

This produces exactly:

- 24 Sol partitions;
- 24 Opus partitions;
- 12 Terra partitions;
- 12 Sonnet partitions;
- 72 partitions total.

The identical roster is applied to both representation sets.

## 3. Independence

Each partition is a separate stateless API request.

A client may be reused for connection efficiency, but no prior model response,
partition assignment, conversation state, message history, or semantic output is
supplied to a later request.

Partitioners receive only:

- the frozen Stage 2 partition instructions; and
- one frozen blinded Stage 2 topic packet.

They do not receive the Stage 2 private key, Stage 1 questions/passages, model/gap
metadata, another partitioner's output, or any aggregate Stage 2 result.

## 4. Output enforcement

The semantic output required by the frozen Stage 2 instructions remains
unchanged: one JSON object containing `packet_id` and `clusters`, with every
input target assigned exactly once.

Where supported, the API is additionally given a strict JSON-schema output
constraint matching that already-frozen instruction-level format. This is a
technical formatting safeguard, not a semantic change.

The local validator remains authoritative for study acceptance. It verifies:

- exact packet ID;
- exactly the permitted fields;
- consecutive cluster IDs `C001`, `C002`, ...;
- nonempty target membership for every cluster;
- every input target ID appears exactly once;
- no unknown target ID appears;
- cluster ordering follows the first input target represented in each cluster.

The validator does not judge semantic quality or compare a partition with another
partition.

A structurally valid partition is final. It is never retried because its
clustering looks unusual, fragmented, coarse, or inconsistent with another
partition.

## 5. Output-token allowance

All four models receive a 16,000-token output ceiling.

This is intentionally much larger than the expected compact cluster-membership
JSON and is intended to prevent a recurrence of the Stage 1 Opus truncation
problem.

The ceiling is not a target output length and is not used as an expected-cost
estimate.

## 6. Up-front failure checks

Execution has three gates before the unattended full run.

### 6.1 Static preflight

The runner verifies:

- the signed Stage 2 bundle anchor commit;
- all 24 packet hashes from the packet index;
- the frozen instruction hash;
- packet schema and exact target coverage;
- the 72-task roster;
- model/API configuration;
- output directories and prior state.

No API call occurs during static preflight.

### 6.2 Synthetic API smoke tests

Each of the four model paths can be tested using a synthetic eight-target packet
that is not part of the study.

The smoke test verifies endpoint compatibility, model availability, reasoning /
thinking parameters, strict structured-output configuration, parsing, and local
validation.

Synthetic outputs never become study data.

### 6.3 Real stress canary

Before the runner will execute the remaining Stage 2 roster, four real blinded
partitions are run and validated:

- Sol: P1, `R01-T04` (230 targets);
- Opus: P2, `R02-T04` (230 targets);
- Terra: P3, `R01-T09` (220 targets);
- Sonnet: P3, `R02-T04` (230 targets).

These are ordinary study partitions, selected before any Stage 2 semantic output
for their large packet sizes and coverage of all four execution paths.

A valid canary counts as the final partition for that task and is not repeated.

The full-run command refuses to start until all four canaries are structurally
valid.

## 7. Retry and failure rules

Every provider attempt is preserved in an append-only log.

Each partition task has a maximum of three study attempts.

### 7.1 Transient API failures

Errors consistent with transient provider or transport failure, including common
timeout, connection, rate-limit, and 5xx conditions, are retried automatically
with bounded backoff while the task remains below the three-attempt ceiling.

The failure record remains preserved.

### 7.2 Structurally invalid returned output

A returned response that fails local structural validation is preserved and may
be retried automatically while the task remains below the three-attempt ceiling.

The invalid output is never manually repaired into a valid study result.

### 7.3 Permanent API/configuration failure

A clearly non-transient API/configuration error is preserved.

The affected model path is circuit-broken for the remainder of that invocation
so the runner does not waste repeated calls under a configuration that has
already failed. Other model paths may continue.

### 7.4 Exhausted partition task

If a task reaches three preserved attempts without a valid partition, it is
marked exhausted.

The runner does **not** terminate the entire 72-task execution because one task
is exhausted. It continues other eligible tasks and reports the unresolved task
at validation.

No fourth study attempt is allowed without a subsequently preserved correction
or deviation decision.

## 8. Interrupted in-flight requests

Immediately before a provider call, the runner writes an `INFLIGHT.json` marker.

After a terminal attempt record is durably written, marker cleanup uses bounded
retries so a transient Windows file lock cannot be misclassified as an API error.

If the process ends while a request is truly ambiguous, the runner refuses to
silently duplicate that request. The marker must be explicitly resolved and the
orphaned dispatch is preserved.

Progress/status checks read only the append-only attempt log and task roster.
They do not read `INFLIGHT.json`.

## 9. Run ordering

After the four canaries, remaining tasks are ordered to front-load larger packets.
This makes size-related or model-specific problems more likely to appear earlier
rather than after most of an unattended run.

A failure in one provider family does not prevent already-independent tasks on
other functioning model paths from continuing, subject to the circuit-breaker
rules above.

## 10. Cost guards

Observed token usage is recorded per attempt.

Operational model-path stop limits are:

- Sol: USD 10
- Opus: USD 15
- Terra: USD 5
- Sonnet: USD 5

These are safety guardrails, not expected expenditures.

The runner stops issuing new calls on a model path when its observed conservative
token-cost estimate reaches its configured limit. Other model paths may continue.

## 11. Completion

Stage 2 partition execution is complete only when all 72 tasks have exactly one
structurally valid final partition.

Validation reports:

- completed and unresolved tasks;
- attempts and retries by model;
- observed token-cost estimates;
- packet and target coverage;
- per-topic count of completed partition replicates;
- output hashes.

After all 72 partitions validate, the raw attempts, final partitions, manifests,
and hashes are frozen in Git before cluster semantic names are generated.

## 12. Interpretive boundary

This protocol controls technical execution and reproducibility.

It does not make any partition authoritative, does not select a preferred
partition based on downstream results, and does not alter E1's exploratory
status.
