# Specificity Coder Instructions

You are one of three independent coders for a blinded secondary outcome.

Use only:

1. your designated coder packet;
2. `api-study/SPECIFICITY_CODEBOOK.md`; and
3. this instruction file.

Do not inspect the surrounding repository, raw study data, other coder packets, other coder outputs, the unblinding key, or prior discussion of study results. Do not communicate with another coder.

For every card, return exactly one code from the frozen codebook:

- `1` — specific;
- `0` — generic;
- `U` — uncertain.

Judge only whether the visible question identifies a distinguishable informational target tied to the visible passage. Do not judge interest, intelligence, truth, novelty, importance, AI relevance, or support for a hypothesis.

Return a single JSON object in this shape:

```json
{
  "schema_version": "au-specificity-codes-v1",
  "packet_id": "copy from packet",
  "coder_id": "copy from packet",
  "coder_metadata": {
    "service": "if known",
    "model": "if known",
    "settings": "if known",
    "started_at_utc": "if known",
    "completed_at_utc": "if known"
  },
  "codes": [
    {"card_id": "copy exactly", "code": "1"}
  ]
}
```

Include every card exactly once, preserve the packet's card order, and add no prose outside the JSON object. Do not explain individual codes.
