# E1 Stage 2 — P1D3 Fixed-Width Partition Output Encoding

This file replaces only the `Cluster IDs` and `Output` sections of the parent
Stage 2 partition instructions for P1D3 API execution.

The semantic partitioning task and answer-space equivalence rule in the parent
instructions are unchanged.

## Fixed-width cluster labels

First decide the semantic partition for the entire supplied packet.

Then encode that partition using one three-digit decimal code for every target,
in the exact order the targets appear in the input packet.

Targets belong to the same semantic cluster if and only if their three-digit
codes are identical.

The numeric values are arbitrary labels only. They do not carry ordinal,
quantitative, or semantic meaning.

Any three-digit value from `000` through `999` may be used.

For example, a five-target partition in which targets 1 and 2 share a cluster,
targets 3 and 5 share another cluster, and target 4 is a singleton can be
encoded as:

```text
001001002003002
```

The same partition could equally be represented as:

```text
731731004999004
```

because only equality of three-digit codes matters.

## Output representation

Return exactly one JSON object with:

- `packet_id`: copy the supplied packet ID exactly;
- `assignment_code`: the concatenated three-digit cluster codes.

If the packet contains N targets, `assignment_code` must contain exactly
`3 * N` decimal digits.

Do not include separators, spaces, commas, line breaks, prefixes, target IDs,
or explanatory text inside `assignment_code`.

Example:

```json
{
  "packet_id": "EXAMPLE",
  "assignment_code": "001001002003002"
}
```

Requirements:

- Encode exactly one three-digit code for every input target.
- Preserve exact input-target order.
- Use the same code if and only if two targets belong to the same semantic
  answer-space cluster.
- Decide cluster membership from the frozen answer-space equivalence rule, not
  lexical resemblance, desired cluster count, treatment balance, or
  anticipated study results.
- Singleton clusters are permitted.
- Do not return semantic cluster names, explanations, confidence scores,
  model names, topic labels, condition labels, hypotheses, or commentary.
- Do not wrap the JSON in markdown fences.

The local runner will split the fixed-width string into three-digit labels and
deterministically renumber labels by first occurrence into `C001`, `C002`, ...
for downstream storage. That renumbering does not change semantic cluster
membership.
