# Design Notes

**Status: exploratory. Nothing in this document is preregistered.**

## 1. Conceptual object

The project begins from the proposition:

> Curiosity may arise when a person becomes aware of a specific piece of knowledge they do not possess and experiences that knowledge as attainable.

The present design adds a second proposition:

> Acquiring one piece of knowledge may terminate curiosity or expose further specific, attainable unknowns.

The instrument therefore treats an answer not only as a reward, but as a possible **junction**.

## 2. Candidate behavioral dimensions

### Breadth

How many different territories become objects of voluntary interest or inquiry?

The interest map currently provides a lightweight breadth proxy.

### Depth

After a root question is answered, does the participant stop satisfied, open one clarifying branch, or open two?

Pilot 0.1 therefore records depth as 0, 1, or 2 for each item.

### Direction

When several newly attainable unknowns are available, what kind of question does the participant pursue?

Pilot 0.1 uses three recurring hidden branch families:

- **explanation** — mechanism, structure, reason;
- **boundary** — exception, limit, contrast;
- **implication** — consequence, application, significance.

These labels are analytic metadata only. Participants see ordinary questions.

Breadth, depth, and direction should not be assumed to reduce to one scalar curiosity trait.

## 3. Concrete and abstract inquiry

The pilot bank deliberately includes both relatively concrete subjects and more abstract concepts.

This allows exploratory comparison of whether curiosity behaves differently when an answer concerns a physical mechanism versus a conceptual structure with contested or theory-dependent boundaries.

Abstractness is **not yet a confirmatory manipulation**. It is a bank characteristic worth observing during piloting.

## 4. Interest-map specificity

Two interest-map variants remain under consideration:

- **broad map** — large intellectual territories;
- **specific map** — concrete named topics.

Pilot 0.1 can randomize participants between them.

The current tool does not use selected interests to choose later root items. This preserves the interest map as a measurable antecedent rather than making it a hidden routing system.

## 5. Pilot 0.1 trial structure

For each sampled root item:

1. participant reads one specific unknown;
2. participant rates desire to know on a 0–100 slider;
3. participant reveals the initial answer;
4. three clarifying branches appear in randomized order;
5. participant may stop immediately, open one branch, or open two of three;
6. the remaining third branch becomes unavailable after two are opened;
7. the study proceeds to the next root item.

Each session samples three concrete and three abstract items from the 12-item draft bank.

All six permutations of the three branch families are available for random presentation.

## 6. Competing motivation: task minimization

Paid online participants may rationally attempt to complete a task efficiently.

Low breadth or low depth therefore should not automatically be interpreted as low curiosity.

Pilot 0.1 records a final 0–100 self-report:

> While doing this study, how much were you trying to finish as quickly as possible?

Latency measures provide additional exploratory context but should not be treated as a mind-reading device.

Compensation should not depend on how many interests or branches a participant chooses.

## 7. Candidate outcomes

Available pilot measures include:

- category-selection breadth;
- root-curiosity rating;
- branch depth per item;
- first and second branch type;
- branch position;
- kind of root item (concrete/abstract);
- latency measures;
- stated speed motivation.

The final confirmatory hierarchy remains unresolved.

## 8. Stimulus constraints

Stimuli should:

- remain low-sensitivity for the first study;
- have accurate, reviewable root answers;
- expose three genuinely distinct clarifying paths;
- avoid making one branch obviously longer, more dramatic, or more practically important than the others;
- avoid permanently coupling branch type to visual position;
- avoid requiring specialist knowledge to understand the answer;
- make stopping after the root answer a legitimate state of satisfaction.

## 9. Open design questions

Before preregistration, decide:

- whether interest-map granularity is confirmatory or merely methodological;
- whether concrete/abstract status should become an explicit factor;
- whether 6 root items is enough for stable within-person direction estimates;
- whether depth should remain capped at two or later support multi-level trees;
- whether the root-curiosity slider adds signal or merely primes introspection;
- which latency measures are worth preserving;
- how to distinguish genuine satisfaction from task minimization;
- sample size and power basis;
- exclusion criteria;
- confirmatory statistical model;
- durable data storage and Prolific completion routing.
