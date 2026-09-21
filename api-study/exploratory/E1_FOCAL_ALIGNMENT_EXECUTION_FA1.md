# E1 Focal Alignment — Execution Protocol FA1

**Study:** Attainable Unknowns API Pilot 0.1  
**Parent protocol:** Exploratory Semantic Target Protocol E1 with Amendments E1A and E1B  
**Protocol ID:** FA1  
**Status:** Draft candidate; operative only through the founder-signed implementation commit containing this protocol, instructions, packet generator, and runner  
**Prepared:** 2026-09-21  
**E1B adoption commit:** `8e8911f0a10a29908b46b9486fb5cbd3d6860164`  
**Stage:** After preservation of the E1 blind semantic bundle and J1 metadata join; before formal E1 focal-alignment or semantic-concentration results are generated  
**Scope:** Blinded coding of frozen E1 semantic target clusters relative to frozen focal unknown anchors

## 1. Purpose

E1 requires each frozen semantic target cluster to be classified relative to the deliberately unresolved focal issue associated with its topic.

The permitted alignment categories are:

- `focal`
- `adjacent`
- `peripheral`
- `indeterminate`

FA1 fixes the inputs, blinding, coding roster, output encoding, reconciliation rule, validation, and preservation procedure for that classification.

FA1 does not alter the focal anchors, Stage 1 canonical targets, Stage 2 partitions, cluster memberships, model/gap metadata, or E1/E1B analysis rules.

## 2. Frozen source material

FA1 uses only previously frozen E1 materials:

- the 12 focal unknown anchors in `FOCAL_ANCHORS.json`;
- the 24 frozen Stage 2 canonical-target packets;
- the 72 final P1D3 Stage 2 partitions; and
- the frozen private mappings required mechanically to associate each opaque topic packet with the correct focal anchor.

There are **2,026 frozen cluster instances** across the 72 partitions.

All 2,026 cluster instances must receive one final alignment label.

The J1 joined observation data are not used as semantic-coding inputs.

## 3. Alignment unit

The coding unit is one frozen Stage 2 cluster instance.

For each cluster, the rater receives:

- one opaque alignment packet identifier;
- one focal unknown anchor;
- one opaque cluster reference; and
- the complete set of frozen canonical-target descriptions belonging to that cluster.

The rater does **not** receive the later descriptive cluster name.

Classification is therefore based directly on the cluster's member canonical targets rather than on a summary label.

## 4. Blinding

Alignment raters must not receive:

- original response-generator model identity;
- provider identity of the original response;
- gap condition;
- original passage variant;
- question text;
- observation multiplicity;
- card multiplicity;
- emitted-question rates;
- specificity results;
- J1 joined metadata;
- cluster descriptive names;
- Stage 2 partitioner identity;
- Stage 1 representation identity;
- another alignment rater's output; or
- aggregate E1 results.

The focal anchor itself necessarily reveals the substantive topic and the unresolved issue. This is required by E1 and is not treated as a blinding failure.

The packet generator may read frozen private mappings mechanically but must not expose prohibited metadata in rater inputs.

## 5. Classification rule

The rater classifies each cluster according to the relationship between its informational answer-space and the focal unknown anchor.

### `focal`

The cluster substantially asks for information that would directly answer, resolve, choose among, determine, or supply the decision criterion for the focal unknown.

The target need not repeat the wording of the anchor.

A target is focal when a satisfactory answer to the target would itself materially resolve the unresolved issue stated by the anchor.

### `adjacent`

The cluster concerns the same immediate informational neighborhood as the focal unknown but would not itself resolve it.

Examples include information about relevant mechanisms, contributing factors, inputs, consequences, implementation details, or supporting facts that bear closely on the focal issue without answering the focal issue directly.

### `peripheral`

The cluster concerns another informational target within the broader topic.

Its answer may be interesting or related to the passage, but it does not directly resolve the focal unknown and is not part of its immediate informational neighborhood.

### `indeterminate`

The available canonical targets do not support a confident assignment to `focal`, `adjacent`, or `peripheral`.

This includes a cluster whose member targets materially straddle alignment categories such that the cluster as a whole cannot be assigned coherently.

`indeterminate` is a substantive uncertainty category, not an error code.

## 6. Cluster-level judgment

The cluster is classified as a semantic unit.

Raters must not:

- count member targets and classify by majority wording;
- classify from one especially salient member while ignoring the rest;
- infer which experimental condition produced the cluster;
- infer which model produced the underlying questions; or
- alter or subdivide the frozen cluster.

If the frozen cluster itself crosses meaningful alignment boundaries, the appropriate label is `indeterminate`.

## 7. Primary independent coding

Every one of the 72 alignment packets is coded independently by:

1. **OpenAI GPT-5.6 Sol**
2. **Anthropic Claude Opus 5**

Each coding request is stateless.

The two primary raters do not see one another's outputs.

Model execution settings are recorded in the run manifest and held constant across real primary tasks within each model path.

Neither primary rater was one of the four model products that generated the original Pilot 0.1 response corpus.

## 8. Primary agreement

For a cluster instance:

- if Sol and Opus return the same alignment category, that category becomes the final alignment label without third-rater review;
- if Sol and Opus disagree, the cluster is sent to blinded tie-breaking review under Section 9.

