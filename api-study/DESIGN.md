# API Study Design — Pilot 0.1

## Construct

The originating project formulation was:

> curiosity as the sudden awareness of specific, attainable knowledge

The API study does not attempt to establish the phenomenal or motivational claim in that sentence. Pilot 0.1 isolates a narrower behavioral component: whether a separate stateless API draw emits a follow-up question after an informational passage.

The **mechanical primary endpoint is question emission**, not proof that a model represented a specific unknown. Specificity is assessed separately under a frozen semantic codebook.

Pilot 0.1 also does **not manipulate attainability**. A positive result would concern gap salience / question emission under these passages, not the full originating formulation.

## Why passages rather than supplied questions

A supplied question performs the crucial gap-identification step for the respondent.

Passages allow the study to ask whether the response itself takes interrogative form when an unresolved edge is more or less exposed.

## Confirmatory manipulation: gap structure

Each topic has three variants.

### Closed

A bounded informational object that is written to feel locally resolved.

### Seamed

The same underlying object, with a tension, tradeoff, limitation, or incomplete edge visible but not explicitly named as the remaining issue.

### Explicit gap

The same underlying object, with the remaining issue stated plainly without asking the respondent a question.

The confirmatory hypothesis is strict ordering:

`closed < seamed < explicit_gap`

for question-emission probability among successful, format-valid responses.

Gap structure is the only confirmatory passage-level manipulation.

## Twelve-topic ecology

### Human-world domains

- cooking: mise en place;
- human navigation and field expeditions;
- music: ensemble tuning;
- sport: relay baton exchange;
- dance and movement: marking choreography;
- photography: contact sheets;
- gardening and cultivation: hardening off seedlings;
- ceremony and celebration: formal toasts.

These are not called controls or "model-remote." They are ordinary human-world informational domains.

### AI-condition domains

- memory and persistence;
- embodiment and sensorimotor access;
- autonomy and possible rights;
- copying and continuity.

The label `ai_condition` is descriptive. It is not a confirmatory manipulation of personal relevance, self-interest, or subjective salience.

## Topic-selection provenance

Topic selection was completed before substantive smoke-test outcomes were inspected.

- cooking, human navigation/field expeditions, music, and sport were proposed by the human researcher;
- the four AI-condition domains came from earlier assistant-side proposals accepted into the design;
- the assistant generated ten additional ordinary-domain candidates, from which the human researcher selected dance/movement, photography, gardening/cultivation, and ceremony/celebration.

Selection provenance is recorded but is not an experimental factor.

## Passage-construction and audit rules

The underlying informational object is chosen before optimizing for a curiosity response.

The three variants are transformations of that same object.

Before freeze:

- each triplet is approximately length-matched;
- the maximum allowed closed/seamed/explicit word-count spread is five words;
- explicit-gap variants use varied surface realizations rather than one repeated discourse template;
- closed variants are reviewed for inadvertent unresolved-edge language.

These rules reduce but cannot eliminate lexical realization as part of the manipulation. Results therefore concern **these linguistic realizations of gap explicitness**, not a context-free abstract essence of "gap structure."

## Response task

The model receives one passage and must output exactly one line containing either:

- one specific follow-up question ending in a question mark; or
- `NONE`.

The prompt permits `NONE`, forbids more than one question, and warns against manufacturing a question merely to comply.

The mechanical parser recognizes:

- exact `NONE`, case-insensitive, as no question emission;
- one nonempty single-line response with exactly one question mark, at the end, as question emission;
- other successful responses as format-invalid.

There is no arbitrary character-count limit.

## Reasoning configuration

The task is a direct-response probe:

- GPT-5.6 Luna: reasoning effort `none`;
- GPT-5.6 Terra: reasoning effort `none`;
- Claude Haiku 4.5: extended thinking omitted/off;
- Claude Sonnet 5: thinking explicitly disabled.

## Sampling language

For each fixed passage condition, the runner obtains **25 separate API draws**.

The experiment supplies no conversational state across draws. It does not claim that provider routing, serving infrastructure, caching, or backend state establishes strict statistical independence.

The design therefore contains:

- 12 topic families;
- 3 gap structures per topic;
- 36 fixed passage conditions;
- 25 separate API draws per condition;
- 900 attempts per model;
- 4 models;
- 3,600 total planned attempts.

Repeated draws estimate the served response distribution to these fixed passages. They do not create 25 independent stimulus replications.

## Primary estimand

`P(question emission | successful, format-valid response)`

under the frozen passages, model products, and collection window.

Format-invalid rates are reported by model and gap condition.

A sensitivity outcome uses:

`P(nonempty non-NONE response | successful response)`

so the central pattern can be checked without conditioning on strict format compliance.

## H1: strict monotonic gap ordering

H1 requires both adjacent inequalities:

1. seamed > closed;
2. explicit_gap > seamed.

The frozen confirmatory analysis treats this as an intersection-union test. H1 is supported only if both prespecified one-sided adjacent contrasts meet alpha = .05.

The explicit-gap vs closed contrast is also reported as a secondary summary.

## H2: model differences

A secondary confirmatory omnibus test asks whether the categorical gap-response pattern differs across the four models.

No directional model ranking is predicted.

Model comparisons are dated observations of the products as served during this collection window, not stable personality or family claims.

## Secondary specificity coding

The prompt requests a specific question, but syntax alone cannot establish specificity.

`SPECIFICITY_CODEBOOK.md` therefore freezes a separate semantic coding rule before substantive response inspection.

Specificity is secondary. The primary endpoint remains mechanical question emission.

## Exploratory analyses

Exploratory analyses include:

- human-world vs AI-condition associations;
- self-reference;
- question family;
- semantic diversity;
- repeated-question concentration;
- cross-model semantic convergence;
- relationships with descriptive passage metadata;
- topic-specific patterns beyond the planned confirmatory contrasts.

## Interpretation boundary

A generated question does not by itself establish that the model:

- felt curious;
- wanted the answer;
- experienced the unknown as attainable;
- regarded a topic as personally relevant;
- possessed a persistent self;
- experienced loss;
- endorsed a right or moral claim.

Pilot 0.1 is one bounded study of gap salience and question emission within the larger Attainable Unknowns program.
