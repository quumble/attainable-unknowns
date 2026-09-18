# Data

No participant data have been collected.

## Default policy

Raw participant exports are excluded from Git by default.

The project should preserve enough information for reproducibility while minimizing unnecessary retention and propagation of participant-linked identifiers.

Candidate structure after data collection:

- `raw/` — original platform exports; restricted; ignored by Git.
- `derived/` — analysis-ready data with unnecessary platform identifiers removed.
- `codebook/` — variable definitions and transformation rules.
- `checks/` — reproducibility and integrity outputs that contain no sensitive fields.

## Candidate analytic fields

Depending on the final design:

- internal participant index;
- experimental condition;
- item ID;
- topic/category ID;
- initial interest selection;
- curiosity rating;
- reveal decision;
- reveal order;
- randomization order;
- latency, if retained;
- completion/exclusion flags.

Do not collect a variable merely because the platform makes it available.

## Provenance

Any transformation from raw to derived data should be scripted or documented so that the analysis-ready dataset can be reconstructed without silently altering observations.
