# Attainable Unknowns

A Bo Chesterton research project on curiosity, specificity, attainability, and information-seeking.

> **Originating formulation:** "curiosity as the sudden awareness of specific, attainable knowledge"

## Working hypothesis

Curiosity is associated with the perception of a **specific unknown** whose answer appears **attainable**.

The current pilot extends that idea by asking what happens after the first unknown is resolved: does the answer satisfy inquiry, or does it expose another attainable unknown worth pursuing?

## Status

**Active pilot-development stage. Private repository.**

No paid participants have been recruited and no confirmatory design has been preregistered.

A browser-runnable test-pilot instrument and a 12-item draft stimulus bank now exist. The instrument currently exports session JSON locally; durable remote data collection is not yet configured.

## Current behavioral model

The project is exploring curiosity along at least three separable dimensions:

- **breadth** — which and how many intellectual territories attract voluntary interest;
- **depth** — whether a resolved question leads to zero, one, or two further inquiries;
- **direction** — which kind of clarifying unknown is pursued when several are simultaneously available.

Pilot 0.1 classifies follow-up branches invisibly as **explanation**, **boundary**, or **implication** while presenting participants only with natural-language questions.

## Pilot 0.1

Each session currently:

1. presents either a broad or specific interest map;
2. samples three concrete and three abstract root questions;
3. records a 0–100 desire-to-know rating;
4. reveals a real answer;
5. presents three clarifying follow-up questions in randomized order;
6. permits the participant to stop, open one, or open two of three;
7. records a final self-report of how strongly the participant was trying to finish quickly.

The initial answer is designed as a **junction**, not merely a fun-fact reward.

## Repository map

- [DESIGN.md](DESIGN.md) — current conceptual and pilot design.
- [ETHICS.md](ETHICS.md) — participant-protection baseline and data-minimization principles.
- [PROVENANCE.md](PROVENANCE.md) — origin of the project and distinction between observation and later design.
- [stimuli/items.json](stimuli/items.json) — machine-readable 12-item stimulus bank.
- [stimuli/category-maps.json](stimuli/category-maps.json) — broad and specific interest maps.
- [stimuli/permutations.json](stimuli/permutations.json) — all six branch-order permutations and balancing notes.
- [interface/](interface/) — runnable browser pilot.
- [prereg/](prereg/) — future frozen preregistration materials.
- [data/](data/) — session schema and future data conventions.

## Run the test pilot

From the repository root in PowerShell:

```powershell
./interface/serve.ps1
```

Then open `http://localhost:8000/interface/`.

For manual comparison, add `?map=broad` or `?map=specific`.

## Governance note

This repository is a research workspace within Bo Chesterton. It is not a constitutional instrument, appointment, mandate, or delegation. Its present private state is working status, not public release.