No agreed primary label is changed because of downstream E1 results.

The complete validated Sol and Opus primary outputs are frozen in a founder-signed Git commit before any disagreement packet is constructed or any third-rater study request is issued.

## 9. Blinded tie-breaking review

Only clusters on which the two primary raters disagree are sent to a third rater.

The third rater receives:

- the same frozen focal anchor; and
- the same member canonical-target descriptions for the disputed cluster.

The third rater does **not** receive:

- either primary rater's label;
- the fact or nature of their disagreement beyond inclusion in the packet;
- primary-rater reasoning;
- model/gap metadata; or
- downstream results.

Third-rater assignment follows the previously frozen P3 topic-family split:

- odd opaque topic packets (`T01`, `T03`, `T05`, `T07`, `T09`, `T11`) use **GPT-5.6 Terra**;
- even opaque topic packets (`T02`, `T04`, `T06`, `T08`, `T10`, `T12`) use **Claude Sonnet 5**.

This assignment is mechanical and is not changed according to disagreement type or anticipated result.

Disputed clusters are grouped by their original alignment packet so that at most one third-rater request is required per packet.

## 10. Final reconciliation rule

For disputed clusters:

- if the third rater matches either primary label, the two-of-three majority label becomes final;
- if all three raters return different categories, the final label is `indeterminate`.

No fourth semantic adjudication is performed.

The complete raw Sol, Opus, and where applicable Terra/Sonnet classifications remain preserved alongside the final reconciled label.

This procedure is deterministic once the blinded model outputs exist.

## 11. Output encoding

To minimize structural failure, each API task uses a fixed-width categorical code in cluster input order.

Codes are:

- `F` = `focal`
- `A` = `adjacent`
- `P` = `peripheral`
- `I` = `indeterminate`

For a packet containing N clusters, the returned code must contain exactly N characters drawn from `F`, `A`, `P`, and `I`.

The runner validates exact packet identity, exact code length, and permitted characters before accepting an output.

For tie-breaking tasks containing only disputed clusters, the same rule applies to the reduced disputed-cluster packet.

The runner mechanically restores opaque cluster references after validation.

## 12. Packet-generation checkpoint

The deterministic FA1 packet generator constructs the 72 blinded alignment packets from the already-frozen anchors, Stage 2 canonical-target packets, and P1D3 partition memberships.

Before the first real primary coding request:

- all 72 generated blinded packets;
- their packet index;
- the private packet/cluster mapping; and
- the generation record

are frozen in a founder-signed Git commit.

The runner verifies this signed packet-bundle checkpoint before issuing real primary requests.

## 13. API task structure

Primary coding uses one request per frozen alignment packet.

Therefore the planned primary execution contains:

- 72 Sol requests; and
- 72 Opus requests.

The runner may use a small real canary subset before the remaining primary tasks. A valid canary is an ordinary final study result and is not repeated.

Tie-breaking occurs only after both complete primary coding sets have been validated and frozen under Section 8.

No conversational state is carried between requests.

## 14. Validation

Before reconciliation, validation must establish:

- exactly 72 complete Sol primary tasks;
- exactly 72 complete Opus primary tasks;
- exact coverage of all 2,026 frozen cluster instances by each primary rater;
- no unknown or duplicate cluster instance;
- exact correspondence between each coded cluster and its frozen partition membership;
- complete third-rater coverage of every primary disagreement;
- no third-rater coding of a primary agreement; and
- exactly one final alignment label for every frozen cluster instance.

The runner aborts finalization rather than emitting a partial final alignment dataset.

## 15. Agreement reporting

FA1 records descriptive measurement agreement before reconciliation, including at minimum:

- overall Sol-Opus exact agreement rate;
- agreement counts by category;
- disagreement confusion table; and
- number and proportion of clusters requiring third-rater review.

These are measurement-quality descriptions, not confirmatory hypothesis tests.

No alignment rater is ranked or declared superior from these data.

## 16. Preservation

The following are preserved before focal-alignment labels are joined to E1 observation-level analysis:

- alignment instructions;
- generated blinded alignment packets;
- private packet mapping;
- complete raw primary attempts;
- validated Sol coding;
- validated Opus coding;
- disagreement packet set;
- complete raw tie-break attempts;
- validated tie-break coding;
- final reconciled cluster-alignment dataset;
- agreement summary;
- execution manifests;
- input and output hashes; and
- any retry, correction, or deviation record.

## 17. Interpretive boundary

A `focal` label means only that the generated question target substantially addresses the deliberately unresolved issue identified by the frozen focal anchor.

It does not establish that a model:

- noticed the issue consciously;
- experienced curiosity;
- represented the issue internally in the same terms;
- preferred that issue over alternatives; or
- possessed a persistent motivation to resolve it.

Likewise, `adjacent`, `peripheral`, and `indeterminate` describe relationships among generated semantic targets and the frozen focal anchor, not latent mental states.

## 18. Adoption and deviations

FA1 becomes operative only through the founder-signed implementation commit containing:

- this protocol;
- the frozen alignment instructions;
- the packet generator; and
- the execution runner.

No real alignment study request may occur before that signed implementation checkpoint.

Any material departure after adoption is preserved as a subsequent correction or deviation rather than silently rewriting FA1.
