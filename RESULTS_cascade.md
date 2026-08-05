# Agent B — routed cascade with model tiering

Can a cheap model plus a cheap escalation rule reproduce Agent A's labels
for a fraction of the money? That is the project's central question and
nobody on the dashboard has answered it.

## Deviation from spec — read first

The spec had the screen read the same full chart as Agent A. At ~2,324
billed input tokens/patient that is $8.09 for the screen alone, over the
run cap. Rather than cut coverage, the chart was cut: **the Haiku screen
reads the six-fact minimal chart (~444 billed tokens); escalated patients
get the full chart at Sonnet.** Full-cohort coverage is preserved.

This tests a stronger form of the hypothesis, not a weaker one — tiering
only pays if the cheap tier is cheap on *both* axes, since a cheap model
reading an expensive prompt still bills every input token. The confound is
real and worth stating plainly: a disagreement with Agent A could come from
the smaller model or from the smaller chart, and this run alone cannot
separate them. Agent D varies the chart with the model held fixed, which is
what makes the pair interpretable.

## Headline

**$2.7606 vs Agent A's $21.30 — 7.7x cheaper**, at **99.97% label agreement** (3,538/3,539).

| | |
| --- | --- |
| rules, free | 850 patients |
| screened by `claude-haiku-4-5-20251001` | 2,689 |
| escalated to `claude-sonnet-5` | 3 (0.1%) |
| └ escalated on low confidence | 0 |
| └ escalated after a screen failure | 3 |
| escalation predicate | confidence in `('low',)` |

## Cost

| | cost | share |
| --- | --- | --- |
| screen (claude-haiku-4-5-20251001) | $2.7453 | 99.4% |
| escalation (claude-sonnet-5) | $0.0153 | 0.6% |
| **total** | **$2.7606** | |
| per patient (whole cohort) | $0.000780 | |
| per patient (called only) | $0.001027 | |
| **cost ratio vs Agent A** | **0.130x** (7.7x cheaper) | |
| wall clock | 0.24 min | |

## Agreement with Agent A

- Compared on 3,539 patients.
- Agree: **3,538** (99.97%)
- Disagree: **1**
  - Agent A positive, cascade negative: 0
  - Agent A negative, cascade positive: 1

## Is the cheap screen trustworthy?

The number that decides whether tiering is sound, reported on its own
rather than averaged into the agreement rate: **of the patients Haiku was
unsure about and escalated, Sonnet overturned 0 of 3** (0.0%).

- Escalation rate: 0.1%
- Screen answered alone: 2,686 patients

A low overturn rate means the screen was merely cautious and the escalation
budget is mostly wasted. A high one means its confidence signal is doing
real work.

### Is the confidence signal calibrated?

Haiku's own labels scored against Agent A, split by the confidence Haiku
claimed. The escalation trigger only fires on `low`, so errors made at
`high` confidence are never caught by anything:

| screen confidence | patients | wrong vs Agent A | error rate |
| --- | --- | --- | --- |
| high | 2,686 | 0 | 0.00% |
| n/a | 3 | 0 | 0.00% |

> ### The escalation trigger never fired.
> Not one patient was escalated for low confidence. The screen returned ['high', 'n/a'] and nothing else across 2,689 patients —
> a constant. All 3 escalation(s) were **failure recovery**, not uncertainty routing.
>
> So this run measures a two-model cascade in name only: in practice it
> is Haiku-on-a-minimal-chart labeling the entire middle, and the
> 7.7x saving belongs to that, not to
> tiering. The escalation path is untested here — it never carried load.
>
> That the screen was also *right* (0 errors at high confidence) makes
> this a good outcome, not a broken one. But a confidence signal with no
> variance cannot route anything, so escalating on `low` is currently
> dead code. To actually test tiering, the trigger needs a signal that
> varies — escalate on disagreement with the rules, on missing evidence,
> or on a calibrated probability rather than a self-reported label.

Haiku's high-confidence error rate is 0.00% (0/2,686), low enough that the trigger firing
only on `low` is defensible — the patients it declines to escalate are
ones it genuinely gets right.

Submission: `submission_cascade.csv` (3,539 rows).
Per-patient tiers, confidences and tokens: `run_log_cascade.csv`.

