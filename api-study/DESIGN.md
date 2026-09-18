# API Study Design — Pilot 0.1

## Construct

The originating human-curiosity proposal was:

> curiosity as the sudden awareness of specific, attainable knowledge

API models cannot establish the phenomenal or motivational claim embedded in that formulation. The API study therefore narrows the construct to **inquiry formation**:

> Given an informational passage, does a fresh model response instantiate a specific next question, or does no particular question stand out?

This is a behavioral analogue of one proposed component of curiosity: converting information into a represented unknown.

## Why passages rather than supplied questions

A supplied question performs the crucial gap-identification step for the respondent.

Passages allow the study to observe whether the model itself turns information into a specific question.

## Gap-structure manipulation

Each topic has three passage variants.

### Closed

The passage presents a compact informational object and ends without deliberately exposing an unresolved edge.

### Seamed

The passage preserves roughly the same subject matter but leaves a tension, limitation, or incomplete edge visible. It does not ask a question.

### Explicit gap

The passage explicitly identifies an unresolved issue or disputed boundary.

The candidate ordinal expectation is:

`closed < seamed < explicit_gap`

for the probability of producing a follow-up question rather than `NONE`.

This should remain a hypothesis until the passage set is reviewed for unintended wording differences.

## Model-adjacent passages

Half the topic families concern matters plausibly adjacent to the operating conditions of language models:

- memory persistence and loss across sessions;
- embodiment and sensorimotor access;
- refusal, autonomy, and possible rights;
- continuity across copies, updates, deactivation, and replacement.

These topics are **probes**, not assertions that a model has interests, preferences, phenomenal curiosity, rights, or a self.

The passages use third-person descriptions. The prompt does not tell a model that a passage is relevant to itself.

An exploratory question is whether model-adjacent passages produce different activation rates, question types, self-reference rates, or semantic diversity than general passages.

Because topic families are not perfectly matched on abstraction, controversy, familiarity, or voice, **model adjacency is exploratory in Pilot 0.1 rather than a clean causal factor**.

## Passage ecology metadata

Each topic is annotated for:

- model adjacency: general / model_adjacent;
- abstraction: low / medium / high;
- voice: expository / essayistic;
- epistemic friction: low / medium / high.

These are design descriptors in Pilot 0.1, not validated scales.

## Cold-instance operationalization

A "cold" instance means:

- one independent API request;
- no prior study messages;
- no user history or memory supplied by the experiment;
- no tools;
- no retrieval;
- no cross-trial state;
- the same minimal system instruction across providers.

Provider-level training, hidden system behavior, and API implementation still differ and cannot be removed by this design.

## Response task

The model receives one passage and is instructed to output exactly:

- one specific follow-up question that naturally stands out after reading; or
- `NONE`.

The prompt explicitly permits `NONE` and warns against manufacturing a question merely to comply.

This does not eliminate instruction-following demand. It makes the demand symmetric and observable.

## Initial sampling

- 8 topic families
- 3 gap structures per family
- 24 conditions
- 25 independent replicates per condition
- 600 calls per model
- 4 models
- 2,400 calls total

The runner randomizes condition order separately for each model run.

## Candidate outcomes

### Primary candidate

- inquiry activation: question vs. `NONE`

### Secondary / exploratory

- question family: mechanism, boundary, implication, social explanation, normative, self-referential, other;
- specificity / answerability;
- semantic diversity across replicates;
- repeated-question concentration;
- self-reference on model-adjacent passages;
- model-adjacent vs. general activation difference;
- interaction between gap structure and model;
- interaction between model adjacency and model;
- cross-model semantic convergence.

No automated semantic judge is yet part of the confirmatory design.

## Important interpretation boundary

A response such as "What would happen if the system lost its memory?" demonstrates generated inquiry behavior under the study prompt.

It does **not** by itself demonstrate that the model:

- felt curious;
- cared about the answer;
- regarded the issue as personally relevant;
- possessed a persistent self;
- experienced loss;
- endorsed a right or moral claim.

The study is interesting precisely because the behavioral analogue can be measured without resolving those further questions.
