import pandas as pd

patients     = pd.read_csv("patients.csv")
conditions   = pd.read_csv("conditions.csv")
medications  = pd.read_csv("medications.csv")
observations = pd.read_csv("observations.csv")
conditions["CODE"]   = conditions["CODE"].astype(str)
medications["CODE"]  = medications["CODE"].astype(str)
observations["CODE"] = observations["CODE"].astype(str)
# .shape gives (rows, columns). Printing it proves each table loaded
print("\n")
print("\n")
print("patients:    ", patients.shape)
print("conditions:  ", conditions.shape)
print("medications: ", medications.shape)
print("observations:", observations.shape)
print("\n")
print("\n")
#Step 2 "sets up" step 3
# Stage 2: code lists. Each bucket from our reference table becomes
# one list. These are the filters every algorithm step will use.

# --- Diagnosis codes (SNOMED), used to count diagnosis dates ---
#conditions.csv
T2D_DX = [
    "44054006",         # Diabetes (generic; kept as T2D per our decision)
    "368581000119106",  # Neuropathy due to type 2 DM
    "422034002",        # Diabetic retinopathy, type 2
    "1551000119108",    # Nonproliferative retinopathy, type 2
    "90781000119102",   # Microalbuminuria due to type 2 DM
    "97331000119101",   # Macular edema + retinopathy, type 2
    "1501000119109",    # Proliferative retinopathy, type 2
    "60951000119105",   # Blindness due to type 2 DM
    "157141000119108",  # Proteinuria due to type 2 DM
]
#conditions.csv
T1D_DX = [
    "46635009",         # Type 1 DM (absent in Coherent; count will be 0)
]
#medications.csv
# --- Medication codes (RxNorm) ---
T2D_MED = [
    "860975",   # Metformin ER 500mg
    "897122",   # liraglutide (GLP-1)
    "1373463",  # canagliflozin (SGLT2)
]
#medications.csv
INSULIN = [          # the "T1D medication" bucket: insulin (+ Symlin, absent)
    "106892",   # Humulin
    "865098",   # Insulin Lispro [Humalog]
]

#observations.csv
# --- Lab codes (LOINC) and their abnormal thresholds ---
A1C = ["4548-4"]              # Hemoglobin A1c, %     -> abnormal if >= 6.5
GLUCOSE = ["2339-0", "2345-7"]  # blood glucose, mg/dL -> abnormal if > 200
#These codes do not indicate test status -- just indicates whether patient has done test
#Later, we will make a new table filtering for these codes, then a new table after that filtering
#which values associated with the patietn ode is indeed over the threshold
#CODE is the field we test, then the VALUE field tells the actual number the patient got
A1C_THRESHOLD = 6.5
GLUCOSE_THRESHOLD = 200

# Confirm the lists loaded by printing how many codes are in each.
print("T2D_DX codes:  ", len(T2D_DX))
print("T1D_DX codes:  ", len(T1D_DX))
print("T2D_MED codes: ", len(T2D_MED))
print("INSULIN codes: ", len(INSULIN))
print("A1C / GLUCOSE: ", len(A1C), "/", len(GLUCOSE))





















# Stage 3: per-patient facts. We compute one fact at a time and build
# up a per-patient table. Starting with t1dm_dx_count — distinct dates
# a patient has a T1D diagnosis. We expect every patient to be 0,
# since Coherent has no T1D, so this doubles as a correctness check.

# Convert the condition START column from text to real dates now, so
# date comparisons later are chronological, not alphabetical.
conditions["START"] = pd.to_datetime(conditions["START"])

# Step 1 - FILTER: keep only condition rows whose code is a T1D code.
# .isin(LIST) tests each row's CODE against the list, giving True/False;
# conditions[...] keeps only the True rows.
t1d_rows = conditions[conditions["CODE"].isin(T1D_DX)]

# Step 2+3 - GROUP BY PATIENT, then COUNT DISTINCT dates within each.
# groupby("PATIENT") splits the rows into one bucket per patient;
# ["START"].nunique() counts the distinct dates in each bucket.
t1dm_dx_count = t1d_rows.groupby("PATIENT")["START"].nunique()
#.groupby("PATIENT") piles the remaining rows into one "bucket" or "stack"
# per patient. So the 


