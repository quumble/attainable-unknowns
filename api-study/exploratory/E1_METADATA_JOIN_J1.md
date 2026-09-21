# E1 Metadata Join J1

**Study:** Attainable Unknowns API Pilot 0.1  
**Parent protocol:** E1 with Amendment E1A  
**Blind semantic bundle:** `AU-E1-BLIND-v1`  
**Source checkpoint:** `bdc20e6926d029a59c58b2e9189bb6ff581c88a8`  
**Status:** Post-freeze mechanical metadata join

## Purpose

J1 performs the first authorized join between the frozen E1 semantic outputs and
the original response metadata. It maps every fixed Stage 2 target and cluster
back to its Stage 1 card and then to every represented eligible observation.

J1 performs no semantic recoding. It does not change canonical targets, cluster
membership, cluster names, focal anchors, or original response metadata. It does
not select among the two Stage 1 representations or three Stage 2 partition
replicates.

## Inputs

The implementation verifies and reads:

- all four accepted raw response files and their generation records;
- the frozen Stage 1 master packet and private observation/card key;
- both frozen Stage 1 canonical-target representations;
- the frozen Stage 2 packet index, all 24 topic packets, and the private target
  key;
- all 72 frozen P1D3 partitions;
- all 72 frozen cluster-label records;
- the 12 frozen passage-only focal anchors; and
- the blind semantic bundle record.

The blind bundle's recorded `api-study/passages.json` SHA-256 reflects the CRLF
working-tree bytes used during F1. GitHub's source ZIP contains the same text
with LF newlines. J1 accepts this only when newline normalization alone
reproduces the recorded hash and independently verifies every focal anchor
against the parsed passage bank.

## Outputs

`api-study/exploratory/e1/metadata_join/AU-E1-J1-v1/`

- `JOINED_CLUSTERS.jsonl` — one row per frozen cluster instance, with its true
  representation and topic restored;
- `JOINED_CARDS.jsonl` — one row per representation × card × partition
  assignment; and
- `JOINED_OBSERVATIONS.jsonl` — one row per eligible observation ×
  representation × partition assignment.
- `E1_METADATA_JOIN_RECORD.json` — input/output hashes, counts, provenance, and
  completed validation checks.

Cluster identifiers remain local to a representation × topic × partition. J1
therefore emits a globally unique `cluster_uid` built from the frozen task ID and
local cluster ID.

## Fixed coverage expectations

- 2 Stage 1 representations;
- 3 Stage 2 partitions per representation/topic packet;
- 12 topics;
- 72 partition records;
- 2,026 frozen cluster instances;
- 1,984 unique visible cards;
- 2,919 eligible emitted-question observations;
- 11,904 joined card assignments; and
- 17,514 joined observation assignments.

The join aborts rather than writing partial outputs if any hash, identity,
coverage, multiplicity, partition, label, passage, anchor, or raw-record check
fails. Output publication is directory-atomic.

## Scope boundary

J1 is a data join, not the E1 descriptive analysis. It does not compute target
concentration, entropy, effective target count, Simpson concentration,
cross-model Jensen-Shannon divergence, partition stability, or focal-gap
alignment. Those outputs remain downstream exploratory analyses.

