# Preregistration

No preregistration has been frozen.

This directory is reserved for dated, immutable-or-clearly-versioned preregistration materials once the design has survived piloting.

A confirmatory preregistration should specify at minimum:

- research questions and hypotheses;
- experimental conditions;
- stimulus set and exclusions;
- recruitment source and eligibility;
- sample-size rationale;
- stopping rule;
- primary and secondary outcomes;
- exclusion criteria;
- randomization procedure;
- statistical model;
- treatment of repeated participant/item observations;
- missing-data rules;
- confirmatory contrasts;
- any planned multiplicity adjustment;
- separation of confirmatory from exploratory analyses.

Pilot-derived choices should be identified as such rather than rewritten as if they preceded the pilot.


## API Pilot 0.1 freeze workflow

The current final candidate is `API_PILOT_0.1_PREREGISTRATION.md`.

Immediately before the founder-signed pre-collection commit, run:

```powershell
.\prereg\build_freeze_record.ps1
```

This produces `API_PILOT_0.1_FREEZE_RECORD.json` from tracked study-file hashes and technical metadata/hashes for locally retained bounded smoke tests. The generator hashes raw JSONL files without parsing response content.
