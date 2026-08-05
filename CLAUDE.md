# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A rule-based implementation of the PheKB Type 2 Diabetes phenotype (Kho et al., eMERGE) run against the Coherent synthetic EHR dataset (Synthea-style CSV exports). The rule-based cohort is not the end goal — it is the **frozen baseline that an LLM phenotyping approach is evaluated against**. That framing explains why the code carries a large audit/EDA layer: the point is to know whether the baseline is trustworthy, not just to emit a count.

## Running things

No build, no test suite, no linter. Every file is a top-to-bottom script with hardcoded relative CSV paths, so **always run from the repo root**:

```bash
python phenotype.py    # main pipeline: facts -> cases -> controls -> writes t2d_cohort.csv
python a.py            # LLM experiment on the "middle" (reads t2d_cohort.csv; needs GOOGLE_API_KEY)
python probe.py        # data-availability probe: ENCOUNTERCLASS values, supplies.csv emptiness, all condition codes
python broad_codes.py  # enumerate diabetes-adjacent SNOMED codes + patient counts (source of DM_DX_BROAD)
python provenance.py   # check encounters.csv patient IDs are a subset of patients.csv
```

**Use `/Users/henry/miniforge3/bin/python3` for everything in this repo.** Bare `python3` resolves to 3.14 in some terminals and miniforge 3.13 in others, and only miniforge has both `pandas` and `anthropic` installed. A run that works in one terminal and `ModuleNotFoundError`s in another is this, every time.

Requires `pandas`; `a.py` additionally needs `google-genai` and `python-dotenv`; `run.py` needs `anthropic`. There is no virtualenv in the repo.

**pandas version.** miniforge has pandas 3.0.5, while `phenotype.py` was written against pandas 2.x. As of the last check the whole of `phenotype.py` runs clean under 3.0.5 — no warnings, no errors, and the regenerated `t2d_cohort.csv` is identical to the 2.x baseline (314 / 536 / 2689, 68 dropped). No 3.0 incompatibilities are known. If one turns up, **flag it and leave the behavior alone** — silently "fixing" a pandas difference would move the frozen baseline that everything else is measured against.

`phenotype.py` reads `observations.csv` (~240 MB) and `encounters.csv` (~88 MB), so a full run takes a while. There is no incremental mode; iterating means editing the script and rerunning it whole. Output is print-heavy by design — the printed EDA blocks are the deliverable as much as the CSV.

## Data and secrets

The six input CSVs (`patients`, `conditions`, `medications`, `observations`, `encounters`, `careplans`, plus an empty `supplies`) live in the working directory and are **gitignored** — `.gitignore` excludes `*.csv`, so `t2d_cohort.csv` is also untracked. `.env` holds `GOOGLE_API_KEY` and is gitignored. `a.py` is itself gitignored, so the LLM half of the project is local-only; do not assume it exists in a fresh clone, and do not "fix" it by committing it.

## Architecture

### The per-patient spine (`phenotype.py`)

Everything hangs off one DataFrame, `per`, indexed by `patients.Id`, one row per patient. The five stages each add columns to it:

1. **Load** the four core tables; coerce every `CODE` to string (codes are mixed-width identifiers, not numbers — this coercion is load-bearing for every `.isin()` below).
2. **Code lists** — `T2D_DX`, `T1D_DX` (SNOMED), `T2D_MED`, `INSULIN` (RxNorm), `A1C`/`GLUCOSE` (LOINC) plus thresholds.
3. **Per-patient facts** — `t1dm_dx_count`, `t2dm_dx_count`, `physician_dx_count`, `t2dm_med_date` (earliest), `insulin_date` (earliest), `abnormal_lab`. Diagnosis counts are *distinct dates*, not row counts.
4. **Case classification** — `classify()` mirrors PheKB T2DM-CASE-SELECTION line for line: five paths, all gated on `t1dm_dx_count == 0`, **first match wins**. `which_path()` is a duplicate of `classify()` that returns `P1`–`P5` instead of `CASE`; if you edit one you must edit the other in the same order or the path breakdown silently stops describing the labels.
5. **Control classification** — `is_control()` is PheKB Algorithm 8: one path, all conditions must hold (no broad-DM dx, glucose was drawn, clean labs at *looser* thresholds A1c ≥ 6.0 / glucose > 110, ≥ 2 office visits, no DM medication).

