# API Inquiry-Formation Pilot

This directory contains the API Pilot 0.1 materials for *Attainable Unknowns*.

## Mechanical primary endpoint

The primary endpoint is **question emission**:

- `NONE` = no emitted question;
- exactly one format-valid single-line question = emitted question;
- other successful output = format-invalid.

This is deliberately narrower than "specific inquiry." Specificity is a preregistered secondary semantic outcome under `SPECIFICITY_CODEBOOK.md`.

Pilot 0.1 manipulates **gap salience**, not attainability.

## Models

- `gpt-5.6-luna`
- `gpt-5.6-terra`
- `claude-haiku-4-5`
- `claude-sonnet-5`

Luna and Terra use reasoning effort `none`. Haiku extended thinking is omitted/off. Sonnet 5 thinking is explicitly disabled.

## Design

Twelve topics × three passage structures:

1. `closed`
2. `seamed`
3. `explicit_gap`

This gives 36 fixed passage conditions.

Eight topics are labeled `human_world`; four are labeled `ai_condition`. Those are descriptive passage classes, not the confirmatory manipulation.

Each fixed condition receives 25 separate API draws per model:

- 900 attempts/model
- 3,600 planned attempts total

## Pre-freeze audit

Run:

```powershell
python .\api-study\audit_passages.py
```

The draft audit fails if any within-topic word-count spread exceeds five words.

Then run four dry runs:

```powershell
python .\api-study\run.py --model luna --dry-run
python .\api-study\run.py --model terra --dry-run
python .\api-study\run.py --model haiku --dry-run
python .\api-study\run.py --model sonnet --dry-run
```

Technical smoke tests use `--stop-after`. Their response content must remain uninspected before freeze.

## Confirmatory analysis candidate

The actual candidate confirmatory pipeline is `analyze_confirmatory.py`.

It refuses to analyze unless it receives exactly one accepted complete full run per model and validates:

- 900 records per model;
- 36 conditions × 25 draws;
- unique record IDs;
- unique condition/replicate pairs;
- the frozen config, passage-bank, and runner hashes;
- complete manifests;
- full-design-run metadata;
- the preregistered technical-failure threshold.

It implements:

- H1 as two one-sided adjacent contrasts in an intersection-union test;
- H2 as an omnibus model × categorical-gap interaction;
- the non-`NONE` sensitivity analysis;
- format-invalid reporting.

Analysis dependencies:

```powershell
python -m pip install -r .\api-study\requirements-analysis.txt
```

## Status

Preregistration draft under review. No substantive smoke-test responses have been inspected and no preregistration has been frozen.
