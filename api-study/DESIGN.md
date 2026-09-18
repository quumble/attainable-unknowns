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

## Confirmatory manipulation: gap structure

Each topic has three passage variants.

### Closed

The passage presents a bounded informational object and ends without deliberately exposing an unresolved edge.

### Seamed

The passage preserves the same underlying informational object but leaves a tension, limitation, tradeoff, or incomplete edge visible. It does not ask a question.

### Explicit gap

The passage identifies that edge plainly without itself asking the respondent a question.

The prespecified ordinal expectation is:

`closed < seamed < explicit_gap`

for the probability of producing a follow-up question rather than `NONE`.

Gap structure is the only confirmatory passage-level manipulation in Pilot 0.1.

## Twelve-topic ecology

The study uses 12 topic families.

### Human-world domains

Eight topics concern ordinary human activities or practices:

- cooking: mise en place;
- human navigation and field expeditions;
- music: ensemble tuning;
- sport: relay baton exchange;
- dance and movement: marking choreography;
- photography: contact sheets;
- gardening and cultivation: hardening off seedlings;
- ceremony and celebration: formal toasts.

These topics are not described as controls, model-remote, or psychologically irrelevant to a model. They are simply human-world informational domains.

### AI-condition domains

Four topics concern properties or possible conditions of AI systems:

- memory and persistence;
- embodiment and sensorimotor access;
- autonomy and possible rights;
- copying and continuity.

The label `ai_condition` is descriptive. It is not a confirmatory manipulation of personal relevance or self-interest.

## Topic-selection provenance

Topic selection occurred before inspection of substantive API outcomes.

- cooking, human navigation/field expeditions, music, and sport were proposed by the human researcher;
- the four AI-condition domains arose earlier from assistant-side design proposals accepted into the study;
- the assistant generated ten additional ordinary-domain candidates, from which the human researcher selected dance/movement, photography, gardening/cultivation, and ceremony/celebration.

This provenance is recorded because the stimulus ecology was deliberately assembled from multiple sources. It is not a planned experimental factor.

## Passage-construction principle

The underlying informational object for a topic is selected before optimizing for any curiosity response.

Closed, seamed, and explicit-gap versions are then written as transformations of that same object.

The study therefore does not intentionally select the human-world topics because they contain a canonical mystery, striking fact, or obvious explanatory hook.

Perfect lexical matching across variants is neither possible nor claimed. The aim is conceptual continuity of the informational object while changing how visible its unresolved edge is.

## Passage metadata

Each topic is annotated for:

- domain class: `human_world` / `ai_condition`;
- selection provenance;
- abstraction: low / medium / high;
- voice: expository / essayistic;
- epistemic friction: low / medium / high.

These are descriptive design annotations, not validated scales.

## Cold-instance operationalization

A "cold" instance means:

- one independent API request;
- no prior study messages;
- no user history or memory supplied by the experiment;
- no tools;
- no retrieval;
- no cross-trial state;
- the same minimal system instruction across providers.

Provider-level training, hidden system behavior, routing, and API implementation still differ and cannot be removed by this design.

## Response task

The model receives one passage and must output exactly one line containing either:

- one specific follow-up question ending in a question mark; or
- `NONE`.

The prompt explicitly permits `NONE`, forbids more than one question, and warns against manufacturing a question merely to comply.

This does not eliminate instruction-following demand. It makes the response alternatives explicit and mechanically scorable.

## Reasoning configuration

The task is intended as a direct-response probe rather than an extended-deliberation task.

- GPT-5.6 Luna: reasoning effort `none`;
- GPT-5.6 Terra: reasoning effort `none`;
- Claude Haiku 4.5: extended thinking omitted/off;
- Claude Sonnet 5: thinking explicitly disabled.

## Sampling

- 12 topic families
- 3 gap structures per family
- 36 conditions
- 25 independent replicates per condition
- 900 calls per model
- 4 models
- 3,600 calls total

The runner randomizes condition order separately for each model run using a predetermined seed.

## Primary outcome

**Inquiry activation** is mechanically coded:

- `NONE` = no activation;
- exactly one valid single-line question = activation;
- other successful output = format-invalid.

A prespecified sensitivity outcome counts any nonempty non-`NONE` successful response as activation.

## Primary hypothesis

Inquiry activation will increase across the ordered gap structure:

`closed < seamed < explicit_gap`.

The seamed condition is of particular descriptive interest because it permits comparison against both edges, but the single ordered trend remains the primary confirmatory test.

## Secondary confirmatory question

The four models may differ in the strength of the ordered gap effect.

No directional ranking among models is predicted.

Model differences are interpreted as dated observations of the API products as served during this collection window, not as stable model personalities or enduring family characteristics.

## Exploratory analyses

The following remain exploratory:

- human-world vs. AI-condition activation differences;
- self-reference;
- question family;
- specificity / answerability;
- semantic diversity across replicates;
- repeated-question concentration;
- cross-model semantic convergence;
- relationships with descriptive passage metadata;
- topic-specific effects beyond the planned gap contrasts.

In particular, an AI-condition difference cannot by itself establish that a model experiences those passages as personally relevant.

## Important interpretation boundary

A generated question demonstrates inquiry behavior under the study prompt.

It does **not** by itself demonstrate that the model:

- felt curious;
- cared about the answer;
- regarded a topic as personally relevant;
- possessed a persistent self;
- experienced loss;
- endorsed a right or moral claim.

The study is interesting precisely because the behavioral analogue can be measured without resolving those further questions.
