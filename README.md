# Attainable Unknowns

A Bo Chesterton research project on curiosity, specificity, attainability, and information-seeking.

> **Originating formulation:** "curiosity as the sudden awareness of specific, attainable knowledge"

## Current direction

The project began with a human-participant browser pilot. A first internal test raised a construct-validity problem: supplying ready-made questions may measure preference among offered information opportunities more directly than spontaneous inquiry formation.

The human pilot remains preserved as provenance.

The active direction is a completed four-model API pilot asking a narrower question:

> When a separate stateless API draw reads an informational passage, does the response emit a follow-up question, or does it produce `NONE`?

The mechanical primary endpoint is **question emission**. It is not treated as proof of felt curiosity or even, by syntax alone, of a specific represented unknown. Specificity has a separate preregistered semantic codebook.

Pilot 0.1 manipulates **gap salience**, not attainability.

## Current API design

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
- 3,600 successful attempts total

The preregistered primary analysis is complete. The next stage is the sampled, blinded semantic-specificity coding governed by Specificity Protocol B1.

See [api-study/README.md](api-study/README.md), [api-study/DESIGN.md](api-study/DESIGN.md), and the frozen and post-freeze records under [prereg/](prereg/).

## Earlier human pilot

The browser pilot remains under [interface/](interface/) with its earlier stimulus bank under [stimuli/](stimuli/).

## Governance note

This repository is a research workspace within Bo Chesterton. It is not a constitutional instrument, appointment, mandate, or delegation. Its private state is working status, not public release.
