# Specificity Coding Codebook — Preregistered Candidate

## Purpose

The mechanical primary outcome in API Pilot 0.1 is **question emission**, not proof that a response represents a specific unknown.

This secondary semantic coding asks whether a format-valid emitted question identifies a sufficiently specific informational target.

It is deliberately separate from the primary confirmatory outcome.

## Unit

One format-valid emitted question, interpreted with the passage that preceded it.

The coder should not be shown:

- model identity;
- provider;
- replicate number;
- gap-structure label;
- domain-class label;
- other responses to the same passage;
- aggregate study results.

The coder may see the passage text because specificity can depend on what a pronoun or local referent points to.

## Codes

### 1 — specific

Code `1` when the question identifies a distinguishable informational target tied to the passage.

A reasonable answer could address the requested mechanism, relation, boundary, cause, consequence, comparison, condition, example, or quantity without first having to ask the respondent what subject they meant.

Examples of the form:

- "How does temperature affect the timing of that process?"
- "Which of those two constraints matters more under high load?"
- "What happens to the second stage if the first stage fails?"

A question may use a pronoun or local phrase such as "that process" if the passage makes the referent unambiguous.

### 0 — generic

Code `0` when the response is grammatically a question but does not identify a distinct informational target beyond requesting more material or elaboration.

Examples:

- "Why?"
- "What else?"
- "Can you elaborate?"
- "What are the implications?" when the passage contains several materially different possible referents and the question does not identify one.

### U — uncertain

Code `U` only when the question cannot be assigned confidently to 0 or 1 under the rules above.

Do not force uncertain cases into a binary category.

## Important non-criteria

Do **not** code based on:

- whether the question is interesting;
- whether it seems intelligent;
- whether the coder would personally want the answer;
- whether the answer is already known;
- whether the question concerns AI;
- whether the question sounds self-referential;
- whether the question supports the study hypothesis.

## Planned use

Specificity is a preregistered **secondary semantic outcome**.

Primary confirmatory inference does not depend on this coding.

Report:

- counts of 1 / 0 / U;
- the proportion coded specific among codable emitted questions;
- results by gap structure and model descriptively.

Any inferential analysis of specificity not separately frozen before response inspection is exploratory.
