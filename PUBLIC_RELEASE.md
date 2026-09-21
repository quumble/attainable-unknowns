# Public-release and reproducibility note

This repository preserves the working record of **Attainable Unknowns API Pilot 0.1**, including preregistration, signed checkpoints, raw accepted API collections, blinded semantic packets, unblinding maps, analysis code, and frozen analysis outputs.

## What `private` means in this repository

Several historical workflow directories contain files named `PRIVATE_KEY`, `UNBLINDING_KEY`, or similar. These are **not authentication secrets or cryptographic private keys**. They are study-internal mapping tables that were withheld from coders or partitioners while blinded work was in progress.

The relevant blind checkpoints were frozen before those mappings were used downstream. After completion, the mappings are intentionally retained with the public research record so that readers can reconstruct the provenance of cards, targets, clusters, conditions, and model identities.

The word `private` in those paths therefore describes their **role during blinded execution**, not their intended permanent publication status.

## Raw API envelopes

The repository preserves exact provider response envelopes for the accepted API runs and for several later model-assisted coding stages. These records may include:

- provider-generated response or message identifiers;
- token-usage and service metadata;
- timestamps and latency information;
- model/provider identifiers; and
- historical local filesystem paths in run manifests.

No API credential is intentionally stored in the repository. API access was supplied through environment variables. The full envelopes are retained because exact-byte preservation and hashes are part of the project's provenance model.

Provider-generated identifiers should not be interpreted as participant identifiers, user account credentials, or evidence of a persistent conversational identity.

## Human-participant data

No paid human-participant data were collected for this version of the project. The earlier browser pilot remains as design provenance only. The repository policy continues to exclude live Prolific identifiers and raw participant exports from Git.

## Evidentiary status

Repository visibility does not change the evidentiary status of any analysis. In particular:

- the API Pilot 0.1 primary analysis is preregistered/confirmatory as documented in `prereg/`;
- the B1/B1A specificity stage has its own frozen protocol and amendment record; and
- E1/E1B semantic-target analyses are post hoc and exploratory.

Later public explanation should not be projected backward onto earlier uncertainty. Signed commits, freeze records, amendments, and preserved intermediate artifacts remain the provenance record.

## Reproducibility and historical artifacts

The repository intentionally contains superseded drafts, correction records, blind packets, model-attempt logs, and intermediate artifacts when they materially document how the study was executed. Their presence does not make every file operative. Where records conflict, the signed protocol/change history and final frozen outputs identify the applicable version.

Before the first public release, all reachable Git objects should be scanned for credentials using `tools/public_release_audit.py`, and non-authoritative development branches should be removed or deliberately documented.

## Citation and reuse

Citation metadata are provided in `CITATION.cff`. Licensing scope is described in `LICENSE.md`.
