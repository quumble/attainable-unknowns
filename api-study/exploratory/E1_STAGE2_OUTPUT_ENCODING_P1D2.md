# E1 Stage 2 — P1D2 Assignment-Vector Output Encoding

This file replaces only the `Cluster IDs` and `Output` serialization sections of
the parent Stage 2 partition instructions during P1D2 execution.

The semantic partitioning task and answer-space equivalence rule in the parent
instructions are unchanged.

## Output representation

After deciding the partition for the entire supplied packet, return exactly one
JSON object containing:

- `packet_id`: copy the supplied packet ID exactly;
- `assignments`: one integer cluster label for every target, in the exact order
  the targets appear in the input packet.

Example for five input targets:

```json
{
  "packet_id": "EXAMPLE",
  "assignments": [1, 1, 2, 3, 2]
}
```

In that example, targets 1 and 2 share one semantic cluster, targets 3 and 5
share another, and target 4 is a singleton.

The integer labels are arbitrary bookkeeping symbols. They do not carry semantic
meaning and do not need to be consecutive or ordered.

Requirements:

- The assignment array must contain exactly one integer for every input target.
- Preserve the exact target order from the input packet.
- Do not omit a target or add an extra assignment.
- Two targets belong to the same cluster if and only if their integers are equal.
- Decide membership from semantic answer-space equivalence, not lexical
  resemblance, desired cluster count, treatment balance, or anticipated study
  results.
- Singleton clusters are permitted.
- Do not return target IDs, canonical target text, semantic cluster names,
  explanations, confidence scores, model names, topic labels, condition labels,
  hypotheses, or commentary.
- Do not wrap the JSON in markdown fences.

The local runner deterministically renumbers arbitrary integer labels by first
occurrence and reconstructs the study's canonical `C001`, `C002`, ... cluster
representation. That canonicalization does not change semantic membership.