`DM_DX_BROAD` (control exclusion) is deliberately broader than `T2D_DX` (case inclusion) — it includes prediabetes, hyperglycemia, diabetic renal disease, CF-related diabetes. Keep that asymmetry; conflating them collapses cases and controls into each other.

The resulting three-way split — CASE / CONTROL / **middle** (neither) — is the whole point. `t2d_cohort.csv` is the full labeled table with all fact columns, not just the label.

### The five case paths as implemented

Every path is gated on `t1dm_dx_count == 0`. Evaluated in order; first match wins.

| Path | Condition |
| --- | --- |
| P1 | T2D dx **and** on T2D med **and** on insulin **and** `t2dm_med_date < insulin_date` (oral agent came first ⇒ T2D, not T1D) |
| P2 | T2D dx **and** not on insulin **and** on T2D med |
| P3 | T2D dx **and** not on insulin **and** not on T2D med **and** abnormal lab |
| P4 | **no** T2D dx **and** on T2D med **and** abnormal lab (treated-but-uncoded) |
| P5 | T2D dx **and** on insulin **and** not on T2D med **and** `physician_dx_count >= 2` |

Abnormal lab for cases: A1c ≥ 6.5 **or** random glucose > 200.

### The six control conditions as implemented

`is_control()` is a single conjunction — all must hold:

| # | Condition | Implementation note |
| --- | --- | --- |
| 1 | `dm_broad_count == 0` | distinct dates with any `DM_DX_BROAD` code |
| 2 | `glucose_drawn` | ≥ 1 glucose lab exists — proves the patient was actually screened |
| 3 | `not ctrl_abnormal_lab` | **looser** thresholds than cases: A1c ≥ 6.0 or glucose > 110 |
| 4 | `office_visits >= 2` | distinct dates where `ENCOUNTERCLASS` ∈ `ambulatory`, `wellness`, `outpatient` |
| 5 | `not on_dm_med` | any `T2D_MED` **or** `INSULIN` disqualifies; supplies criterion dropped |
| 6 | `fam_hist == False` | no family-history data in Coherent ⇒ passes vacuously, not implemented as a filter |

Condition 2 is what makes a control meaningful rather than merely unlabeled — it is the difference between "screened and clean" and "never looked at".

### Code lists

| List | Vocabulary | Codes |
| --- | --- | --- |
| `T2D_DX` | SNOMED | `44054006` Diabetes (generic, treated as T2D) · `368581000119106` neuropathy · `422034002` retinopathy · `1551000119108` nonproliferative retinopathy · `90781000119102` microalbuminuria · `97331000119101` macular edema + retinopathy · `1501000119109` proliferative retinopathy · `60951000119105` blindness · `157141000119108` proteinuria |
| `T1D_DX` | SNOMED | `46635009` Type 1 DM — **matches zero patients in Coherent** |
| `DM_DX_BROAD` | SNOMED | strict superset of `T2D_DX` (all 9) plus `15777000` prediabetes · `80394007` hyperglycemia · `127013003` diabetic renal disease · `427089005` CF-related diabetes |
| `T2D_MED` | RxNorm | `860975` metformin ER 500mg · `897122` liraglutide (GLP-1) · `1373463` canagliflozin (SGLT2) |
| `INSULIN` | RxNorm | `106892` Humulin · `865098` insulin lispro (Humalog) |
| `A1C` | LOINC | `4548-4` — abnormal ≥ 6.5 (cases) / ≥ 6.0 (controls) |
| `GLUCOSE` | LOINC | `2339-0`, `2345-7` — abnormal > 200 (cases) / > 110 (controls) |

`METABOLIC_RISK` (in `a.py` only, for chart rendering, never for labeling): `162864005` BMI 30+ · `408512008` BMI 40+ · `55822004` hyperlipidemia · `59621000` hypertension · `302870006` hypertriglyceridemia · `237602007` metabolic syndrome X · `53741008` CHD · `230690007` stroke.

### Baseline result

On the 3539-patient roster: **314 cases / 536 controls / 2689 middle**. The middle is 76% of the population — that is the headline fact of this project, and the population the LLM work targets.

