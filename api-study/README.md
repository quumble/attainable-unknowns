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
- 3,600 accepted API records total

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

## Confirmatory analysis

The frozen confirmatory pipeline is `analyze_confirmatory.py`. The founder-signed, outcome-blind Amendment A1 adds `analyze_confirmatory_a1.py` to handle separation and preserve results when model × gap cells saturate.

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

The preregistered confirmatory collection and A1 analysis are complete and preserved under `results/` and `prereg/`.

## Secondary specificity stage

Specificity Protocol B1 fixes a deterministic 180-observation stratified sample, exact-visible duplicate collapse, three cold model coders, and blinded founder adjudication of disagreements.

The B1/B1A specificity stage is complete. Its records remain preserved under the specificity and preregistration materials.

## Exploratory semantic-target analysis

Exploratory Semantic Target Protocol E1 examines the 2,919 eligible emitted-question observations conditional on question emission.

The semantic workflow preserves:

- 1,984 exact-visible unique question cards;
- two independent Stage 1 canonical-target representations;
- three independent Stage 2 partitions per representation/topic;
- 72 frozen partition records;
- 2,026 frozen cluster instances;
- a blinded focal-alignment procedure; and
- a mechanical metadata join performed only after the blind semantic bundle was frozen.

The completed formal E1/E1B descriptive analysis is preserved under:

`exploratory/e1/analysis/AU-E1-ANALYSIS-v1/`

Across the cross-topic summaries, both Stage 1 representations show increasing semantic concentration from closed to seamed to explicit-gap passages: top-target share rises while Shannon entropy and effective target count fall. The same broad pattern remains in the unique-card sensitivity, so it is not explained solely by exact repeated question strings.

Focal-alignment analysis shows that much of the explicit-gap concentration reflects direct convergence on the deliberately exposed unresolved issue. E1B nevertheless finds residual concentration after focal-target clusters are excluded. The stronger focal-plus-adjacent exclusion is less stable because relatively few observations remain, especially under one semantic representation.

Average pairwise Jensen-Shannon divergence between the four generator-model target distributions also declines as gap salience increases, indicating greater semantic similarity among emitted-question target distributions in the aggregate.

Partition reproducibility is heterogeneous and in several topics low. E1 therefore preserves all semantic representations and partitions rather than selecting a preferred clustering or constructing a consensus taxonomy.

All E1/E1B findings are **post hoc and exploratory**. They describe distributions of generated questions and do not establish felt curiosity, conscious gap representation, or latent internal choice among alternatives.

See the operative E1 materials under `exploratory/`, including the metadata join, focal-alignment, analysis execution protocol, and frozen analysis record.

## Current stage

Pilot 0.1 is analytically complete through the frozen E1/E1B descriptive analysis.

The next stage is interpretation, robustness review, write-up planning, and deciding which exploratory observations merit prospective testing in a later study.
