t2d-phenotype

A rule-based implementation of the PheKB Type 2 Diabetes Mellitus phenotype (Kho et al., eMERGE) run against the Coherent synthetic EHR dataset (Synthea-style CSV exports).

The output is a labeled patient table (t2d_cohort.csv) assigning each patient CASE, CONTROL, or neither ("middle"). This cohort is intended as the rule-based baseline that LLM-based phenotyping approaches are evaluated against — so the code deliberately includes an audit layer that interrogates whether the baseline is trustworthy, rather than just producing a number.


Data

Expects the following CSVs in the working directory:

FileUsed forpatients.csvpatient roster (Id, BIRTHDATE)conditions.csvSNOMED diagnosis codes (PATIENT, CODE, DESCRIPTION, START)medications.csvRxNorm medication codesobservations.csvLOINC labs (A1c, glucose) with VALUEencounters.csvENCOUNTERCLASS, used for office-visit countssupplies.csvprobed only — empty in Coherent, so the PheKB supplies criterion is dropped

Data files are not committed (see .gitignore).

Requirements

python 3.x
pandas

Usage

bashpython probe.py        # inspect encounters.csv / supplies.csv structure
python broad_codes.py  # enumerate diabetes-adjacent SNOMED codes + patient counts
python provenance.py   # check patient-ID overlap between patients.csv and encounters.csv
python phenotype.py    # main: build facts, classify cases + controls, write t2d_cohort.csv


Files

phenotype.py — main pipeline

Five stages:


Load the four core tables; coerce CODE to string.
Code lists. T2D diagnoses, T1D diagnoses, T2D medications (metformin, liraglutide, canagliflozin), insulin, and lab codes with thresholds (A1c ≥ 6.5, random glucose > 200).
Per-patient facts. t1dm_dx_count, t2dm_dx_count, physician_dx_count, t2dm_med_date (earliest), insulin_date (earliest), abnormal_lab.
Case classification. classify() implements the five PheKB T2DM-CASE-SELECTION paths line for line; all five are gated on t1dm_dx_count == 0. First match wins.
Control classification. is_control() implements PheKB Algorithm 8: no broad-DM diagnosis, glucose lab drawn, clean labs at looser thresholds (A1c ≥ 6.0 / glucose > 110), ≥ 2 office visits, no DM medication.


Also writes t2d_cohort.csv and prints an EDA / audit block:


cases per path (P1–P5),
age sanity check on flagged cases (a diabetic child = a bug),
per-code patient counts flagging zero and near-zero codes (a code that matches nobody is either absent from the vocabulary or wrong),
dropped dx-coded patients: patients with a T2D diagnosis who nonetheless fall out as UNKNOWN, with a breakdown of why.


broad_codes.py

Text-searches conditions.DESCRIPTION for diabetes-adjacent terms and reports every matching code with its patient count. Used to construct DM_DX_BROAD, the control-exclusion list.

probe.py

Data-availability probe: what ENCOUNTERCLASS values exist, and whether supplies.csv has any rows.

provenance.py

Sanity check that encounters.csv patient IDs are a subset of patients.csv IDs.


Coherent-specific adaptations

The PheKB algorithm assumes a real EHR. Coherent doesn't have everything, so the following deviations are deliberate and documented in-code:


No Type 1 diabetes patients exist in Coherent. The T1D exclusion gate therefore never fires. It is retained as a correctness check (expected count: 0), not as a working filter.
No billing stream. Every condition arrives through an encounter, so physician_dx_count == t2dm_dx_count.
supplies.csv is empty, so the Table 8 supplies criterion in the control algorithm is omitted.
No family-history coding, so the control fam_hist == False condition passes vacuously for everyone.
No fasting-glucose distinction, so control abnormality is defined on random glucose and A1c only.
The generic SNOMED code 44054006 ("Diabetes") is treated as T2D.
DM_DX_BROAD excludes 386806002 (impaired cognition) — a false hit from the text search, not glucose-related.


Known limitations


Case paths are evaluated in order and the first match wins; the path breakdown is descriptive, not a partition of independent criteria.
Patients with a T2D diagnosis who are dropped to UNKNOWN are mostly dropped because they are on insulin. Whether that is a correct clinical exclusion or an artifact of a T1D gate that does no work in this dataset is an open question — and precisely the kind of case where an LLM adjudicator would likely disagree with the rule.
Ages are computed against a fixed reference date (2020-01-01), not the diagnosis date.



Paper I used for algorithm:
Kho AN et al., Use of diverse electronic medical record systems to identify genetic risk for type 2 diabetes within a genome-wide association study. PheKB T2DM algorithm (eMERGE).