### The LLM experiment (`a.py`)

Consumes `t2d_cohort.csv` as read-only truth; it never recomputes the rules. It splits the middle into:

- **subgroup A** (`dm_broad_count > 0`): has a diabetes-adjacent code — the LLM could read the answer off the chart.
- **subgroup B** (`dm_broad_count == 0`): no code at all — the clean test, where the model must reason from indirect metabolic evidence (BMI, BP, lipids, smoking, comorbidities).

`build_chart(pid, mask=False)` renders one patient as text from the raw CSVs. The `mask` flag suppresses the two **leakage channels** — diabetes-adjacent condition descriptions and diabetes-named care plans — so the same patient can be shown with and without the giveaway. Preserve that property when editing the builder: anything that names diabetes must sit behind `mask`.

Note `a.py` defines its own `classify()`, which calls Gemini — unrelated to the rule-based `classify()` in `phenotype.py`.

Code lists (`A1C`, `GLUCOSE`, `T2D_MED`, `INSULIN`, `DM_DX_BROAD`) are **copy-pasted** from `phenotype.py` into `a.py` so the LLM sees exactly the evidence the rules keyed on. They are not imported. If you change a code list, change it in both files or the comparison stops being apples-to-apples.

Sampling uses `SEED = 42` with `random_state`; keep runs reproducible.

## Coherent-specific deviations (intentional — do not "fix")

The PheKB algorithm assumes a real EHR. These departures are deliberate and documented in-code:

- **No Type 1 patients exist in Coherent**, so the T1D exclusion gate never fires. It is retained as a correctness check (expected count: 0), not a working filter.
- **No billing stream** — every condition arrives via an encounter, so `physician_dx_count` is literally assigned `t2dm_dx_count`.
- **`supplies.csv` is empty**, so the Table 8 supplies criterion in the control algorithm is omitted (meds only).
- **No family-history coding**, so the control's `fam_hist == False` condition passes vacuously for everyone and is not implemented as a filter.
- **No fasting/random glucose distinction**, so control abnormality uses random glucose and A1c only.
- Generic SNOMED `44054006` ("Diabetes") is treated as T2D.
- `DM_DX_BROAD` excludes `386806002` (impaired cognition) — a false hit from the `broad_codes.py` text search, not glucose-related.

## Audit layer — why it exists

`phenotype.py` ends with an EDA block that is not decoration; it is the argument that the baseline is sound. Keep these outputs alive when refactoring:

- **cases per path (P1–P5)** — descriptive only; paths are first-match-wins, not a partition.
- **age sanity on flagged cases** — a diabetic child is a bug signal.
- **per-code patient counts** — a code matching zero patients is absent or wrong (typo/wrong vocabulary); near-zero means present but inert.
- **dropped dx-coded patients** — patients with a T2D diagnosis who still fall out as UNKNOWN, with a why-breakdown. Most are dropped for insulin. Whether that is a correct clinical exclusion or an artifact of a T1D gate that does no work in this dataset is the open question, and exactly where an LLM adjudicator is expected to disagree.
- **case/control disjointness** — must print 0.

Ages are computed against a fixed reference date (`2020-01-01`), not the diagnosis date.

## Style

The scripts are written as didactic, first-person research notes: dense inline commentary explaining *why* a step exists and what a result would mean, numbered stage banners, and generous blank-line separation between stages. Match that register — commentary that reasons about the data, not restatements of what the pandas call does.

## Project context and architecture decisions

### What the submissions are actually scored against

Submissions are scored on a Streamlit dashboard against **silver standards derived from rule-based PheKB definitions**. The metric is therefore agreement with a set of rules, not clinical truth — a clinically correct label that the rules would not have produced still scores as an error. Every submission must cover **all 3539 patients**; uncovered patients are counted against the score, so a short file is strictly worse than a complete but imperfect one.

All 22 submissions to date are deterministic (`cost_usd = 0`, `runtime_min <= 0.3`). **No LLM method has been submitted by anyone.**

### T2D headroom is small and known

The T2D silver standard is approximately "has a T2D dx code". 382 patients have one, ~319 are silver-positive, and the rules already call 314. The **68 dx-coded patients that fell to UNKNOWN hold the only remaining headroom (~5 flips)**. Patients with no T2D dx code are all silver-negative, so flagging them can only lower precision — worth remembering before any change that adds positives outside the coded set.

