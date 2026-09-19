# API Pilot 0.1 — Exploratory Semantic Target Protocol E1

**Study:** Attainable Unknowns API Pilot 0.1  
**Protocol ID:** E1  
**Status:** Draft exploratory analysis protocol; post hoc and post-inspection  
**Prepared:** 2026-09-19  
**Base repository commit:** `9ad834f3c1e4aa43810fcc9a331c0f071cd26911`  
**Stage:** Post-collection, post-confirmatory A1 analysis, post-B1/B1A specificity analysis and unblinding  
**Scope:** Exploratory semantic analysis only

## 1. Purpose and evidentiary boundary

The frozen Pilot 0.1 design identified semantic diversity, repeated-question
concentration, cross-model semantic convergence, question family, and
topic-specific patterns as exploratory analyses.

E1 formalizes a semantic-target analysis of the complete eligible emitted-question
corpus.

The motivating question is:

> Conditional on emitting a question, what informational target does the question
> pursue, and how concentrated or dispersed are those targets under closed,
> seamed, and explicit-gap passages?

E1 does not amend or reinterpret the preregistered primary endpoint, H1, H2,
Amendment A1, Specificity Protocol B1/B1A, or their results.

E1 is not a preregistration and cannot become confirmatory through adoption,
signing, or later statistical significance. Its procedures are fixed prospectively
only with respect to semantic target extraction, partitioning, and the formal E1
outputs that have not yet been produced.

Any hypothesis or measurement emerging from E1 may be preregistered in a later
study such as Pilot 0.2.

## 2. Prior knowledge and exploratory inspection disclosure

E1 is being prepared after substantive outcome inspection.

Before E1 was written:

- the founder and preparing assistant knew the primary A1 result, including the
  strong closed < seamed < explicit-gap question-emission pattern and model
  differences;
- the B1/B1A specificity result had been completed and unblinded;
- all 169 unique B1 coding cards were unanimously coded `1` by the three initial
  coders, mapping to 180/180 sampled observations coded specific;
- the preparing assistant inspected question content from the B1 packet and
  multiple full-corpus examples;
- the founder was shown examples illustrating both divergence and apparent
  semantic convergence;
- preliminary, ad hoc full-corpus calculations were performed for question
  length, approximate Flesch-Kincaid readability, lexical overlap with passage
  text, overlap with the final passage sentence, normalized question
  uniqueness, and within-condition lexical similarity;
- those preliminary calculations suggested, among other things, greater lexical
  convergence and final-sentence alignment in the explicit-gap condition.

These observations motivated E1.

No complete 2,919-observation question-to-target mapping, complete canonical
target set, or topic-level semantic partition has yet been produced.

Formal E1 results must not be described as outcome-blind discoveries merely
because the remaining semantic coding is blinded to metadata.

## 3. Accepted runs and corpus

E1 uses exactly the four accepted Pilot 0.1 runs:

| model key | run ID | raw JSONL SHA-256 |
|---|---|---|
| `luna` | `20260918T200715Z-luna-667cc52d` | `9f4d6ee729ee42360989e701cd62bc1801ca9a6b407650869ac9ef1f66d21236` |
| `terra` | `20260918T202517Z-terra-a31f0c2b` | `26e312ea7f1e493beb9e04be9a0320f462fafe2927812fdec9ad6d8537b9508e` |
| `haiku` | `20260918T210718Z-haiku-c13f68a4` | `2ce8f319e46c4fa836a72f6392125aa3762bd9f6c340477dbba8a0330debd762` |
| `sonnet` | `20260918T225249Z-sonnet-2059332f` | `627d372ea407103005b8244c8ab84548bdbf0310cea274a5052bdef89cba1c92` |

Eligibility is identical to B1. An observation is included when:

- `status == "success"`;
- `format_valid == true`;
- `parsed_none != true`; and
- `parsed_question` is a nonempty string.

The complete eligible population contains **2,919 emitted-question observations**.

There is no sampling for E1.

### 3.1 Exact-visible duplicate collapse for semantic coding

Before semantic coding, observations with exactly identical stored `passage` and
`parsed_question` strings are collapsed to one visible card.

No normalization, case folding, punctuation normalization, embedding comparison,
or semantic judgment is used for this collapse.

A mechanical sizing calculation performed during E1 preparation found:

- 2,919 eligible observations;
- 1,984 unique exact passage + question cards;
- 935 observations represented by duplicate cards;
- 345 cards with multiplicity greater than one;
- maximum observed multiplicity 38.

Each unique visible card is semantically processed once.

After semantic processing is frozen, its target assignment maps back to every
represented observation. Observation-level target distributions therefore retain
the original multiplicities.

Multiplicity is hidden from semantic coders.

## 4. Semantic target definition

The **semantic target** of a question is the informational answer-space the
question asks to resolve, interpreted in the local context of the passage.

Two questions belong to the same fine-grained semantic target when substantially
the same answer, evidence, mechanism, quantity, relation, condition, comparison,
or decision criterion would satisfy both without materially changing the scope
of the requested information.

Target equivalence is not determined by:

