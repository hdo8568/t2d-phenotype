# Agent E — a routing signal that actually varies

Agent B escalated on the model's self-reported confidence, and that signal
turned out to be the constant `high` on 2,686 of 2,686 screens. This run
replaces it with a *measured* one: ask the cheap model the same question
k=3 times at temperature 1.0 and escalate only when the votes
disagree. Sampling disagreement cannot be rounded up to `high` by a model
describing itself.

> ### Every patient voted unanimously. This signal is constant too.
> All 400 patients agreed with themselves 3-0. Not one genuine split.
> (1 patient(s) did escalate — but on a FAILED vote, not a disagreement. That is API flakiness, not
> uncertainty, and it is counted separately here for the same reason
> Agent B's escalations had to be: a failure dressed as a signal is
> how you conclude that a dead trigger works.)
>
> Same dead trigger as Agent B, reached by a different route and at
> 3x the screening cost.
>
> This is a result, not a failure. It says the decision boundary is
> nowhere near these patients: the task, as posed by the six-fact chart,
> is easy enough that temperature-1.0 sampling cannot separate anything.
> Uncertainty-based routing has now failed twice for the same underlying
> reason — the model is not uncertain. Any future router should key on
> evidence structure (as the rule-based router already does), not on the
> model's opinion of its own answer, however that opinion is elicited.

## Vote splits

| split | patients | share |
| --- | --- | --- |
| 3 | 399 | 99.8% |
| 2 | 1 | 0.2% |

- Unanimous: **399/400** (99.8%)
- Escalated to `claude-sonnet-5`: **1** (0.2%)

## Cost

| | |
| --- | --- |
| patients | 400 (sample of the non-decisive bucket, seed=42) |
| total | $1.2312 |
| per patient | $0.003078 |
| vs Agent A per patient | $0.006019 |
| vs Agent B per patient | $0.001027 |
| wall clock | 0.42 min |

Voting k=3 times triples the screening cost. With no splits to escalate, that is 3x spend for
zero routing decisions — the cost of finding out that the signal is flat.

## Agreement with Agent A

- Compared on 400 patients
- Agree: **400** (100.00%)
- Disagree: **0**

## Does disagreement correlate with anything?

| feature | split-vote patients | all patients |
| --- | --- | --- |
| has a T2D dx code | 0.0% | 3.2% |
| A1c in 6.0-7.0 (near the 6.5 threshold) | 0.0% | 46.2% |

Vacuous: with zero split-vote patients there is nothing to correlate.
The columns are left in so the shape of the intended analysis is visible.

`submission_consensus.csv` is an experiment artifact covering the 400 sampled patients only — not a scoreable submission, and not
padded with rule labels.

