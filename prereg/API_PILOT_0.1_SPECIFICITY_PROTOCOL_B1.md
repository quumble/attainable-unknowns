# API Pilot 0.1 — Specificity Protocol B1

**Study:** Attainable Unknowns API Pilot 0.1
**Protocol ID:** B1
**Status:** Final candidate; adopted only by the founder-signed pre-packet commit containing this file
**Prepared:** 2026-09-19
**Stage:** Post-collection and post-primary-analysis; pre-packet generation and pre-semantic-coding
**Prepared for adoption by:** Robert Leo Duffy III / Bo Chesterton

## 1. Purpose and boundary

The frozen preregistration specifies a blinded semantic specificity outcome among format-valid emitted questions but does not specify a sampling fraction, number of coders, consensus procedure, or adjudication rule.

B1 fixes those remaining procedures before a coding packet is generated or any item receives a semantic code. It does not alter the mechanical primary endpoint, H1, H2, the accepted run set, any response, the frozen specificity codebook, or the adopted A1 analysis.

Specificity remains a secondary descriptive outcome. No inferential specificity test is introduced by B1.

## 2. Timing and knowledge disclosure

The four accepted confirmatory runs were complete and the A1 primary analysis had been run before B1 was written. The founder and the preparing assistant knew the broad primary result: the pooled strict `closed < seamed < explicit_gap` ordering was supported, and question-emission behavior differed substantially across models. They also knew mechanical counts of eligible emitted questions and the result of a content-blind workload-sizing calculation.

No semantic specificity code had been assigned to any study question when B1 was prepared. No item was selected, retained, excluded, or collapsed because of a judgment about its meaning or specificity.

During implementation review before B1 adoption, the preparing assistant displayed one raw record to confirm the stored field names and therefore saw that record's passage and question text. It did not assign a specificity code, search for that record during sampling, or use its content to choose the salt, sample size, stratification, duplicate rule, coder procedure, or reporting rules. This limited exposure is recorded rather than described as complete item-text blindness.

The founder will not serve as the initial coder. He may adjudicate disagreements under §9. He will remain blind to item-level model, provider, gap, topic-class, replicate, condition, run, and selection-rank metadata, but he is not blind to the aggregate primary result. This limitation must be reported.

## 3. Accepted run set and eligible population

The accepted set is fixed to these four complete 900-attempt runs:

| model key | run ID | raw JSONL SHA-256 |
|---|---|---|
| `luna` | `20260918T200715Z-luna-667cc52d` | `9f4d6ee729ee42360989e701cd62bc1801ca9a6b407650869ac9ef1f66d21236` |
| `terra` | `20260918T202517Z-terra-a31f0c2b` | `26e312ea7f1e493beb9e04be9a0320f462fafe2927812fdec9ad6d8537b9508e` |
| `haiku` | `20260918T210718Z-haiku-c13f68a4` | `2ce8f319e46c4fa836a72f6392125aa3762bd9f6c340477dbba8a0330debd762` |
| `sonnet` | `20260918T225249Z-sonnet-2059332f` | `627d372ea407103005b8244c8ab84548bdbf0310cea274a5052bdef89cba1c92` |

An observation is eligible exactly when it belongs to the accepted set and has:

- `status == "success"`;
- `format_valid == true`;
- `parsed_none != true`; and
- a nonempty string in `parsed_question`.

The mechanically determined eligible population contains 2,919 observations: Luna 624, Terra 720, Haiku 900, and Sonnet 675. These counts are not semantic judgments.

## 4. Fixed stratified sample

Sampling occurs at the observation level, without replacement, within each of the 12 model × gap cells.

- Strata: four `model_key` values × `closed`, `seamed`, and `explicit_gap`.
- Sample per stratum: 15 eligible observations.
- Total sampled observations: 180.

Within each stratum, eligible records are ordered by the lowercase hexadecimal value of:

```text
SHA256("AU-SPECIFICITY-V1|" + record_id)
```

Ties are broken by the literal `record_id` in ascending Unicode code-point order. The first 15 records are selected. If any required stratum has fewer than 15 eligible records, generation must stop; records may not be borrowed from another cell without a new disclosed amendment.

There is no replacement for a sampled record because it is repetitive, difficult, apparently obvious, or later produces coder disagreement.

## 5. Exact-visible duplicate collapse

Sampling is completed before duplicate collapse.

Two sampled observations share one coding card only when both of these stored strings are exactly equal, code point for code point:

1. `passage`; and
2. `parsed_question`.

No case folding, punctuation normalization, whitespace normalization, semantic clustering, embedding comparison, or paraphrase judgment is permitted. A card's final code maps back to every sampled observation represented by that card.

A mechanical pre-freeze sizing run of this exact rule found 180 sampled observations and 169 unique visible cards. That calculation assigned no semantic code and is disclosed because it occurred before B1 adoption.

## 6. Packet blinding and identifiers

Every coder sees only:

- an opaque card ID;
- the stored question text;
- the passage that preceded it; and
- the frozen specificity codebook and task instructions.

Coder packets must not contain model identity, provider, run ID, record ID, replicate, sequence, condition ID, gap label, domain-class label, topic labels, passage metadata, selection rank, other responses to the same passage, primary results, or any summary by hidden condition.

The passage itself may make aspects of topic or gap structure inferable. The frozen preregistration permits the passage because local reference resolution may require it. Labels and metadata are withheld; inference from visible wording cannot be eliminated and is not treated as a protocol breach.

