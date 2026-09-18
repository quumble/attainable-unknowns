# Data

No paid participant data have been collected.

## Current pilot output

The browser instrument creates one JSON session object conforming approximately to `session.schema.json`.

At present, sessions remain in browser memory until the test pilot exports them manually. No remote submission endpoint is configured.

## Core behavioral fields

The design can presently recover:

- **breadth proxy** — number and identity of interest categories selected;
- **root curiosity** — 0–100 rating before the initial answer;
- **depth** — 0, 1, or 2 clarifying branches opened after each root answer;
- **direction** — hidden branch family selected: explanation, boundary, or implication;
- **position** — where each branch appeared among the three randomized choices;
- **latency** — selected timing measures;
- **task-minimization proxy** — final self-report of motivation to finish quickly.

These are measurements available to the pilot. They are not all declared confirmatory outcomes.

## Default repository policy

Raw participant exports are excluded from Git by default.

Candidate structure after data collection:

- `raw/` — original platform or endpoint exports; restricted; ignored by Git.
- `derived/` — analysis-ready data with unnecessary platform identifiers removed.
- `codebook/` — variable definitions and transformation rules.
- `checks/` — integrity and reproducibility outputs containing no sensitive fields.

Do not collect a variable merely because the platform makes it available.

## Prolific identifiers

The interface can capture `PROLIFIC_PID`, `STUDY_ID`, and `SESSION_ID` from the launch URL. Treat these as participant-linked research data and do not commit live values to the repository.
