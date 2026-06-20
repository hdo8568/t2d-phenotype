import pandas as pd


# Stage 1: load the four CSVs and confirm each one reads.
# pd.read_csv opens a CSV and returns it as a DataFrame — a table
# you can filter and count. The string is the filename; because the
# script lives in the same folder as the data, no full path is needed.

patients     = pd.read_csv("patients.csv")
conditions   = pd.read_csv("conditions.csv")
medications  = pd.read_csv("medications.csv")
observations = pd.read_csv("observations.csv")


conditions["CODE"]   = conditions["CODE"].astype(str)
medications["CODE"]  = medications["CODE"].astype(str)
observations["CODE"] = observations["CODE"].astype(str)

# .shape gives (rows, columns). Printing it proves each table loaded
# and lets you eyeball the row counts against what we found earlier.
print("patients:    ", patients.shape)
print("conditions:  ", conditions.shape)
print("medications: ", medications.shape)
print("observations:", observations.shape)
#QUESTION: are patients, conditions, medications, and observations
#the primary tables we will be working with? It seems to be this way right now



#Step 2 "sets up" step 3
# Stage 2: code lists. Each bucket from our reference table becomes
# one list. These are the filters every algorithm step will use.

# --- Diagnosis codes (SNOMED), used to count diagnosis dates ---
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

T1D_DX = [
    "46635009",         # Type 1 DM (absent in Coherent; count will be 0)
]

# --- Medication codes (RxNorm) ---
T2D_MED = [
    "860975",   # Metformin ER 500mg
    "897122",   # liraglutide (GLP-1)
    "1373463",  # canagliflozin (SGLT2)
]

INSULIN = [          # the "T1D medication" bucket: insulin (+ Symlin, absent)
    "106892",   # Humulin
    "865098",   # Insulin Lispro [Humalog]
]

# --- Lab codes (LOINC) and their abnormal thresholds ---
A1C = ["4548-4"]              # Hemoglobin A1c, %     -> abnormal if >= 6.5
GLUCOSE = ["2339-0", "2345-7"]  # blood glucose, mg/dL -> abnormal if > 200

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

# --- (2) age sanity: a diabetic child = a bug. BIRTHDATE is tz-naive,
# --- so use a tz-naive reference date or the subtraction errors out. ---
pts = patients.set_index("Id").copy()
pts["BIRTHDATE"] = pd.to_datetime(pts["BIRTHDATE"])
case_ages = (pd.Timestamp("2020-01-01") - pts.loc[cases.index, "BIRTHDATE"]).dt.days / 365.25
print("\ncase age — min {:.0f} / median {:.0f} / max {:.0f} | under 18: {}".format(
      case_ages.min(), case_ages.median(), case_ages.max(), int((case_ages < 18).sum())))

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