# Patients with zero T1D rows won't appear above at all (they had no
# matching rows to group). That's fine — absence means 0. Show how many
# patients DID get a nonzero count; we expect this to be 0.
print("patients with any T1D dx:", len(t1dm_dx_count))








medications["START"] = pd.to_datetime(medications["START"])
# Fact #3: t2dm_med_date — earliest T2D medication date per patient.
t2d_med_rows = medications[medications["CODE"].isin(T2D_MED)]
t2dm_med_date = t2d_med_rows.groupby("PATIENT")["START"].min()

print("patients with any T2D med:", len(t2dm_med_date))











# Fact #2: t2dm_dx_count — distinct dates with a T2D diagnosis.
t2dm_dx_count = conditions[conditions["CODE"].isin(T2D_DX)].groupby("PATIENT")["START"].nunique()

# Fact #4: insulin_date — earliest insulin date. Same shape as the T2D med line.
insulin_date = medications[medications["CODE"].isin(INSULIN)].groupby("PATIENT")["START"].min()

# Fact #5: abnormal_lab — does the patient have ANY A1c >= 6.5 OR glucose > 200.
# observations VALUE is TEXT ('5.9'), so convert to numbers before comparing.
# errors="coerce" turns any non-numeric junk into NaN, which fails the test safely.
a1c = observations[observations["CODE"].isin(A1C)].copy()
a1c["VALUE"] = pd.to_numeric(a1c["VALUE"], errors="coerce")
a1c_pts = a1c[a1c["VALUE"] >= A1C_THRESHOLD]["PATIENT"].unique()

glu = observations[observations["CODE"].isin(GLUCOSE)].copy()
glu["VALUE"] = pd.to_numeric(glu["VALUE"], errors="coerce")
glu_pts = glu[glu["VALUE"] > GLUCOSE_THRESHOLD]["PATIENT"].unique()

abnormal_pts = set(a1c_pts) | set(glu_pts)   # union: in either list = abnormal

# Fact #6: physician_dx_count — clinician-entered T2D dx dates. In Coherent every
# condition comes through an encounter (no billing stream), so this equals fact #2.
physician_dx_count = t2dm_dx_count















# --- ASSEMBLE: one row per patient, six fact columns ---
per = pd.DataFrame(index=patients["Id"])
per["t1dm_dx_count"]      = t1dm_dx_count
per["t2dm_dx_count"]      = t2dm_dx_count
per["physician_dx_count"] = physician_dx_count
per["t2dm_med_date"]      = t2dm_med_date
per["insulin_date"]       = insulin_date
per["abnormal_lab"]       = per.index.isin(abnormal_pts)
for c in ("t1dm_dx_count", "t2dm_dx_count", "physician_dx_count"):
    per[c] = per[c].fillna(0).astype(int)

print("per-patient table rows:", len(per))
print("  T2D dx > 0:", (per["t2dm_dx_count"] > 0).sum())
print("  on T2D med:", per["t2dm_med_date"].notna().sum())
print("  on insulin:", per["insulin_date"].notna().sum())
print("  abnormal lab:", per["abnormal_lab"].sum())
print("\n")
print("\n")



















# Stage 4: apply the five case paths to each patient.
# We write a function that takes one patient's row of facts and returns
# "CASE" or "UNKNOWN". This mirrors T2DM-CASE-SELECTION in the pseudocode,
# line for line — read each path against the algorithm image.

def classify(p):
    no_t1d   = p["t1dm_dx_count"] == 0          # the exclusion gate, top of the flowchart
    has_t2d  = p["t2dm_dx_count"] > 0
    on_med   = pd.notna(p["t2dm_med_date"])     # T2DM-RX-DT != NULL
    on_insln = pd.notna(p["insulin_date"])      # T1DM-RX-DT != NULL

    # Path 1: no T1D dx, has T2D dx, on T2D med, on insulin, T2D med BEFORE insulin
    if no_t1d and has_t2d and on_med and on_insln and p["t2dm_med_date"] < p["insulin_date"]:
        return "CASE"
    # Path 2: no T1D dx, has T2D dx, NOT on insulin, on T2D med
    if no_t1d and has_t2d and not on_insln and on_med:
        return "CASE"
    # Path 3: no T1D dx, has T2D dx, no insulin, no T2D med, abnormal lab
    if no_t1d and has_t2d and not on_insln and not on_med and p["abnormal_lab"]:
        return "CASE"
    # Path 4: no T1D dx, NO T2D dx, on T2D med, abnormal lab
    if no_t1d and not has_t2d and on_med and p["abnormal_lab"]:
        return "CASE"
    # Path 5: no T1D dx, has T2D dx, on insulin, NOT on T2D med, >= 2 clinician dx dates
    if no_t1d and has_t2d and on_insln and not on_med and p["physician_dx_count"] >= 2:
        return "CASE"
    return "UNKNOWN"

