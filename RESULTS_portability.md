# Agent F — cross-schema portability

The stated reason to prefer LLM phenotyping over feature-engineered ML is
that it ports across institutions with varying schemas (Tim, 7/29). That
claim is untestable on one dataset, so `mangle.py` builds a second one:
the same patients and the same clinical facts wearing a different schema
and a different coding system.

## The confound, stated up front

**The LLM still reads the descriptions.** `mangle.py` renames every column,
remaps every SNOMED/RxNorm/LOINC code to an arbitrary local integer, and
deletes `careplans.csv` — but it leaves `DESCRIPTION` text intact. So this
measures robustness to **schema and vocabulary drift**, not to information
loss. A site that ships codes with no readable descriptions would defeat
the LLM as thoroughly as it defeats the rules, and this experiment says
nothing about that case.

That is the realistic case, though: extracts differ in column names and
local code systems far more often than they omit human-readable text.

## How the rules break

Two distinct failures, and the second is the dangerous one:

1. **Without an integration layer — hard exception.** `KeyError: 'CODE'`
   Loud, immediate, impossible to miss.
2. **With a column map — silent zero-match.** The records load cleanly, all
   3,539 of them, and every `.isin(T2D_DX)` test returns nothing
   because `44054006` is now `700xxx`. No exception, no warning: the
   algorithm reports **0 cases** and looks
   like it ran successfully.

A phenotype that fails loudly can be fixed. One that returns a clean,
confident, empty cohort is the failure mode that gets published.

## Results

F1 against Agent A's labels, on the 600 sampled patients (seed=42):

| method | F1 | precision | recall | vs clean |
| --- | --- | --- | --- | --- |
| rules, clean schema | 0.8991 | 1.0000 | 0.8167 | — |
| **rules, mangled** | **0.0000** | 0.0000 | 0.0000 | **-0.8991** |
| LLM, clean schema | 1.0000 | 1.0000 | 1.0000 | — |
| **LLM, mangled** | **1.0000** | 1.0000 | 1.0000 | **+0.0000** |

**Degradation delta: rules -0.8991, LLM +0.0000.**

- Labels changed by mangling (LLM): **0** of 600 (0.00%)
- Whole-cohort rules F1: clean 0.9007 -> mangled 0.0000

## Cost

| | |
| --- | --- |
| LLM calls | 1,200 (600 per arm) |
| total | $3.4567 |
| per patient per arm | $0.002881 |
| rules, both arms | $0.0000 |
| wall clock | 13.94 min |

`mangle.py` itself makes zero API calls, and so does the rules arm.

`submission_portability.csv` holds the mangled-arm labels for the 600 sampled patients — an experiment artifact, not a
scoreable submission, and not padded.

