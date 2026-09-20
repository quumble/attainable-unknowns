# E1 Stage 2 — Blinded Topic-Level Partition Instructions

You are performing one blinded semantic-partitioning task for **Attainable Unknowns API Pilot 0.1, Exploratory Semantic Target Protocol E1 / E1A**.

You will receive exactly one opaque topic packet containing:

- `packet_id`
- `representation_set_id`
- `topic_packet_id`
- `targets`

Each target contains only:

- `target_id`
- `canonical_target`

Use only the supplied packet and these instructions. Do not use external sources, prior study knowledge, assumptions about the study condition, or guesses about which model produced the canonical targets.

## Task

Partition **all targets in the packet** by semantic answer-space equivalence.

Two targets belong in the same cluster when substantially the same answer, evidence, mechanism, quantity, relation, condition, comparison, or decision criterion would satisfy both **without a material change in scope**.

Targets that merely share vocabulary can belong in different clusters. Targets with different wording can belong in the same cluster.

Preserve distinctions that materially change the answer, including distinctions between:

- quantity and consequence;
- mechanism and correlation;
- descriptive fact and decision criterion;
- evidence for a claim and implications of that claim;
- threshold and general effect;
- conditions under which something occurs and what occurs;
- a general method and a particular implementation detail;
- an object's identity and the criteria used to determine that identity.

Do not create or merge clusters in order to obtain balanced sizes, a preferred number of clusters, stronger experimental differences, or cleaner-looking results.

There is **no minimum or maximum number of clusters**.

Singleton clusters are permitted.

Every target must appear in exactly one cluster.

## Cluster IDs

Cluster IDs are local, arbitrary bookkeeping labels only. They carry no semantic meaning.

Use consecutive IDs `C001`, `C002`, `C003`, and so on, in order of the first target from each cluster as it appears in the input packet.

Do **not** generate semantic cluster names in this task. Cluster names are generated only after membership has been frozen.

## Output

Return exactly one JSON object and nothing else:

```json
{
  "packet_id": "<copy exactly>",
  "clusters": [
    {
      "cluster_id": "C001",
      "target_ids": ["<target id>", "<target id>"]
    },
    {
      "cluster_id": "C002",
      "target_ids": ["<target id>"]
    }
  ]
}
```

Requirements:

- Copy `packet_id` exactly.
- Include every input `target_id` exactly once.
- Do not invent target IDs.
- Do not omit targets.
- Do not duplicate targets across clusters.
- Do not include `canonical_target` text in the output.
- Do not include semantic cluster names, explanations, confidence scores, model names, condition labels, topic labels, study hypotheses, or commentary.
- Do not include markdown fences around the returned JSON.
