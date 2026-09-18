# Pilot Interface

This directory contains the first browser-runnable *Attainable Unknowns* pilot instrument.

## Run locally

From PowerShell:

```powershell
./interface/serve.ps1
```

Then open:

```text
http://localhost:8000/interface/
```

Do not open `index.html` directly from the filesystem; the browser must be able to load the JSON stimulus files.

## Useful query parameters

- `?map=broad` — force the broad interest map.
- `?map=specific` — force the specific interest map.
- `PROLIFIC_PID`, `STUDY_ID`, `SESSION_ID` — captured automatically when Prolific appends them.

Without a `map` override, the instrument randomly assigns broad vs. specific interest maps.

## Current participant flow

1. Interest-map selection.
2. Six root questions: three concrete and three abstract, sampled from the bank.
3. 0–100 root-curiosity rating.
4. Initial answer reveal.
5. Three clarifying branches in randomized order.
6. Participant may stop, open one branch, or open two of three.
7. Final speed-motivation calibration.
8. Local JSON export.

The three hidden branch families are:

- **explanation** — underlying mechanism, structure, or reason;
- **boundary** — limit, exception, counterexample, or contrast;
- **implication** — consequence, use, or broader significance.

Participants see only the natural-language questions, not these labels.

## Data capture

The session trace includes:

- Prolific URL parameters when present;
- interest-map condition;
- selected interests;
- sampled item order;
- root-curiosity ratings;
- root decision latency;
- branch presentation permutation;
- branch position and hidden type;
- depth per item (0, 1, or 2);
- branch-selection latency;
- final self-reported speed motivation;
- event-level timestamps.

See `../data/session.schema.json`.

## Storage status

`config.json` currently has `submission_endpoint: null`.

Therefore this build does **not** transmit participant data. The completion screen exports a JSON file instead. Before a remote Prolific launch, configure and test a durable data endpoint and a Prolific completion URL.

The interface already captures Prolific's standard `PROLIFIC_PID`, `STUDY_ID`, and `SESSION_ID` URL parameters when present.

## Files

- `index.html` — shell.
- `styles.css` — visual layer.
- `app.js` — study logic and event capture.
- `config.json` — pilot settings and future endpoint/completion configuration.
- `serve.ps1` — local test server helper.
