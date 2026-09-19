# E1A Stage 1 — Runner Correction and Deviation Record D1

**Study:** Attainable Unknowns API Pilot 0.1  
**Protocol:** E1 with Amendment E1A  
**Record ID:** E1-STAGE1-RUNNER-D1  
**Prepared:** 2026-09-19  
**Original runner implementation commit:** `4d507553fe9a37f5a49c183a97537ae452a162ef`  
**Affected representation:** Sol  
**Affected card:** `AU-E1-S1-0814`  
**Status:** Technical deviation recorded; semantic result preserved

## 1. Incident

During the Sol Stage 1 run, card `AU-E1-S1-0814` received a structurally valid
provider response and the runner durably appended that valid semantic result to
`ATTEMPTS.jsonl`.

Immediately afterward, while the runner attempted to delete the local
`INFLIGHT.json` marker, Windows raised `PermissionError: [WinError 32]` because
another process was temporarily reading that marker.

The progress-monitoring PowerShell loop used at the time read `INFLIGHT.json` to
display the current card. On Windows, that read could transiently prevent the
runner from deleting the file.

Because marker deletion occurred inside the runner's broad provider exception
scope, the local cleanup exception was then incorrectly preserved as an
`api_error` record for the same card and attempt index.

No second provider request was made for the card.

## 2. Preserved evidence

The append-only attempt log contains, in order:

1. a `valid` record for `AU-E1-S1-0814`, attempt index 1, with a parsed canonical
   target and provider token usage; and
2. an `api_error` record for the same card, same attempt index, same start time,
   and same request SHA, whose error is the local `PermissionError` on
   `INFLIGHT.json`.

The post-incident validator reported:

- 815 attempt-log records;
- 814 valid cards;
- 1 card with more than one preserved attempt record;
- maximum preserved records for any card: 2;
- 1,170 cards remaining;
- no remaining `INFLIGHT.json`;
- zero `uncertain: true` results among the 814 valid Sol cards;
- conservative observed cost: USD 2.27206;
- `ATTEMPTS.jsonl` SHA-256:
  `e21f021a2db42c6a105b5bb92cca8b33334648817f2fe980ab472627c0f918d2`;
- `CANONICAL_TARGETS.jsonl` SHA-256:
  `6d45b31195e94214e5aeebd74de007433814ccdadae8cd971baaac132dfb21f7`.

The valid semantic result for `AU-E1-S1-0814` remains final under the signed
procedure. It is not recoded or replaced.

The spurious `api_error` row is retained in the append-only log as provenance. It
is interpreted as a runner-cleanup logging artifact, not as semantic
noncompletion and not as evidence of a second provider call.

## 3. Scope

This incident does not change:

- any frozen study card;
- the E1 or E1A semantic-target definition;
- the Sol canonical target already preserved for `AU-E1-S1-0814`;
- provider model or request settings;
- the Stage 1 blinding boundary;
- the rule that a structurally valid semantic output is final.

The incident does reveal a technical defect in the original runner:
a local `INFLIGHT.json` cleanup failure could enter the provider/API-error
exception path after a valid response had already been preserved.

## 4. Corrective implementation

The D1 runner correction makes only technical state-management changes.

1. `INFLIGHT.json` removal uses a bounded retry loop for transient Windows file
   locks.
2. Failure to remove the marker after a preserved attempt raises a local cleanup
   stop, not an `api_error`.
3. On resume, a surviving `INFLIGHT.json` marker is automatically cleared only
   when the append-only attempt log already contains a matching terminal record
   with the same card ID, attempt index, and request SHA.
4. If no matching terminal record exists, the prior ambiguous-dispatch rule
   remains in force and the runner refuses to repeat the request silently.
5. The append-only attempt log is not rewritten to remove or edit the D1 incident.
6. The progress monitor should read `ATTEMPTS.jsonl` only and should not read
   `INFLIGHT.json` during active execution.

No change is made to the semantic prompt, output schema, model settings, card
order, attempt ceiling, or semantic decision rule.

## 5. Continuation rule

The Sol run may continue from the existing append-only log after the corrected
runner is preserved in a new founder-signed implementation commit and its signed
preflight succeeds.

Already valid cards are reconstructed from `ATTEMPTS.jsonl` and are not sent
again.

`AU-E1-S1-0814` therefore remains completed and must not receive a second semantic
canonicalization request because of this cleanup incident.

The Opus run should use the corrected runner from its first real study request.

## 6. Evidentiary status

D1 is a technical deviation/correction record within an exploratory analysis.
It does not convert E1 or E1A into confirmatory analysis and does not erase the
original execution artifact.

The original runner commit and the append-only incident records remain part of
the provenance chain.