The unblinding key is written separately from all coder packets. A coder is instructed to consult only its designated packet, the frozen codebook, and the coder instructions.

All three coder packets contain the same cards in separately determined orders. Card order for coder `Ck` is ascending:

```text
SHA256("AU-SPEC-CODER-ORDER-V1|" + Ck + "|" + card_id)
```

## 7. Three independent cold model coders

Three initial coders, `C1`, `C2`, and `C3`, code every unique card independently.

The planned execution is three fresh subagents launched concurrently with no inherited conversation history and no model override. Each receives only its designated blinded packet, `SPECIFICITY_CODEBOOK.md`, and `CODER_INSTRUCTIONS.md`. Equivalent fresh temporary chats may be used only if the subagent route is technically unavailable; the substitution and reason must be recorded before substantive codes are inspected.

Exact service/model identifiers, settings, timestamps, and agent or conversation identifiers are recorded when available. The three coders may be separate instances of the same underlying product. Agreement therefore measures agreement among these coding instances, not agreement among independent human experts and not semantic validity by itself.

Coders do not communicate and are not shown one another's output. A coder output may not be discarded or replaced because its codes appear unusual or reduce agreement. Mechanical omissions or invalid output are returned to the same coder for correction when possible. If technical noncompletion requires a replacement, the replacement must be a fresh cold context that codes the entire packet under the same coder ID, and the reason and discarded-file hash are preserved.

## 8. Codes and output validation

Each coder applies the frozen codes without additions:

- `1` — specific informational target;
- `0` — generic request for more information or elaboration;
- `U` — uncertain under the frozen rules.

Before reconciliation, a validator must confirm that each coder file:

- names the correct packet and coder;
- contains every expected card exactly once;
- contains no extra card;
- uses only `1`, `0`, or `U`; and
- preserves card IDs exactly.

Invalid or incomplete files do not enter consensus calculations.

## 9. Consensus and blinded founder adjudication

For each unique card:

- if all three initial codes are identical, that unanimous code is final;
- otherwise, the card enters founder adjudication.

There is no majority-vote finalization.

The founder receives a new packet containing only discordant cards, still stripped of all hidden study metadata. To reduce anchoring, the adjudication packet does not display the three model-coder votes or coder identities. The founder applies the same frozen codebook and selects `1`, `0`, or `U`; that code is final for the card.

The adjudication record must disclose that the founder knew the aggregate primary result and knew that every presented card had produced initial disagreement. The founder must not open the unblinding key before blind finalization.

## 10. Blind finalization before unblinding

The three raw coder files, any technical-correction or replacement record, the adjudication packet, the founder's adjudications, and the mechanically produced `BLIND_CODING_FINAL.json` are preserved before unblinding.

`BLIND_CODING_FINAL.json` contains card-level raw votes, resolution route, final code, input hashes, and descriptive agreement statistics, but no hidden model/gap metadata.

Before the unblinding key is merged, the blinded coding bundle must be committed in a founder-signed Git commit. The unblinding command must verify that signed commit and that the relevant blinded files match it.

## 11. Descriptive reporting

Report at minimum:

- sampled-observation and unique-card counts;
- raw counts of `1`, `0`, and `U` among the 180 sampled observations;
- model × gap counts and `1 / (1 + 0)` proportions, with `U` reported separately;
- descriptives collapsed by model, by gap, and overall;
- card-level unanimity rate, all three pairwise agreement rates, and Fleiss' kappa across `1`, `0`, and `U`;
- the number and proportion of cards requiring founder adjudication;
- coder identities/settings to the extent exposed by their services; and
- all deviations and technical replacements.

Within a model × gap cell, every sampled observation has the same sampling probability, so the cell proportion is the ordinary sample proportion among codable observations.

For any quantity collapsed across cells, use the design weight:

```text
w_h = N_h / 15
```

where `N_h` is the full eligible-observation count in model × gap stratum `h`. The weighted proportion specific among codable observations is the weighted sum for code `1` divided by the weighted sum for codes `1` and `0`. Weighted uncertainty prevalence is reported separately. Unweighted sample counts remain visible.

These are descriptive estimates for the eligible emitted-question population in the accepted runs. No hypothesis test, p-value, confirmatory confidence claim, or causal interpretation is added. Any later inferential specificity analysis is exploratory unless separately frozen before it is run.

## 12. Implementation and stopping rules

The following implementation files are frozen with B1:

- `api-study/specificity/generate_packet.py`;
- `api-study/specificity/coding_pipeline.py`;
- `api-study/specificity/coder.html`;
- `api-study/specificity/CODER_INSTRUCTIONS.md`; and
- `api-study/specificity/README.md`.

`prereg/build_prepacket_freeze.py` creates the technical freeze record. Packet generation is forbidden until:

1. `PRIMARY_A1.json` and its run record exist;
2. the B1 candidate and implementation files have been hashed into the pre-packet freeze record;
3. the commit containing them has been signed by the founder; and
4. `git verify-commit` succeeds for the supplied freeze commit.

A failed validation or missing signature stops the affected branch. The generator must not silently repair, replace, or resample data.

## 13. Adoption

This file makes no claim that it is already frozen. B1 becomes operative only through the founder-signed pre-packet commit. That signed commit is the adoption evidence and authoritative timestamp.
