# Full-cohort agentic T2D phenotyping — measured run

Every T2D submission on the dashboard to date is deterministic and reports
`cost_usd = 0`. This one does not. What follows is measured, not estimated.

## Run integrity — read this first

| check | count | meaning |
| --- | --- | --- |
| fallbacks to rule label | **0** | patients with no LLM verdict; NOT model agreement |
| parse failures | **0** | unparseable responses, raw text in `parse_failures.log` |
| refusals | 0 | model declined to answer |
| empty responses | 0 | no text returned |
| truncated responses | 0 | hit the max_tokens ceiling |
| 429s absorbed | 0 | retried with backoff |

> **1 of 20 adjudicated patients (5.0%) diverge from the rule baseline** — 1 negative->positive, 0 positive->negative.

## Method

- Model: `claude-sonnet-5`, one call per patient, reasoning effort `medium`.
- Mode: **full cohort (--all)** — 20 of 3,539 patients adjudicated by the LLM; the remainder carry the rule label.
- Chart: structured render of demographics, conditions, collapsed
  medications, a 13-test metabolic lab panel, encounter counts and care
  plans. Clinical notes were deliberately **not** included, to keep the
  chart identical to the one the cost projection was measured on.
- Concurrency: started at 4 workers, never throttled — finished at 4.
  Retries on 429/503 with exponential backoff and jitter; on repeated
  failure the patient falls back to the rule label and is recorded as a
  fallback rather than as agreement.

## Cost and latency

| metric | value |
| --- | --- |
| wall clock | **2.42 min** |
| API calls | 20 |
| input tokens | 44,728 |
| output tokens | 2,659 |
| cache write tokens | 0 |
| cache read tokens | 0 |
| **total cost** | **$0.1160** |
| cost per patient | $0.00580 |
| mean latency | 13.35 s |
| median latency | 3.83 s |
| p95 latency | 23.70 s |
| retries | 1 |
| fallbacks | 0 |

Pricing: $2.00/MTok input, $10.00/MTok output (Sonnet introductory rates, valid through 2026-08-31).

**On prompt caching.** The system prompt is identical across every call
and is sent with `cache_control`, but it is roughly 275 tokens and the
minimum cacheable prefix on Sonnet is 1024. The cache therefore never
engages, which is exactly what the two zero rows above report. Caching
would only pay here if the shared prefix were padded past the minimum —
worth doing deliberately, not worth pretending already happened.

## Divergence from the rule baseline

- Patients adjudicated by the LLM: **20**
- Labels matching the rule baseline: **19**
- Divergent from the PheKB rule label: **1** (5.0% of adjudicated)
  - rules negative -> LLM positive: **1**
  - rules positive -> LLM negative: **0**
- Of the rule-negative flips, **1** carry a T2D
  diagnosis code and 0 do not.

Final submission: **315 positive** / 3,224 negative out of 3,539.
The frozen rule baseline calls 314 positive.

The flips with a diagnosis code are the defensible ones: those patients are
coded diabetic and were dropped by the algorithm's insulin branch, a Type 1
exclusion doing work in a dataset with no Type 1 patients. The flips without
a diagnosis code are the risky ones — against a silver standard derived from
the rules themselves, they can only cost precision, however clinically
reasonable the model's stated reason is. `divergence.csv` has every case with
the model's own words.

## Files

| file | contents |
| --- | --- |
| `submission.csv` | 3539 rows, `patient_id,label` |
| `submission_PATIENT_pred.csv` | same labels, `PATIENT,prediction` |
| `submission_id_label.csv` | same labels, `patient_id,label` |
| `submission_Id_pred.csv` | same labels, `Id,prediction` |
| `run_log.csv` | per patient: label, reason, tokens, latency, attempts |
| `divergence.csv` | every disagreement with the rules, with reasons |
