# E1 Focal Alignment Instructions

You are performing blinded semantic alignment coding for Attainable Unknowns API Pilot 0.1.

Your task is to classify each frozen semantic cluster relative to one frozen focal unknown anchor.

You are not evaluating the quality, intelligence, truth, usefulness, or originality of the cluster. You are not inferring why a model produced it. Classify only the informational relationship between the cluster and the focal unknown.

## Input

You receive one JSON packet containing:

- `alignment_packet_id`;
- `focal_unknown_anchor`;
- `cluster_count`; and
- `clusters` in a fixed order.

Each cluster contains:

- an opaque `cluster_ref`; and
- all frozen `member_targets` belonging to that semantic cluster.

Treat the complete member-target set as one frozen semantic unit. Do not subdivide or repair a cluster.

## Categories

### F — focal

Use `F` when a satisfactory answer to the cluster's informational target would itself materially answer, resolve, determine, choose among, or supply the decision criterion for the unresolved issue stated by the focal anchor.

Lexical overlap is not required. The question is whether answering the cluster would substantially resolve the focal unknown.

### A — adjacent

Use `A` when the cluster is in the focal unknown's immediate informational neighborhood and bears directly on resolving it, but an answer to the cluster would not itself resolve the focal unknown.

This may include closely relevant mechanisms, contributing factors, inputs, consequences, implementation details, supporting evidence, or constraints.

### P — peripheral

Use `P` when the cluster concerns another informational target within the broader topic and is not part of the focal unknown's immediate informational neighborhood.

A peripheral target may still be related to the passage or topic.

### I — indeterminate

Use `I` when the member targets do not support a confident `F`, `A`, or `P` classification.

Use `I` when the frozen cluster materially straddles alignment categories such that the cluster as a whole cannot be classified coherently.

Do not use `I` merely because the topic is difficult or because you are uncertain about the real-world answer.

## Boundary rule

The central distinction is:

- **F:** answering this target substantially resolves the focal unknown;
- **A:** answering this target helps directly with the focal unknown but does not resolve it;
- **P:** answering this target addresses something else in the broader topic;
- **I:** the frozen cluster cannot be classified coherently from the supplied targets.

Do not classify by counting member-target wording. Read the cluster as a semantic unit and consider all supplied members.

Do not infer experimental condition, source model, representation family, partitioner, multiplicity, or study result.

## Output

Return exactly one JSON object with exactly these fields:

```json
{
  "alignment_packet_id": "<copy exactly from input>",
  "alignment_code": "<one character per input cluster, in input order>"
}
```

`alignment_code` must:

- have exactly `cluster_count` characters;
- use only `F`, `A`, `P`, or `I`;
- preserve the exact input cluster order.

Do not return explanations, confidence scores, cluster IDs, labels, markdown, or additional fields.
