# E1A Stage 1 — Opus Output-Ceiling Correction D2

**Study:** Attainable Unknowns API Pilot 0.1  
**Protocol:** E1 with Amendment E1A  
**Record ID:** E1-STAGE1-OPUS-D2  
**Prepared:** 2026-09-20  
**Prior runner correction commit:** `56a60ddbbc8801986365c20d0d94fca74b7d6423`  
**Aborted Opus-160 anchor commit:** `ff0132294efd1710a96434a5511b470b427a7525`  
**Affected representation:** Opus  
**Status:** Technical correction candidate; operative only through the founder-signed implementation commit containing this record and the corrected runner

## 1. Incident and evidence

The first real Opus Stage 1 execution used Claude Opus 5 with thinking explicitly
disabled and `max_output_tokens = 160`.

That run produced 91 structurally valid cards before card
`AU-E1-S1-0092` failed twice.

Both preserved failures had the same proximal mechanism:

- attempt 1: `stop_reason = max_tokens`, `output_tokens = 160`, followed by an
  unterminated JSON string;
- attempt 2: `stop_reason = max_tokens`, `output_tokens = 160`, followed by an
  unterminated JSON string.

No structurally valid semantic result was accepted for `AU-E1-S1-0092` under the
160-token configuration.

The frozen post-stop validator reported:

- 93 attempt records;
- 91 valid cards;
- 1,893 remaining cards;
- 1 card with more than one attempt;
- maximum attempts for any card: 2;
- no remaining `INFLIGHT.json`;
- zero `uncertain: true` results among the 91 valid cards;
- conservative observed cost: USD 0.5877;
- `ATTEMPTS.jsonl` SHA-256:
  `d93505b44272b0d3c4e210a1a338ecc0d73ce6beebdf6946f753c3dffc7831a6`;
- `CANONICAL_TARGETS.jsonl` SHA-256:
  `b03c0254bc66882cfbf2b53fe486ddce7a7dcd21db7d94b49b529c276c75f74e`.

The aborted run is anchored at commit
`ff0132294efd1710a96434a5511b470b427a7525`.

## 2. Diagnosis boundary

D2 treats the demonstrated technical defect as an insufficient visible-output
ceiling for at least one Opus Stage 1 card under the frozen 160-token setting.

The two preserved truncations are sufficient evidence that 160 tokens is a
binding technical limit for this card.

D2 does **not** infer from those failures that disabling thinking caused the
verbosity or truncation.

Accordingly, D2 changes the demonstrated binding parameter while holding the
reasoning/thinking configuration fixed.

## 3. Corrected Opus configuration

The corrected complete Opus representation uses:

- Provider: Anthropic
- Requested model: `claude-opus-5`
- Messages API
- thinking: explicitly `disabled`
- maximum output tokens: **512**
- one user message per independent request
- no tools
- no sampling parameter override
- same frozen E1 Stage 1 instructions
- same frozen card packet
- same card order
- same structural output validator

The operational conservative stop limit for the corrected Opus run is raised
from USD 20 to **USD 40** so that the full-corpus preflight can accommodate the
larger technical output ceiling.

The stop limit is an operational guardrail, not an expected expenditure.

## 4. Full restart rather than mixed settings

The 91 valid canonical targets from the aborted 160-token execution are retained
as provenance but are **not** incorporated into the final Opus Stage 1
representation.

The corrected Opus representation restarts from card 1 and processes all 1,984
cards under the single corrected 512-token configuration.

This avoids a final Opus representation that mixes two output ceilings.

The original `opus` output directory remains preserved as the aborted 160-token
run.

The corrected runner writes the fresh complete run to:

`api-study/exploratory/e1/stage1_outputs/AU-E1-S1-cad71b8ce8fe0866/opus_d2_512`

The logical representation remains `opus`; `opus_d2_512` is an execution-variant
directory name only.

## 5. Attempt accounting

The aborted 160-token execution and the corrected D2 execution are distinct
technical execution variants.

The original 160-token attempt records remain immutable provenance.

Because D2 restarts the complete representation under a corrected configuration,
the three-attempt ceiling is applied afresh within the D2 execution variant.

No prior 160-token response is treated as a D2 semantic result, and no prior
160-token failure consumes one of the D2 variant's three technical attempts.

Within D2, a structurally valid semantic output remains final and is never retried
because its content is surprising, verbose, uncertain, or inconsistent with
another representation.

## 6. Parameters not changed

D2 does not change:

- the E1 semantic-target definition;
- the E1A dual-representation design;
- the frozen 1,984-card Stage 1 corpus;
- card IDs or card order;
- blinding fields;
- the canonicalization instructions;
- the requested Opus model product;
- the thinking configuration;
- provider route;
- semantic validity rules;
- Stage 2 design;
- interpretation limits.

D2 changes only the Opus visible-output ceiling, associated operational cost
guardrail, and execution directory necessary to produce a homogeneous corrected
Opus representation.

## 7. Continuation and preservation

Before the first real D2 study request, the corrected runner and this D2 record
must be preserved together in a founder-signed implementation commit.

The corrected signed preflight must show zero existing valid D2 cards and no
in-flight marker in the fresh `opus_d2_512` directory.

The aborted 160-token run must not be deleted, rewritten, or merged into the D2
output.

After D2 completes all 1,984 cards and validates cleanly, the final Sol and D2
Opus Stage 1 representations are frozen together before any Stage 2 packet is
constructed.

## 8. Evidentiary status

D2 is a technical correction within an explicitly post hoc exploratory semantic
analysis.

It does not convert E1 or E1A into confirmatory analysis and does not erase the
aborted execution that motivated the correction.
