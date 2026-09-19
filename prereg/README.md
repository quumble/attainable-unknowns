# Preregistration and protocol record

API Pilot 0.1 was frozen in founder-signed commit `d24269a93fa25f61306145a68bd0f4ea896b3e01` before full collection.

Post-freeze Amendment A1 was adopted in founder-signed commit `32155549d4b347b3d1ae3b9e5f9dc3a2d2a63284` before substantive outcome inspection. The complete collection was anchored in founder-signed commit `9a2b2ec37de6f62421b9c648d0148adb3c6135c5` and the final uploaded files were preserved in verified commit `be42d8572564e290272d6cf8820d09603bf46a34`.

Specificity Protocol B1 is a post-collection, post-primary-analysis, pre-packet procedure. Its own text states its activation boundary; the founder-signed commit containing B1 and `API_PILOT_0.1_PREPACKET_FREEZE_RECORD.json` is the adoption evidence.

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


## Original API Pilot 0.1 freeze workflow

The original final candidate was `API_PILOT_0.1_PREREGISTRATION.md`.

Immediately before the founder-signed pre-collection commit, run:

```powershell
.\prereg\build_freeze_record.ps1
```

This produces `API_PILOT_0.1_FREEZE_RECORD.json` from tracked study-file hashes and technical metadata/hashes for locally retained bounded smoke tests. The generator hashes raw JSONL files without parsing response content.

## Specificity B1 freeze workflow

From the repository root:

```powershell
python .\api-study\run_primary_a1_record.py
python .\prereg\build_prepacket_freeze.py
git add -- README.md api-study/README.md prereg/README.md `
  prereg/API_PILOT_0.1_SPECIFICITY_PROTOCOL_B1.md `
  prereg/API_PILOT_0.1_PREPACKET_FREEZE_RECORD.json `
  prereg/build_prepacket_freeze.py `
  api-study/run_primary_a1_record.py api-study/results api-study/specificity
git diff --cached --check
git status --short
git commit -S -m "Freeze specificity protocol before blinded packet generation"
git push origin main
git verify-commit HEAD
```

Only after signature verification succeeds may the blinded packet be generated.
