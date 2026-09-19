# E1A Stage 1 — Dual Canonicalization Runner Procedure

**Study:** Attainable Unknowns API Pilot 0.1  
**Protocol:** E1 with Amendment E1A  
**Procedure:** Stage 1 dual-provider execution  
**Status:** Implementation candidate; operative only when preserved in the founder-signed runner implementation commit  
**Prepared:** 2026-09-19

## 1. Fixed inputs

The runner uses the already-anchored Stage 1 corpus identified by packet ID
`AU-E1-S1-cad71b8ce8fe0866`.

The runner must verify before real study calls:

- E1A adoption commit `084245d39e90eb98d76c98e22cc4be88d6c9be2f`;
- Stage 1 corpus checkpoint `15dbac07a615938464b03f5fa3e2539aed3ef8c1`;
- the exact hashes of the Stage 1 master packet, canonicalization instructions,
  and Stage 1 input manifest;
- a founder-signed runner implementation commit containing this procedure and
  the runner source.

A failed signature, ancestry, or input-hash check stops the affected branch.

## 2. Representations and API settings

Two complete representations are produced independently.

### Sol representation

- Provider: OpenAI
- Requested model: `gpt-5.6-sol`
- Responses API
- reasoning effort: `none`
- maximum output tokens: 160
- no conversational state or previous-response identifier
- no tools
- no sampling parameter override

### Opus representation

- Provider: Anthropic
- Requested model: `claude-opus-5`
- Messages API
- thinking: explicitly `disabled`
- maximum output tokens: 160
- one user message per independent request
- no tools
- no sampling parameter override

The same frozen Stage 1 instructions are used as the system/instruction text for
both providers.

The user payload is only the canonical JSON serialization of one frozen card:
`card_id`, `passage`, and `question`.

Provider-specific structured-output enforcement is not used in Stage 1. Both
representations therefore face the same instruction-level JSON requirement, and
the local runner applies the same validator afterward.

## 3. Independence and order

Each API request contains exactly one study card.

A client object may be reused for connection efficiency, but no prior response,
conversation identifier, message history, or semantic output is supplied to a
later request.

The runner processes cards in the fixed order already present in the frozen
master packet.

The Sol and Opus representations have separate output directories and logs and
may be executed at different times or concurrently. Neither receives or reads
the other representation's outputs.

## 4. Required returned structure

A returned semantic output is structurally valid only if its visible text parses
as exactly one JSON object with exactly these keys:

- `card_id`
- `canonical_target`
- `uncertain`

Additional requirements:

- `card_id` must exactly equal the dispatched card ID;
- `canonical_target` must be a nonempty string;
- `uncertain` must be a JSON boolean.

The validator does not judge whether the semantic target is good, reasonable,
interesting, aligned with another model, or consistent with study expectations.

A structurally valid output is final for that card. It is never retried because
its semantic content seems unusual or because `uncertain` is `true`.

## 5. Errors, invalid outputs, and retries

Every provider attempt is preserved in an append-only attempt log.

The runner stops the representation on the first:

- API/provider exception; or
- returned response that fails the structural validator.

It does not automatically continue through a stream of failures.

On a later invocation, a card lacking a structurally valid output may be retried
with the identical frozen semantic input and provider settings.

The total preserved attempt ceiling is **three attempts per card**, counting API
errors, structurally invalid returned outputs, and explicitly resolved orphaned
dispatches.

No fourth attempt is permitted by this runner. Reaching that ceiling without a
valid output requires a separately preserved decision before any further call.

This retry rule addresses technical noncompletion or structural invalidity only.
It may not be used to replace an unfavorable or surprising valid semantic code.

## 6. Interrupted in-flight requests

Immediately before each provider call, the runner writes an `INFLIGHT.json`
marker identifying the card, attempt number, start time, and request hash.

After a result or ordinary API error is durably appended to the attempt log, the
marker is removed.

If the process ends while a request is in flight, the marker remains. On resume,
the runner refuses to silently duplicate that request because provider-side
completion may be unknown.

The `resolve-inflight --action retry` operation preserves an
`orphaned_dispatch` record and removes the marker. That orphan counts against the
three-attempt ceiling. A later retry can then proceed transparently.

## 7. Resume and source of truth

`ATTEMPTS.jsonl` is the append-only execution source of truth.

On every run or validation pass, completed cards are reconstructed from the
attempt log. The first and only structurally valid result for a card is its Stage
1 representation.

`CANONICAL_TARGETS.jsonl` is deterministically rebuilt from the attempt log in
the frozen master-packet order. It is therefore a derived artifact, not an
independent editing surface.

More than one structurally valid output for the same card is treated as a
corruption condition and stops validation.

## 8. Cost boundaries

The runner records a conservative token-cost estimate from provider-reported
input and output token counts.

The pricing snapshot used for the implementation is:

- GPT-5.6 Sol: USD 4 per million input tokens and USD 20 per million output tokens;
- Claude Opus 5: USD 5 per million input tokens and USD 25 per million output tokens.

The estimate ignores any prompt-cache discount and is therefore intended as a
conservative operational record, not an invoice reconstruction.

Hard runner stop limits are:

- Sol: USD 15;
- Opus: USD 20.

Before execution, the runner also performs a conservative full-corpus estimate
using the configured maximum output allowance and refuses to start if that
estimate exceeds the stop limit.

## 9. Synthetic testing

Before the runner implementation is frozen, and optionally again afterward, each
provider path may be tested with the built-in synthetic fixture card.

The synthetic test uses the frozen Stage 1 instructions but does not read or
transmit any study card.

Synthetic outputs are used only to confirm API compatibility, JSON parsing,
model availability, and request settings. They are not Stage 1 data.

## 10. Completion boundary

A representation is complete only when all 1,984 frozen card IDs have exactly one
structurally valid canonical target.

After both the Sol and Opus representations are complete:

1. run the validator for both representations;
2. preserve the raw attempt logs, derived canonical-target files, manifests, and
   hashes;
3. freeze both complete Stage 1 representation sets in Git before constructing
   any Stage 2 packet.

Stage 2 must not begin from one completed representation while the other remains
incomplete.