# Run classify on every patient row; store the label in a new column.
per["status"] = per.apply(classify, axis=1)

# Stage 5 preview: how many cases, and what prevalence.
n_cases = (per["status"] == "CASE").sum()
print("T2D cases:", n_cases)
print("prevalence: {:.1%}".format(n_cases / len(per)))

print("\n")
print("\n")







# Stage 5: write the cohort to a file, and spot-check a few flagged patients.

# Save the full labeled table (every patient + their status) to CSV, so the
# cohort is a real deliverable file, not just a number on screen.
per.to_csv("t2d_cohort.csv")
print("\nwrote t2d_cohort.csv  (", len(per), "patients,",
      (per["status"]=="CASE").sum(), "cases )")

# Spot-check: show the facts for the first 5 patients flagged as CASE.
# Eyeball that they actually have the diagnosis/med/lab signals you'd expect.
cases = per[per["status"]=="CASE"]
print("\nfirst 5 flagged cases (their facts):")
print(cases[["t2dm_dx_count","t2dm_med_date","insulin_date","abnormal_lab"]].head())






























print("\n")
print("\n")

# ============================================================
# EDA + DATA-AVAILABILITY AUDIT
# ============================================================

# --- which_path: same logic as classify(), but records WHICH path
# --- fired instead of just CASE/UNKNOWN. Order must match classify()
# --- exactly — first match wins. This lets us see the path breakdown.
def which_path(p):
    no_t1d   = p["t1dm_dx_count"] == 0
    has_t2d  = p["t2dm_dx_count"] > 0
    on_med   = pd.notna(p["t2dm_med_date"])
    on_insln = pd.notna(p["insulin_date"])
    if no_t1d and has_t2d and on_med and on_insln and p["t2dm_med_date"] < p["insulin_date"]:
        return "P1"
    if no_t1d and has_t2d and not on_insln and on_med:
        return "P2"
    if no_t1d and has_t2d and not on_insln and not on_med and p["abnormal_lab"]:
        return "P3"
    if no_t1d and not has_t2d and on_med and p["abnormal_lab"]:
        return "P4"
    if no_t1d and has_t2d and on_insln and not on_med and p["physician_dx_count"] >= 2:
        return "P5"
    return "UNKNOWN"

per["path"] = per.apply(which_path, axis=1)
cases = per[per["path"] != "UNKNOWN"]

# --- (1) cases per path: the headline EDA output ---
print("\n===== EDA =====")
print("cases:", len(cases), "| prevalence: {:.1%}".format(len(cases)/len(per)))
print("cases per path:")
print(cases["path"].value_counts().sort_index().to_string())
print("\n")
print("\n")
# --- (2) age sanity: a diabetic child = a bug. BIRTHDATE is tz-naive,
# --- so use a tz-naive reference date or the subtraction errors out. ---
pts = patients.set_index("Id").copy()
pts["BIRTHDATE"] = pd.to_datetime(pts["BIRTHDATE"])
case_ages = (pd.Timestamp("2020-01-01") - pts.loc[cases.index, "BIRTHDATE"]).dt.days / 365.25
print("\ncase age — min {:.0f} / median {:.0f} / max {:.0f} | under 18: {}".format(
      case_ages.min(), case_ages.median(), case_ages.max(), int((case_ages < 18).sum())))
print("\n")
print("\n")
# --- (3) code-level audit: count patients per INDIVIDUAL code.
# --- A zero means the code is absent OR wrong (typo/wrong vocabulary).
# --- A near-zero means the code is present but inert (doing no real work). ---
def code_audit(label, codes, table):
    print(f"\n{label}:")
    for c in codes:
        n = table[table["CODE"] == c]["PATIENT"].nunique()
        flag = "   <-- ZERO" if n == 0 else ("   <-- near-zero" if n <= 2 else "")
        print(f"  {c:<18} {n:>5} patients{flag}")

