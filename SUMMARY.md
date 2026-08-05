# T2D phenotyping — five agents, one table

Every T2D submission on the project dashboard is deterministic and reports
`cost_usd = 0`. These five runs measure what an LLM method actually costs, and
then try to make that cost smaller. Agent A is the reference all the others are
compared against; it is not ground truth, only the most expensive answer.

## Results

| agent | method | n | cost | cost/patient | agreement with A | caveat |
| --- | --- | --- | --- | --- | --- | --- |
| **A** | `claude-sonnet-5`, full chart, one call per patient | 3,539 | **$21.3019** | $0.006019 | — (reference) | Diverges from the PheKB rules on 69 patients; whether that is *better* is unmeasured — no silver-standard score. |
| **B** | rules on decisive buckets (850 free) + `haiku-4.5` screen on 2,689 + Sonnet escalation | 3,539 labels<br>(2,689 called) | **$2.7606** | $0.001027 per call<br>$0.000780 per cohort patient | **99.97%** (3,538/3,539) | The escalation trigger never fired — Haiku said `high` on 2,686/2,686. This measures Haiku on a minimal chart, not tiering. |
| **D** | `claude-sonnet-5`, six-fact chart | 700 | **$1.9390** | $0.002770 | **100%** (700/700) | n=700, not the requested 1,000 — budget-sized. Accuracy delta is directional; cost is exact. |
| **E** | k=3 `haiku-4.5` votes @ temperature 1.0, escalate on disagreement | 400 | **$1.2312** | $0.003078 | **100%** (400/400) | Zero genuine split votes. The measured signal is as flat as B's self-reported one, at 3× the screening cost. |
| **F** | `claude-sonnet-5` on mangled vs clean schema, two arms | 600 × 2 | **$3.4567** | $0.002881 per call | **100%** (600/600, both arms) | The LLM still reads `DESCRIPTION` text — tests schema/vocabulary drift, not information loss. |

Totals: **$30.79** across all five runs. Zero fallbacks, zero truncated
responses, zero unrecovered parse failures in every run.

## What the numbers say

**Cost is not the constraint.** Agent B reproduces Agent A's labels to within
one patient for **7.7× less**, and that single disagreement comes from the free
rules tier, not from the cheap model. Agent D gets identical labels from six
facts for 54% less. Nothing in these five runs found a case where paying more
bought a different answer.

**Portability is the real separation.** Agent F is the only experiment where
methods diverge sharply:

| | clean schema | mangled schema |
| --- | --- | --- |
| rules | F1 0.8991 | **F1 0.0000** |
| LLM | F1 1.0000 | **F1 1.0000** |

The rules fail two ways, and the second is the dangerous one. Without an
integration layer: `KeyError: 'CODE'` — loud and unmissable. With a column map:
all 3,539 records load cleanly, every `.isin(T2D_DX)` matches nothing because
`44054006` is now `700043`, and the algorithm reports **0 cases while appearing
to have run successfully**.

**Uncertainty-based routing failed twice, for one reason.** Agent B escalated on
self-reported confidence (constant `high`). Agent E replaced it with measured
vote disagreement at temperature 1.0 (zero genuine splits). Two different
elicitations, same flat result: the model is not uncertain on this task, so no
signal derived from its uncertainty can route. A future router should key on
evidence structure — as `router.py` already does — not on the model's opinion of
its own answer.

## The caveat that applies to all of them

**Four configurations agreeing at ~100% is not four confirmations — it is one
observation.** The silver standard is approximately "has a T2D dx code," and
every chart here surfaces that code. A model reading it off the chart scores
1.000 without demonstrating any reasoning, and that is consistent with
everything above.

The only place any method showed independent judgment is Agent A's 69
divergences from the rule baseline: 68 dx-coded patients the PheKB algorithm
dropped on its insulin branch — a Type 1 exclusion doing work in a dataset with
zero Type 1 patients — plus one reversal where the model argued a
cystic-fibrosis-related diabetes code is not Type 2. Those 69 are where the
question is live. Agreement percentages elsewhere mostly measure how legible the
dx code is.

None of these runs has been scored against the actual dashboard key. Every
"agreement" figure is agreement with Agent A, not accuracy.

## Artifacts

| file | contents |
| --- | --- |
| `RESULTS.md` | Agent A — full-cohort run, cost and divergence |
| `RESULTS_cascade.md` | Agent B — tiering, with the dead-trigger finding up top |
| `RESULTS_ablation.md` | Agent D — chart ablation, cost and accuracy reported separately |
| `RESULTS_consensus.md` | Agent E — consensus voting, flat-signal finding |
| `RESULTS_portability.md` | Agent F — three-row F1 table and the confound |
| `submission.csv` | Agent A, 3,539 rows — the only scoreable submission here |
| `submission_cascade.csv` | Agent B, 3,539 rows — also scoreable |
| `submission_minimal.csv`, `submission_consensus.csv`, `submission_portability.csv` | sampled experiment artifacts, **not** scoreable and never padded with rule labels |

Reproduce with `run.py --all`, `--cascade`, `--chart-mode minimal`,
`--consensus`, `--portability`. Every run is checkpointed and resumable; all
sampling uses `seed=42`.
