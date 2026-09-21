# Raw API records

This directory contains exact records from API Pilot 0.1 collection.

## Why a normally ignored directory is tracked

`api-study/data/raw/` is ignored by default so that new ad hoc or accidental API output is not silently committed. The historical files already under version control were deliberately force-added as frozen study artifacts. Git continues to track those files even though the directory remains ignored for future unreviewed output.

## Contents

The directory contains two broad classes of run files:

1. **bounded technical/smoke runs**, collected before the confirmatory full runs and excluded from the accepted confirmatory dataset; and
2. **four accepted complete 900-request runs**, one per model, with manifests and SHA-256 sidecars.

The accepted full runs are identified by their manifests and by the preregistration/freeze records elsewhere in the repository. Do not infer accepted-dataset status merely from the presence of a raw JSONL file.

## Provider envelopes

The JSONL records preserve the provider response object returned at collection time in addition to the parsed study fields. Provider envelopes may contain response/message IDs, token accounting, service metadata, timestamps, and related technical fields. They do not contain intentionally stored API credentials.

Some manifests also preserve the absolute local path used when the run was collected. Those paths are operational provenance and are not required to reproduce the analysis.

## Human data

These files contain model/API records, not paid human-participant records. Human-participant exports remain excluded from Git by project policy.
