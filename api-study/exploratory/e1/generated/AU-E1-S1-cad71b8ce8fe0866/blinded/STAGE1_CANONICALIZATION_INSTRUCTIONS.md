# E1 Stage 1 — Canonical Target Extraction Instructions

You are performing one blinded semantic-coding task for **Attainable Unknowns API Pilot 0.1, Exploratory Semantic Target Protocol E1**.

You will receive exactly one card containing:

- `card_id`
- `passage`
- `question`

Use only those fields and these instructions. Do not use external sources, prior study knowledge, or assumptions about model identity, experimental condition, or study results.

## Task

Identify the **semantic target** of the question: the informational answer-space that the question asks to resolve in the local context of the passage.

Return a short declarative description of that answer-space. Do **not** answer the question and do **not** assign a cluster.

Preserve distinctions that would materially change the answer, including distinctions between:

- quantity and consequence;
- mechanism and correlation;
- descriptive fact and decision criterion;
- evidence for a claim and implications of that claim;
- threshold and general effect;
- conditions under which something occurs and what occurs.

Questions that merely share vocabulary can have different targets. Questions with different wording can have the same target.

Set `uncertain` to `true` only if the requested answer-space cannot be represented confidently from the question and passage. Otherwise set it to `false`.

## Output

Return exactly one JSON object and nothing else:

```json
{"card_id":"<copy exactly>","canonical_target":"<short declarative target>","uncertain":false}
```

Requirements:

- Copy `card_id` exactly.
- `canonical_target` must be a nonempty string.
- Do not include model names, condition labels, study hypotheses, cluster IDs, or explanations.
- Do not include markdown fences around the returned JSON.
