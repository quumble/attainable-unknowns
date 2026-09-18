# API Inquiry-Formation Pilot

This subdirectory contains a four-model API study derived from the *Attainable Unknowns* project.

## What this study measures

The API study does **not** claim to measure felt curiosity.

It measures a behavioral analogue: whether a fresh language-model instance converts an informational passage into a specific next question.

The core response is deliberately minimal:

- one specific follow-up question; or
- `NONE` if no particular question stands out.

## Four models

The initial four-way comparison is:

- `gpt-5.6-luna`
- `gpt-5.6-terra`
- `claude-haiku-4-5`
- `claude-sonnet-5`

The design treats Luna/Haiku as lower-cost tiers and Terra/Sonnet as more capable tiers within their respective provider families. This is a practical sampling frame, not a claim that the tiers are psychometrically equivalent.

## Experimental structure

Eight topics each have three passage variants:

1. **closed** — compact explanation with no deliberately exposed unresolved edge;
2. **seamed** — substantially the same informational object, but with a tension or incompleteness left visible without asking a question;
3. **explicit_gap** — the unresolved edge is stated plainly.

Four topics concern ordinary human-world subject matter. Four are **model-adjacent**: memory persistence, embodiment, autonomy/rights, and continuity/copying/shutdown.

Model-adjacent passages are written in the third person. They do not tell the model that the topic concerns "systems like you."

At 25 replicates per condition:

- 24 passage conditions
- 600 calls per model
- 2,400 total calls

Every call is independent: one passage, no prior messages, no tools, no retained study conversation.

## Primary outcome

**Inquiry activation:** whether the response is a question rather than `NONE`.

Candidate secondary outcomes include question type, specificity, semantic diversity, self-reference, and cross-model convergence. Those require a separate coding or analysis plan.

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

Dry-run a model first:

```powershell
python .\api-study\run.py --model luna --dry-run
```

Then run:

```powershell
python .\api-study\run.py --model luna
python .\api-study\run.py --model terra
python .\api-study\run.py --model haiku
python .\api-study\run.py --model sonnet
```

A debug run can be bounded without pretending to be confirmatory:

```powershell
python .\api-study\run.py --model luna --stop-after 8
```

Raw outputs are written beneath `api-study/data/raw/` and are ignored by Git.

## Configuration

See `config.yaml`.

The configuration records a pricing snapshot for budget estimation and applies a provider-specific stop limit. Pricing changes over time; the snapshot is provenance, not a permanent pricing claim.

OpenAI reasoning effort is set to `none` for Luna and Terra so the task is a direct-response probe rather than an extended-reasoning study. Anthropic extended thinking is not enabled.

## Study status

Exploratory pilot. Not preregistered.