### Resistant Hypertension is the open phenotype

Best F1 on the board is 0.2227. 1126 patients carry HTN code `59621000`; implied silver positives ~212. Coherent stocks only 3 antihypertensives (lisinopril, HCTZ, amlodipine); 175 patients are on all 3 and **zero** on >= 4, which constrains any "resistant = on N+ agents" definition badly. The ~212 figure is **derived from dashboard arithmetic, not from Tim's actual key — treat it as unverified.**

### Architecture: a routed cascade

A **router** assigns each patient to exactly one labeler based on *what evidence exists in their record* — never on the phenotype label, which would leak the answer into the routing decision. Rules where the evidence is decisive, LLM where it conflicts or is indirect, abstain to negative where it is absent.

The router, record builder, and scorer are **method-agnostic and shared across phenotypes**; only the rules module is phenotype-specific.

| file | role |
| --- | --- |
| `records.py` | `build_records()` -> one record per patient, indexed off `patients.csv`. Also `render_chart()`. |
| `router.py` | `route(record, rules)` -> one of five buckets. Asserts disjoint and covering. |
| `labelers/rules.py` | wraps the PheKB logic; also supplies `ROUTE_PREDICATES` |
| `labelers/llm.py` | one Claude call per patient, schema-validated verdict |
| `run.py` | preflight, routing, labeling, submission, accounting |

**The spine is `patients.csv`, always.** `conditions.csv` is missing 4 patients and `medications.csv` is missing 92; building the index off either silently drops them from the submission. `records.py` prints this coverage check on every run and preflight asserts it.

The five buckets, and why `DECISIVE_POS` is not "the rules said yes": each predicate is a boolean expression over evidence presence (does a dx code exist, is an oral agent on file, is insulin on file, were labs abnormal, was glucose ever drawn). "Does a PheKB path close on this evidence?" is a question about the evidence's sufficiency, not about the patient's status.

| bucket | T2D count | labeler |
| --- | --- | --- |
| `DECISIVE_POS` | 314 | rules |
| `DECISIVE_NEG` | 536 | rules |
| `CONFLICTING` | **68** | LLM |
| `INDIRECT` | 1285 | rules |
| `NO_EVIDENCE` | 1336 | rules |

`CONFLICTING` is exactly the dx-coded patients where no path closes — the headroom set. `run.py` asserts it is 68.

### Two run modes, and why the second exists

- **cascade** (default): LLM sees only the 68. Caps F1 around 0.91, below three existing submissions.
- **full cohort** (`--all`): every patient to the LLM. The goal here is *not* F1 — it is **measured cost and latency for a per-patient agentic method, plus divergence from the rules**. Since every existing submission reports `cost_usd = 0`, that measurement is the contribution.

### Anti-silent-success rules

A 3539-call run has many ways to produce a plausible result that means nothing. These are load-bearing, not decoration:

- **Fallbacks are not agreement.** When the API fails, the patient falls back to its rule label — logged per patient, counted, and reported at the *top* of `RESULTS.md`. Above a 5% fallback rate the run stops and writes `FAILURES.md` instead of a submission, because a run that quietly falls back for 800 patients looks like a result and is not.
- **Preflight before bulk.** One live API call proves the key and model string; a 401 or bad model stops the run instead of retrying 3539 times.
- **Zero divergence is a headline, not a footnote.** If the LLM never disagrees with the rules, `RESULTS.md` says so at the top — it means the run bought nothing.
- **Chart format is the control variable.** `diagnostic_reports.csv` (clinical notes) is present but `render_chart()` does **not** include notes by default. Turning them on changes token counts and makes runs non-comparable — do it as a deliberate, separate experiment.
- Prompt caching is enabled on the system prompt, which is identical across calls. It is ~300 tokens against a 1024-token minimum, so **it caches nothing**; measured cache tokens are reported rather than a saving being assumed.

## Reference

Kho AN et al., *Use of diverse electronic medical record systems to identify genetic risk for type 2 diabetes within a genome-wide association study.* PheKB T2DM algorithm (eMERGE).