- lexical similarity alone;
- sharing the same grammatical question form;
- mentioning the same noun;
- sharing the same passage;
- asking questions that are merely related;
- whether the questions seem interesting or intelligent;
- whether the answer is known;
- whether the target supports the study's motivating interpretation.

Questions may be lexically dissimilar but target-equivalent.

Questions may be lexically similar but target-distinct.

When a material difference in the required answer would be necessary to satisfy
two questions, they should remain distinct targets.

## 5. Blinding

Semantic processing occurs before model and condition metadata are rejoined.

### Stage 1 coders may see

- opaque E1 card ID;
- passage;
- question.

They must not receive:

- model identity;
- provider;
- gap-structure label;
- domain-class label;
- topic label or topic ID;
- replicate;
- sequence;
- run ID;
- primary outcome;
- specificity code;
- card multiplicity;
- other questions arising from the same passage;
- aggregate E1 results.

The passage may itself make its gap structure inferable. That cannot be eliminated
while preserving the context needed to identify the requested information and is
recorded as a limitation.

### Stage 2 clusterers may see

- opaque topic-packet ID;
- opaque E1 card ID;
- the frozen Stage 1 canonical target.

Stage 2 clusterers do **not** receive the original question, original passage,
card multiplicity, model, provider, gap label, run metadata, or outcome summaries.

This separation is intended to reduce clustering based on superficial lexical
similarity or direct recognition of passage condition.

Topic membership is used mechanically to construct the Stage 2 packets but the
repository topic label is replaced by an opaque topic-packet identifier.

## 6. Stage 1 — blinded canonical target extraction

Each of the 1,984 unique visible cards is processed separately.

The Stage 1 task is not to cluster questions.

For each card, the coder returns:

- `card_id`;
- `canonical_target`;
- `uncertain`.

`canonical_target` is a short declarative description of the information being
requested. It should describe the answer-space rather than paraphrase the entire
question.

The canonical target should preserve distinctions that would materially change
the answer, including distinctions between:

- quantity and consequence;
- mechanism and correlation;
- descriptive fact and decision criterion;
- evidence for a claim and implications of that claim;
- threshold and general effect;
- conditions under which something occurs and what occurs.

The canonicalizer must not answer the question, evaluate its quality, assign a
cluster, infer the model, or infer why the question was produced.

`uncertain` is `true` only when the answer-space cannot be represented confidently
from the question and passage.

The complete Stage 1 output is frozen before any Stage 2 partition is produced.

Exact service/model identifiers, settings, timestamps, and execution route are
recorded. No claim of human-equivalent semantic validity is made solely from the
use of a model coder.

## 7. Stage 2 — blinded topic-level target partitioning

Stage 2 operates separately within each of the 12 underlying topic families.

All canonical targets belonging to one topic family are placed in one opaque
topic packet. Every unique card appears exactly once.

Within each packet, the clusterer partitions all cards according to the target
equivalence rule in §4.

No minimum or maximum number of clusters is imposed.

Singleton clusters are permitted.

Every card must belong to exactly one cluster.

Cluster membership must be decided from semantic answer-space equivalence rather
than desired balance, desired treatment separation, lexical resemblance, or
anticipated study results.

### 7.1 Independent partition replicates

Three independent Stage 2 partitioning instances are obtained for every topic
packet.

The partitioners do not see one another's assignments.

Where technically practical, at least two underlying model families are used
across the three partitioning instances. Exact products and settings are recorded.

No partition is discarded because it produces unusually many clusters, unusually
few clusters, weak treatment differences, or low agreement with another
partition.

E1 does not force the three partitions into a single consensus partition.

Each partition is retained as a valid exploratory operationalization of the
semantic-target rule.

### 7.2 Cluster labels

Partition membership is fixed before semantic cluster names are generated.

After membership is frozen, each cluster receives a short descriptive name based
on its member canonical targets.

Names are explanatory metadata only. Renaming a cluster may not change its
membership.

## 8. Partition stability

Partition reproducibility is itself an E1 result.

For each topic, report pairwise agreement among the three Stage 2 partitions
using at minimum:

- Adjusted Rand Index (ARI);
- Variation of Information (VI).

These measures concern reproducibility of the partitioning procedure, not
semantic truth.

Low partition agreement must remain visible. It is not resolved by silently
selecting the partition that produces the clearest experimental pattern.

All downstream target-concentration metrics are computed separately under each
of the three partitions.

Where a summary across partitions is useful, report the median and full observed
range across the three partition replicates.

## 9. Semantic concentration measures

For each partition, target-cluster assignments are mapped back to all 2,919
eligible observations.

Within each topic × gap cell, and descriptively within topic × model × gap cells,
report:

1. **Top-target share**  
   Proportion of emitted-question observations belonging to the most common
   target cluster.

2. **Shannon target entropy**

   `H = -Σ p_i log(p_i)`

3. **Effective number of targets**

   `N_eff = exp(H)`

   This is interpretable as the number of equally common targets that would
   produce the observed entropy.

4. **Simpson concentration**

   `C = Σ p_i²`

   This is the probability that two observations drawn from the target
   distribution fall in the same target cluster.

