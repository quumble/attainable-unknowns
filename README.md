# Attainable Unknowns

A Bo Chesterton research project on curiosity, specificity, attainability, and information-seeking.

> **Originating formulation:** "curiosity as the sudden awareness of specific, attainable knowledge"

## Current direction

The project began with a human-participant browser pilot exploring breadth, depth, and direction of information seeking. A first internal test exposed a construct-validity problem: supplying participants with ready-made questions may measure preference among offered information opportunities more cleanly than it measures the formation of curiosity itself.

The human pilot is preserved in this repository as provenance and may be revisited.

The active direction is now an **API inquiry-formation study** asking a narrower question:

> When a fresh language-model instance reads an informational passage, does it formulate a specific next question, or does no particular question stand out?

This is a measurable behavioral analogue of one component of the original curiosity proposal. It is **not** treated as evidence of felt curiosity, subjective interest, or phenomenal experience.

## API pilot

The study compares:

- GPT-5.6 Luna
- GPT-5.6 Terra
- Claude Haiku 4.5
- Claude Sonnet 5

Twelve topic families each receive three passage structures:

- **closed**
- **seamed**
- **explicit gap**

Eight topics are ordinary human-world domains: cooking, human navigation/field expeditions, music, sport, dance/movement, photography, gardening/cultivation, and ceremony/celebration.

Four concern possible conditions of AI systems: memory/persistence, embodiment, autonomy/possible rights, and copying/continuity.

These groupings are descriptive. The confirmatory passage manipulation is gap structure.

At 25 replicates per condition, the full pilot is **3,600 independent API requests**.

See [api-study/README.md](api-study/README.md), [api-study/DESIGN.md](api-study/DESIGN.md), and the current preregistration draft under [prereg/](prereg/).

## Earlier human pilot

The browser pilot remains under [interface/](interface/), with its stimulus bank under [stimuli/](stimuli/).

It explored:

- **breadth** — which intellectual territories attract voluntary interest;
- **depth** — whether an answer leads to further inquiry;
- **direction** — which kind of clarifying unknown is pursued.

That design is exploratory and not intended for paid deployment without further revision.

## Repository map

- [api-study/](api-study/) — active four-model inquiry-formation pilot.
- [DESIGN.md](DESIGN.md) — earlier human-pilot conceptual design.
- [ETHICS.md](ETHICS.md) — human-participant baseline if that branch resumes.
- [PROVENANCE.md](PROVENANCE.md) — project origin and provenance distinctions.
- [stimuli/](stimuli/) — earlier human-pilot stimulus materials.
- [interface/](interface/) — earlier browser pilot.
- [prereg/](prereg/) — preregistration drafts and future frozen materials.
- [data/](data/) — human-pilot schema and data conventions.

## Governance note

This repository is a research workspace within Bo Chesterton. It is not a constitutional instrument, appointment, mandate, or delegation. Its present private state is working status, not public release.
