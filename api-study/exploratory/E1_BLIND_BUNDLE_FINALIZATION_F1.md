# E1 Blind Semantic Bundle Finalization F1

**Study:** Attainable Unknowns API Pilot 0.1
**Parent protocol:** E1 with Amendment E1A
**P1D3 partition freeze:** `fb54cd0c37841e880372694e056d985ac3272b40`
**Status:** Final candidate; operative only through the founder-signed commit containing this record and `finalize_e1_blind_bundle.py`.

## Purpose

E1 requires the blind semantic bundle to be preserved before original response
model/gap metadata are joined to semantic outputs. P1D3 membership is frozen.
F1 creates the two remaining pre-unblinding artifacts: descriptive cluster names
and passage-only focal-unknown anchors.

F1 never reads the E1 private metadata keys.

## Cluster names

For each of the 72 frozen P1D3 partitions, GPT-5.6 Sol (`low` reasoning) receives
only the fixed cluster IDs and the blinded canonical targets belonging to each
cluster. It receives no original response model/provider, gap condition,
multiplicity, topic name, question, passage, or downstream result.

It returns exactly one short descriptive name per fixed cluster, in cluster
order. Names are explanatory metadata only and may not alter, merge, split,
select, or repair cluster membership.

Maximum three technical attempts per partition. Output ceiling: 12,000 tokens.
The attempt log is append-only.

## Focal anchors

For each topic in `api-study/passages.json`, the focal anchor is mechanically
defined as the **verbatim final sentence of the `explicit_gap` passage**.

This procedure reads no questions, canonical targets, partitions, multiplicities,
or response-model metadata. The source topic ID and full source passage are
preserved in the anchor record, but anchors are not linked to opaque Stage 2
topic-packet IDs during F1.

## Frozen input check

The runner requires the frozen P1D3 partition SHA-256:

`605d95f063d01349e95ebb126aa512796cb4f1fc9b12fae7862bacb8073e2aea`

## Outputs

`api-study/exploratory/e1/blind_bundle/AU-E1-BLIND-v1/`

- `CLUSTER_LABEL_ATTEMPTS.jsonl`
- `CLUSTER_LABELS.jsonl`
- `FOCAL_ANCHORS.json`
- `BLIND_SEMANTIC_BUNDLE_RECORD.json`

The bundle is complete only when all 72 partitions have valid label records,
every fixed cluster has one name, all 12 topics have one anchor, and no request
is in flight.

The completed output directory is founder-signed and pushed before either E1
private metadata key is used to join original model/gap metadata to semantic
outputs.
