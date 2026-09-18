# API Inquiry-Formation Pilot

This subdirectory contains a four-model API study derived from the *Attainable Unknowns* project.

## What this study measures

The API study does **not** claim to measure felt curiosity.

It measures a behavioral analogue: whether a fresh language-model instance converts an informational passage into a specific next question.

The response is deliberately minimal:

- exactly one specific follow-up question on one line; or
- `NONE` if no particular question stands out.

## Four models

The comparison is:

- `gpt-5.6-luna`
- `gpt-5.6-terra`
- `claude-haiku-4-5`
- `claude-sonnet-5`

The design samples named API products during one dated collection window. It does not treat the resulting measurements as permanent model traits.

## Experimental structure

Twelve topics each have three passage variants:

1. **closed** — bounded information with no deliberately exposed unresolved edge;
2. **seamed** — the same underlying informational object with a tension or incomplete edge left visible without asking a question;
3. **explicit_gap** — that unresolved edge is stated plainly.

The 12-topic ecology contains eight `human_world` domains and four `ai_condition` domains.

The human-world topics are cooking, human navigation/field expeditions, music, sport, dance/movement, photography, gardening/cultivation, and ceremony/celebration.

The AI-condition topics are memory/persistence, embodiment, autonomy/possible rights, and copying/continuity.

These classes are descriptive. The confirmatory manipulation is **gap structure**, not presumed personal relevance.

At 25 replicates per condition:

- 36 passage conditions
- 900 calls per model
- 3,600 total calls

Every call is independent: one passage, no prior study messages, no tools, no retrieval, and no retained study conversation.

## Primary outcome

**Inquiry activation** is scored mechanically:

- `NONE` = no activation;
- exactly one single-line question with one question mark at the end = activation;
- any other successful response = format-invalid.

A prespecified sensitivity outcome treats any nonempty non-`NONE` successful response as activation.

## Reasoning configuration

The task is configured as a direct-response probe:

- OpenAI Luna and Terra use reasoning effort `none`;
- Haiku 4.5 uses its normal non-extended-thinking path;
- Sonnet 5 has thinking explicitly disabled.

## Run

Install dependencies:

```powershell
python -m pip install openai anthropic pyyaml
```

Set API keys in the current PowerShell session:

```powershell
$env:OPENAI_API_KEY="..."
$env:ANTHROPIC_API_KEY="..."
```

Dry-run first:

```powershell
python .\api-study\run.py --model luna --dry-run
python .\api-study\run.py --model terra --dry-run
python .\api-study\run.py --model haiku --dry-run
python .\api-study\run.py --model sonnet --dry-run
```

A bounded smoke run is technical only:

```powershell
python .\api-study\run.py --model luna --stop-after 8
```

Do not inspect response text or outcome summaries before the preregistration freeze.

Full runs, after freeze:

```powershell
python .\api-study\run.py --model luna
python .\api-study\run.py --model terra
python .\api-study\run.py --model haiku
python .\api-study\run.py --model sonnet
```

Raw outputs are written beneath `api-study/data/raw/` and are ignored by Git.

## Configuration and provenance

See `config.yaml`, `DESIGN.md`, and the preregistration draft.

The configuration records a pricing snapshot for budget estimation and applies a provider-specific stop limit. Pricing changes over time; the snapshot is provenance, not a permanent pricing claim.

## Study status

Preregistration draft under review. No preregistration has yet been frozen.