code_audit("T2D_DX (conditions)",  T2D_DX,  conditions)
code_audit("T1D_DX (conditions)",  T1D_DX,  conditions)   # expect 0 — intended exclusion
code_audit("T2D_MED (medications)",T2D_MED, medications)
code_audit("INSULIN (medications)",INSULIN, medications)
code_audit("A1C (observations)",   A1C,     observations)
code_audit("GLUCOSE (observations)",GLUCOSE,observations)







missed = per[(per["t2dm_dx_count"] > 0) & (per["path"] == "UNKNOWN")]
print("dropped dx-coded patients:", len(missed))
print("  all on insulin:", missed["insulin_date"].notna().sum(), "of", len(missed))
print("  with dx_count >= 2:", (missed["t2dm_dx_count"] >= 2).sum())
##We are doing this because we want to see whether the rule-based cohort is
##trustworthy enough to be the baseline the LLM gets compared against
#This motivates the questinos:
#are those 68 corrrectly exluded for a proper clinical reason, or
#did the algorithm have a bug
#Based on our assessment, we see that most were dropped due to insulin.
#Furthermore, Coherent had zero type-1 pateints, so the exlusion guard
#seems to be something that doesn't apply in our dataset.
#I would suspect that an LLM would diagnose these 67 individuals T2D.

















# ---- CONTROL ALGORITHM: data-availability probe ----
# Q1: does Coherent encode family history of diabetes? Search condition descriptions.
print("\n")
print("\n")
fh = conditions[conditions["DESCRIPTION"].str.contains("family history", case=False, na=False)]
print("family-history condition rows:", len(fh))
print(fh["DESCRIPTION"].value_counts().head(10).to_string() if len(fh) else "  (none)")
print("\n")
print("\n")
# Q2: prediabetes / impaired-glucose / gestational — the broad Table 9 categories.
# These must EXCLUDE people from controls. How prevalent are they?
for term in ["prediabet", "impaired", "gestational", "glycosuria", "screening for diabet"]:
    n = conditions[conditions["DESCRIPTION"].str.contains(term, case=False, na=False)]["PATIENT"].nunique()
    print(f"  '{term}': {n} patients")
print("\n")
print("\n")
# Q3: encounters — does encounters.csv have an office/outpatient type we can count?
enc = pd.read_csv("encounters.csv")
print("\nencounter columns:", list(enc.columns))
if "ENCOUNTERCLASS" in enc.columns:
    print(enc["ENCOUNTERCLASS"].value_counts().to_string())
print("\n")
print("\n")













# --- Broad DM diagnosis codes (SNOMED) for CONTROL exclusion (PheKB Table 9).
# --- Any of these disqualifies a patient from being a clean control.
# --- Narrower than Table 9: gestational/glycosuria/screening absent in Coherent.
# --- Excludes 386806002 (impaired cognition) — false hit from text search, not glucose-related.
DM_DX_BROAD = [
    "15777000",         # Prediabetes
    "44054006",         # Diabetes
    "127013003",        # Diabetic renal disease
    "80394007",         # Hyperglycemia
    "368581000119106",  # Neuropathy due to T2DM
    "422034002",        # Diabetic retinopathy, T2
    "1551000119108",    # Nonproliferative retinopathy, T2
    "90781000119102",   # Microalbuminuria due to T2DM
    "97331000119101",   # Macular edema + retinopathy, T2
    "1501000119109",    # Proliferative retinopathy, T2
    "157141000119108",  # Proteinuria due to T2DM
    "60951000119105",   # Blindness due to T2DM
    "427089005",        # Diabetes from Cystic Fibrosis
]












# ============================================================
# CONTROL ALGORITHM (PheKB Algorithm 8). One path, six conditions,
# ALL must be true. Logic: prove the patient is clearly NOT diabetic.
# Adjusted for Coherent: supplies empty, family-history absent (both noted).
# ============================================================

# Load encounters (new file). supplies.csv is empty (0 rows) so we skip it.
encounters = pd.read_csv("encounters.csv")
encounters["CODE"] = encounters["CODE"].astype(str)  # harmless, keeps types consistent

# --- Condition 1: dm_dx_broad_count == 0 (broad Table 9 list) ---
# Distinct dates with ANY diabetes-related dx. Must be zero for a control.
dm_broad_count = (conditions[conditions["CODE"].isin(DM_DX_BROAD)]
                  .groupby("PATIENT")["START"].nunique())

