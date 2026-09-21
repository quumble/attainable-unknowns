# Attainable Unknowns

A Bo Chesterton research project on curiosity, specificity, attainability, and information-seeking.

> **Originating formulation:** "curiosity as the sudden awareness of specific, attainable knowledge"

## Current direction

The project began with a human-participant browser pilot. A first internal test raised a construct-validity problem: supplying ready-made questions may measure preference among offered information opportunities more directly than spontaneous inquiry formation.

The human pilot remains preserved as provenance.

The active research line is a completed four-model API pilot asking a narrower question:

> When a separate stateless API draw reads an informational passage, does the response emit a follow-up question, or does it produce `NONE`?

The mechanical primary endpoint is **question emission**. It is not treated as proof of felt curiosity or, by syntax alone, of a specific represented unknown.

Pilot 0.1 manipulates **gap salience**, not attainability.

## API Pilot 0.1

Models:

- GPT-5.6 Luna
- GPT-5.6 Terra
- Claude Haiku 4.5
- Claude Sonnet 5

Twelve topic families each receive:

- closed
- seamed
- explicit-gap

Eight are ordinary human-world domains and four concern possible conditions of AI systems. Those classes are descriptive; gap structure is the confirmatory manipulation.

At 25 separate API draws per fixed condition, the accepted collection contains:

- 36 passage conditions
- 900 attempts per model
- 3,600 accepted API records
- 2,919 eligible emitted-question observations

## Analysis status

The preregistered collection and primary analysis are complete.

The subsequent sampled semantic-specificity analysis under Protocol B1/B1A is also complete.

Exploratory Semantic Target Protocol E1 and Amendment E1B have now been executed through the frozen E1 descriptive analysis. E1 maps emitted questions into independently generated semantic-target representations and partitions while preserving uncertainty across those operationalizations.

Across the cross-topic E1 summaries, both semantic representations show greater semantic concentration as gap salience increases from closed to seamed to explicit-gap passages: top-target share rises while target entropy and effective target count fall.

Focal-alignment analysis indicates that much of this concentration reflects questions converging on the deliberately exposed unresolved issue. However, aggregate concentration differences remain after focal-target questions are excluded, indicating that direct focal capture does not fully account for the observed redistribution. A stronger analysis excluding both focal and adjacent targets is more fragile because relatively few explicit-gap observations remain.

Pairwise model target distributions also become more similar on average as gap salience increases.

These findings are **post hoc and exploratory**. They do not establish felt curiosity, conscious gap representation, or latent internal choice among question alternatives.

Semantic partition reproducibility is heterogeneous and in some topics low. The repository therefore preserves both Stage 1 representations and all three Stage 2 partitions rather than selecting or constructing a single preferred taxonomy.

The current stage is interpretation, robustness review, and deciding which observations merit prospective testing in a subsequent study.

See [api-study/README.md](api-study/README.md), [api-study/DESIGN.md](api-study/DESIGN.md), the frozen and post-freeze records under [prereg/](prereg/), and the E1 materials under [api-study/exploratory/](api-study/exploratory/).

## Public research record

This repository is intended to serve as the public reproducibility record for API Pilot 0.1.

It preserves signed checkpoints, raw accepted API records, blinded coding/partition packets, study-internal unblinding maps, intermediate provenance artifacts, analysis code, and frozen outputs. Files named `PRIVATE_KEY`, `UNBLINDING_KEY`, or similar are **blinding maps rather than authentication secrets**; they were kept from coders during the relevant blind stage and are retained after completion so that the analysis can be reconstructed.

Exact raw API envelopes are also preserved. They may contain provider-generated response/message identifiers, technical service metadata, and historical local filesystem paths, but API credentials were supplied through environment variables rather than intentionally committed to the repository.

No paid human-participant data were collected for this version of the project.

See [PUBLIC_RELEASE.md](PUBLIC_RELEASE.md) for the release/reproducibility note, [CITATION.cff](CITATION.cff) for citation metadata, and [LICENSE.md](LICENSE.md) for licensing scope.

## Earlier human pilot

The browser pilot remains under [interface/](interface/) with its earlier stimulus bank under [stimuli/](stimuli/).

## Governance note

This repository is a research workspace within Bo Chesterton. It is not a constitutional instrument, appointment, mandate, or delegation. Repository visibility provides access to research materials and provenance; it does not change the evidentiary status of confirmatory, secondary, or exploratory analyses.