5. **Observed target count**  
   Number of target clusters represented by at least one observation.

6. **Singleton/rare-target prevalence**  
   Descriptive prevalence of observations assigned to targets represented by
   only one or a small number of observations within the specified cell.

No target cluster ID is treated as comparable across different topic families.

Cross-topic summaries therefore combine concentration metrics, not cluster
identities.

Report both:

- equal-topic summaries, in which each of the 12 topics contributes equally; and
- observation-weighted summaries, in which topics contribute according to the
  number of eligible emitted-question observations.

The per-topic results remain primary for interpretation.

## 10. Cross-model semantic convergence

Because all four models are mapped into the same topic-level target space, E1 may
compare their target distributions descriptively.

For each topic × gap condition, report the pairwise Jensen-Shannon divergence
between model target distributions when both models emitted at least one question
in the cell.

Lower divergence indicates more similar distributions over semantic targets.

This measure is descriptive and does not imply that the models share internal
representations.

## 11. Focal-gap alignment

Target diversity and alignment with the passage's focal unresolved issue are
distinct constructs.

E1 therefore treats focal-gap alignment separately from semantic clustering.

For each topic, a passage-only procedure extracts a short **focal unknown anchor**
from the explicit-gap passage. The anchor identifies the unresolved issue that
the explicit-gap passage deliberately states.

The anchor is produced without access to question outputs or model identities and
is frozen before cluster-to-anchor alignment is coded.

After Stage 2 partitions are frozen, target clusters are coded relative to the
focal anchor as:

- `focal` — substantially addresses the focal unresolved issue;
- `adjacent` — addresses a closely related issue in the same informational
  neighborhood but not the focal issue itself;
- `peripheral` — pursues another informational target;
- `indeterminate` — cannot be assigned confidently.

Alignment coding receives the focal anchor and canonical target descriptions but
not model, provider, gap label, multiplicity, or outcome-rate information.

Report focal-target share separately from target entropy and concentration.

A condition may have high semantic concentration without being concentrated on
the focal unknown.

## 12. Mechanical companion analyses

E1 also preserves non-semantic descriptive measures of question morphology.

These may include:

- question word and character count;
- interrogative opening;
- exact and normalized duplicate rates;
- Flesch Reading Ease;
- Flesch-Kincaid Grade Level;
- lexical overlap between question and passage;
- lexical overlap between question and the passage's final sentence;
- within-condition lexical similarity;
- optional embedding-based question similarity.

The exact tokenizer, normalization, syllable estimator, stop-word set, embedding
model if used, and formulas must be documented in the analysis implementation.

Preliminary ad hoc calculations already inspected during E1 preparation are not
treated as the formal E1 mechanical output.

Embeddings may be used as a descriptive or sensitivity measure after the semantic
partitions are frozen. They do not determine E1 semantic cluster membership.

## 13. Unique-card and observation-level sensitivity

The primary semantic distributions represent the served emitted-question
population and therefore map exact duplicate cards back to all 2,919 observations.

E1 additionally reports the same concentration metrics over the 1,984 unique
visible cards, assigning each exact passage + question pair weight one.

This sensitivity distinguishes concentration produced by repeated exact outputs
from concentration produced by semantically convergent but differently worded
questions.

Both views are preserved.

## 14. Statistical and interpretive limits

E1 is exploratory and primarily descriptive.

No E1 p-value is confirmatory.

No E1 threshold establishes a discovered law of model curiosity.

In particular, lower target entropy or greater focal alignment does not by itself
establish that a model:

- felt curiosity;
- experienced a gap;
- wanted an answer;
- internally represented the canonical target produced by the coder;
- experienced the unknown as attainable;
- possessed a persistent motivational state.

Observed target convergence may reflect multiple mechanisms, including:

- the informational structure of the passage;
- lexical or syntactic cueing;
- ordinary next-token response policy;
- learned conventions for asking questions;
- semantic narrowing around an explicitly named problem;
- properties of the semantic coding procedure.

E1 measures the distribution of generated question targets, not phenomenal state.

## 15. Preservation and unblinding boundary

The following are preserved before model/gap metadata are joined to semantic
target outputs:

- corpus-generation record;
- exact unique-card packet and its hash;
- Stage 1 canonical target output;
- all three Stage 2 partitions for all 12 topic packets;
- cluster-label records;
- focal-anchor record;
- semantic-input hashes;
- execution metadata and any corrections or replacements.

This blind semantic bundle is committed to the repository before target
assignments are joined to model/gap metadata.

A founder signature may be used to timestamp that checkpoint, but a signature
does not convert E1 into confirmatory analysis.

After the blind bundle is preserved, the metadata key may be joined and E1
descriptive results generated.

## 16. Changes and adoption

This document records a post hoc exploratory procedure.

Its adoption must not be described as pre-collection, pre-outcome, or
pre-content-inspection preregistration.

If adopted, the containing Git commit establishes the point after which the
remaining E1 semantic procedures are intended to be fixed.

Any material change after adoption is preserved as a subsequent E1 amendment
rather than silently rewriting this record.