# --- Condition 2: glucose_lab_exists == True ---
# Patient must have had at least one glucose lab drawn (proves they were screened).
glucose_drawn = set(observations[observations["CODE"].isin(GLUCOSE)]["PATIENT"].unique())

# --- Condition 3: abnormal_lab_control == False (LOOSER thresholds) ---
# Control abnormal = random glucose >110 OR A1c >=6.0 (vs case 200 / 6.5).
# Fasting still unavailable in Coherent. Reuse a1c/glu frames already numeric-coerced.
glu_ctrl = observations[observations["CODE"].isin(GLUCOSE)].copy()
glu_ctrl["VALUE"] = pd.to_numeric(glu_ctrl["VALUE"], errors="coerce")
a1c_ctrl = observations[observations["CODE"].isin(A1C)].copy()
a1c_ctrl["VALUE"] = pd.to_numeric(a1c_ctrl["VALUE"], errors="coerce")
ctrl_abnormal_pts = (set(glu_ctrl[glu_ctrl["VALUE"] > 110]["PATIENT"])
                     | set(a1c_ctrl[a1c_ctrl["VALUE"] >= 6.0]["PATIENT"]))

# --- Condition 4: office_visit_count >= 2 ---
# Distinct dates of in-person clinic visits. Your chosen classes only.
OFFICE_CLASSES = ["ambulatory", "wellness", "outpatient"]
encounters["START"] = pd.to_datetime(encounters["START"])
office = encounters[encounters["ENCOUNTERCLASS"].isin(OFFICE_CLASSES)]
office_visit_count = office.groupby("PATIENT")["START"].dt.date.nunique() \
    if False else office.groupby("PATIENT")["START"].apply(lambda s: s.dt.date.nunique())

# --- Condition 5: dm_meds_count == 0 (supplies empty, so meds only) ---
# Any T2D oral OR insulin disqualifies. Table 8 supplies dead -> omitted.
dm_med_pts = set(medications[medications["CODE"].isin(T2D_MED + INSULIN)]["PATIENT"].unique())

# --- Condition 6: fam_hist == False ---
# No family-history data in Coherent -> defaults False for everyone (no filtering).

# --- ASSEMBLE control facts onto the per-patient table ---
per["dm_broad_count"]    = dm_broad_count
per["dm_broad_count"]    = per["dm_broad_count"].fillna(0).astype(int)
per["glucose_drawn"]     = per.index.isin(glucose_drawn)
per["ctrl_abnormal_lab"] = per.index.isin(ctrl_abnormal_pts)
per["office_visits"]     = office_visit_count
per["office_visits"]     = per["office_visits"].fillna(0).astype(int)
per["on_dm_med"]         = per.index.isin(dm_med_pts)

def is_control(p):
    return (p["dm_broad_count"] == 0          # cond 1: no diabetes-related dx
            and p["glucose_drawn"]            # cond 2: glucose was measured
            and not p["ctrl_abnormal_lab"]    # cond 3: clean at loose thresholds
            and p["office_visits"] >= 2       # cond 4: regular outpatient
            and not p["on_dm_med"]            # cond 5: no DM meds (supplies empty)
            # cond 6: family history always False -> always passes
            )

per["control"] = per.apply(is_control, axis=1)

# --- REPORT ---
n_ctrl = per["control"].sum()
n_case = (per["path"] != "UNKNOWN").sum()
n_mid  = len(per) - n_ctrl - n_case
print("\n===== CONTROL ALGORITHM =====")
print("cases:    ", n_case)
print("controls: ", n_ctrl)
print("middle:   ", n_mid, "({:.1%})".format(n_mid/len(per)))
print("total patients (cases + controls + middle) = ", len(per))
print("\ncontrol condition attrition (whole population):")
print("  dm_broad_count == 0:", (per["dm_broad_count"] == 0).sum())
print("  glucose drawn:      ", per["glucose_drawn"].sum())
print("  clean (loose) lab:  ", (~per["ctrl_abnormal_lab"]).sum())
print("  >=2 office visits:  ", (per["office_visits"] >= 2).sum())
print("  no DM med:          ", (~per["on_dm_med"]).sum())

# sanity: no patient should be both case and control
both = per[(per["path"] != "UNKNOWN") & per["control"]]
print("\npatients flagged BOTH case and control (must be 0):", len(both))