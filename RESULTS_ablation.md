# Agent D — chart ablation

Does chart engineering matter more than model choice? Same model as Agent A
(`claude-sonnet-5`), same schema, same everything — except the chart is cut
to six facts: age, sex, T2D dx code present/absent, max HbA1c, max glucose,
diabetes medication present/absent.

## Deviation from spec — read first

**Sample is 700, not the requested 1,000** (seed=42). Agent B spent $2.76 of
the $5 combined cap; 1,000 patients here priced at $2.93 against $2.24
remaining, so the sample was sized to the budget rather than the run
being started and aborted partway with nothing to show.

The sample is random over the full roster with a fixed seed, so it is
unbiased — but at n=700 the agreement figure below carries a
sampling error of roughly ±1-2 points, which is the same order as the
effect being measured. Treat the cost numbers as precise and the
accuracy delta as directional.

## The two numbers, kept separate

| | |
| --- | --- |
| **cost reduction** | **54.0%** ($0.006019 -> $0.002770 per patient) |
| **accuracy delta** | **0 of 700 labels changed** (0.00% disagreement with Agent A) |

Reported apart on purpose: a cost saving and an accuracy cost are not
commensurable, and averaging them into one score would hide whichever one
is inconvenient.

## Chart size

| | full | minimal | ratio |
| --- | --- | --- | --- |
| mean tokens/chart | 716 | 43 | 6.0% |
| min | 164 | 41 | |
| max | 1,403 | 46 | |

## Cost

| | |
| --- | --- |
| patients labeled | 700 (random sample, **seed=42**) |
| input tokens | 594,044 |
| output tokens | 75,092 |
| total cost | $1.9390 |
| per patient | $0.002770 |
| Agent A per patient | $0.006019 |
| wall clock | 8.10 min |

Output tokens dominate once the chart is gone: the input shrank to
6% of full, but reasoning tokens bill as output and
do not shrink with the prompt. That ceiling is the real finding about how
far chart trimming alone can take cost down.

## Which patients flipped

- Agreement with Agent A: **700/700** (100.00%)
- Agent A positive -> minimal negative: 0
- Agent A negative -> minimal positive: 0

`submission_minimal.csv` holds exactly the 700 patients this
experiment labeled — not a padded 3,539. Filling the remainder with rule
labels would invent labels this run never produced.

