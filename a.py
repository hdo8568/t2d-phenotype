import pandas as pd

# Load the frozen rule-based baseline. This is our reference cohort —
# phenotype.py produced it, we never recompute it here, only read it.
per = pd.read_csv("t2d_cohort.csv")
conditions_raw = pd.read_csv("conditions.csv")
conditions_raw["CODE"] = conditions_raw["CODE"].astype(str)
careplans_raw = pd.read_csv("careplans.csv")


# The middle = patients the rules could not call either way:
# not a case (status UNKNOWN) AND not a control (control False).
middle = per[(per["status"] == "UNKNOWN") & (~per["control"])]

print("total patients:", len(per))
print("middle:", len(middle))
print("\n")








# Split the middle by presence of a diabetes-adjacent code.
# dm_broad_count counts distinct dates with ANY diabetes-flavored code.
#   A = has a code (dm_broad_count > 0): mostly coded prediabetics.
#       The code makes LLM "cheating" possible -> later masking experiment.
#   B = no code at all (dm_broad_count == 0): the clean test.
#       Nothing to read off the chart, so the LLM must reason from evidence.
subgroup_A = middle[middle["dm_broad_count"] > 0]
subgroup_B = middle[middle["dm_broad_count"] == 0]

print("subgroup A (coded):  ", len(subgroup_A))
print("subgroup B (no code):", len(subgroup_B))
print("A + B:", len(subgroup_A) + len(subgroup_B))
print("\n")
print("\n")








# Debug sample: 10 patients from subgroup B, fixed seed for reproducibility.
# Goal of this small draw is ONLY to prove the LLM pipeline runs end to end
# and its output parses. We scale to all 1336 of B only after that works.
SEED = 42
sample_B = subgroup_B.sample(n=10, random_state=SEED)

print("sample_B drawn:", len(sample_B), "patients (seed", SEED, ")")
print(sample_B["Id"].tolist())

print("\n")
print("\n")











# ----------------------------------------------------------------
# Section 4: build a readable chart for ONE patient from raw files.
# The 15-column table only gave us IDs. The actual lab values / meds
# live in the raw CSVs, so we load those and carve out one patient
# at a time. Reuses the SAME code lists the rules keyed on.
# ----------------------------------------------------------------

# Code lists — identical to phenotype.py so the LLM sees the same evidence.
A1C     = ["4548-4"]
GLUCOSE = ["2339-0", "2345-7"]
T2D_MED = ["860975", "897122", "1373463"]
INSULIN = ["106892", "865098"]

# Load raw source files. These are big; we filter per-patient below.
patients_raw     = pd.read_csv("patients.csv")
observations_raw = pd.read_csv("observations.csv")
medications_raw  = pd.read_csv("medications.csv")
observations_raw["CODE"] = observations_raw["CODE"].astype(str)
medications_raw["CODE"]  = medications_raw["CODE"].astype(str)



















# --- condition code lists for the chart filter ---
METABOLIC_RISK = [
    "162864005",  # Body mass index 30+ - obesity (finding)
    "408512008",  # Body mass index 40+ - severely obese (finding)
    "55822004",   # Hyperlipidemia
    "59621000",   # Hypertension
    "302870006",  # Hypertriglyceridemia (disorder)
    "237602007",  # Metabolic syndrome X (disorder)
    "53741008",   # Coronary Heart Disease
    "230690007",  # Stroke
]
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




















def summarize_numeric(pid, description):
    rows = observations_raw[(observations_raw["PATIENT"] == pid)
                            & (observations_raw["DESCRIPTION"] == description)].sort_values("DATE")
    if not len(rows):
        return "none"
    vals = pd.to_numeric(rows["VALUE"], errors="coerce").dropna()
    if not len(vals):
        return "none"
    units = "" if pd.isna(rows.iloc[-1]["UNITS"]) else f" {rows.iloc[-1]['UNITS']}"
    first_d, last_d = rows.iloc[0]["DATE"][:10], rows.iloc[-1]["DATE"][:10]
    f, l, lo, hi = vals.iloc[0], vals.iloc[-1], vals.min(), vals.max()
    if lo == hi:                       # never changed
        return f"{l}{units} (stable, n={len(vals)}, {first_d}–{last_d})"
    return (f"{l}{units} latest ({last_d}); "
            f"first {f} ({first_d}); range {lo}–{hi}; n={len(vals)}")


def summarize_smoking(pid):
    rows = observations_raw[(observations_raw["PATIENT"] == pid)
                            & (observations_raw["DESCRIPTION"] == "Tobacco smoking status NHIS")].sort_values("DATE")
    if not len(rows):
        return "none"
    statuses = rows["VALUE"].tolist()
    latest = statuses[-1]
    if len(set(statuses)) == 1:
        return latest
    return f"{latest} (changed over time: {statuses[0]} → {latest})"












def build_chart(pid, mask=False):
    lines = []

    # --- demographics ---
    prow = patients_raw[patients_raw["Id"] == pid].iloc[0]
    birth = pd.to_datetime(prow["BIRTHDATE"])
    age = int((pd.Timestamp("2020-01-01") - birth).days / 365.25)
    lines.append(f"Patient: {age}-year-old {prow['GENDER']}")

    # --- A1c (all readings; "none" when absent) ---
    a1c = observations_raw[(observations_raw["PATIENT"] == pid)
                           & (observations_raw["CODE"].isin(A1C))]
    lines.append("A1c results:")
    if len(a1c):
        for _, r in a1c.iterrows():
            lines.append(f"  {r['DATE']}: {r['VALUE']}")
    else:
        lines.append("  none")

    # --- glucose ---
    glu = observations_raw[(observations_raw["PATIENT"] == pid)
                           & (observations_raw["CODE"].isin(GLUCOSE))]
    lines.append("Glucose results:")
    if len(glu):
        for _, r in glu.iterrows():
            lines.append(f"  {r['DATE']}: {r['VALUE']}")
    else:
        lines.append("  none")

    # --- diabetes meds ---
    meds = medications_raw[(medications_raw["PATIENT"] == pid)
                           & (medications_raw["CODE"].isin(T2D_MED + INSULIN))]
    lines.append("Diabetes-related medications:")
    if len(meds):
        for _, r in meds.iterrows():
            lines.append(f"  {r['START']}: {r['DESCRIPTION']}")
    else:
        lines.append("  none")

    # --- metabolic observations (summarized: latest + trajectory) ---
    lines.append("Metabolic observations:")
    numeric_fields = [
        ("BMI",               "Body Mass Index"),
        ("Systolic BP",       "Systolic Blood Pressure"),
        ("Diastolic BP",      "Diastolic Blood Pressure"),
        ("Total cholesterol", "Total Cholesterol"),
        ("Triglycerides",     "Triglycerides"),
        ("LDL",               "Low Density Lipoprotein Cholesterol"),
        ("HDL",               "High Density Lipoprotein Cholesterol"),
    ]
    for label, desc in numeric_fields:
        lines.append(f"  {label}: {summarize_numeric(pid, desc)}")
    lines.append(f"  Smoking status: {summarize_smoking(pid)}")

    # --- conditions: metabolic always shown; diabetes-adjacent only if not masked ---
    cond = conditions_raw[conditions_raw["PATIENT"] == pid]
    shown = cond[cond["CODE"].isin(METABOLIC_RISK)]["DESCRIPTION"].unique().tolist()
    if not mask:
        shown += cond[cond["CODE"].isin(DM_DX_BROAD)]["DESCRIPTION"].unique().tolist()
    lines.append("Relevant conditions:")
    if shown:
        for d in shown:
            lines.append(f"  {d}")
    else:
        lines.append("  none")

    # --- care plans: diabetes-named plans are a second leak channel, maskable ---
    plans = careplans_raw[(careplans_raw["PATIENT"] == pid)
                          & careplans_raw["DESCRIPTION"].str.contains("diabet", case=False, na=False)]
    shown_plans = [] if mask else plans["DESCRIPTION"].unique().tolist()
    lines.append("Care plans:")
    if shown_plans:
        for d in shown_plans:
            lines.append(f"  {d}")
    else:
        lines.append("  none")

    return "\n".join(lines)






















# Smoke test: build and print the chart for the FIRST sampled patient.
first_id = sample_B["Id"].iloc[0]
print("\n===== CHART FOR ONE PATIENT =====")
print(build_chart(first_id))


print("\n")
print("\n")


print("\n===== ALL 10 SAMPLED CHARTS =====")
for pid in sample_B["Id"]:
    print("\n" + build_chart(pid))

print("\n")
print("\n")
print("\n")
print("\n")

# Sanity: build a chart for a KNOWN case (must have labs if builder works)
known_case_id = per[per["status"] == "CASE"]["Id"].iloc[0]
print("\n===== KNOWN CASE CHART (builder sanity check) =====")
print(build_chart(known_case_id))



print("\n")
print("\n")
print("\n")
print("\n")


# How much of subgroup B has ANY lab/med evidence vs is data-silent?
obs_pts = set(observations_raw[observations_raw["CODE"].isin(A1C + GLUCOSE)]["PATIENT"])
med_pts = set(medications_raw[medications_raw["CODE"].isin(T2D_MED + INSULIN)]["PATIENT"])
has_evidence = obs_pts | med_pts

b_ids = set(subgroup_B["Id"])
b_with_evidence = b_ids & has_evidence
print("\nsubgroup B total:", len(b_ids))
print("B with any lab/med evidence:", len(b_with_evidence))
print("B data-silent (empty):", len(b_ids) - len(b_with_evidence))


test_id = sample_B["Id"].iloc[0]   # the 31-year-old F who looked empty

print("\n===== ALL conditions for this B patient =====")
print(conditions_raw[conditions_raw["PATIENT"] == test_id]["DESCRIPTION"].tolist())

print("\n===== ALL observation types for this B patient =====")
obs_this = observations_raw[observations_raw["PATIENT"] == test_id]
print(obs_this["DESCRIPTION"].value_counts().to_string())

bmi_pts = set(observations_raw[observations_raw["DESCRIPTION"] == "Body Mass Index"]["PATIENT"])
b_with_bmi = b_ids & bmi_pts
print("B total:", len(b_ids))
print("B with BMI recorded:", len(b_with_bmi))
print("B without BMI:", len(b_ids) - len(b_with_bmi))



























# GATE: do any B patients have a diabetes-named care plan? Predicted 0.
# If nonzero, those are uncoded diabetics — a care plan implies a diagnosis
# in Synthea, so a B patient with one means the code that should exist is missing.
dm_plans = careplans_raw[careplans_raw["DESCRIPTION"].str.contains("diabet", case=False, na=False)]
b_with_dm_plan = b_ids & set(dm_plans["PATIENT"])
print("\nB patients with a diabetes-named care plan (predicted 0):", len(b_with_dm_plan))


































SYSTEM_PROMPT = """You are a clinical reviewer assessing whether a patient shows evidence of type 2 diabetes (T2D) or emerging T2D risk, based on a structured chart summary.

This patient has NO diabetes diagnosis code and NO diabetes-specific labs or medications on record. Your job is NOT to find a diagnosis that was already made. It is to reason from the INDIRECT metabolic evidence — BMI, blood pressure, lipids, smoking, and related conditions — and judge which of the following best fits:

- "case": the metabolic picture is strongly consistent with undiagnosed or emerging T2D (e.g. obesity plus dyslipidemia plus hypertension, a metabolic-syndrome pattern, especially if worsening over time). You are flagging this person as someone a clinician should screen for diabetes.
- "control": the metabolic picture is reassuring. Normal or near-normal BMI, BP, and lipids, no metabolic comorbidities, no concerning trajectory. This person looks metabolically healthy.
- "unsure": the evidence is mixed, borderline, or too sparse to support either call. This includes patients with little or no metabolic data, and patients with some risk factors but not a coherent picture.

Important guidance:
- Absence of evidence is not evidence of health. If the chart is largely empty, prefer "unsure", not "control".
- Do not invent values or findings not present in the chart. Base your judgment only on what is shown.
- A single mildly abnormal value is weak evidence. Look for a coherent pattern and, where readings span time, the direction of change.
- Reason about THIS patient's actual numbers, not population base rates.

Respond with ONLY a single JSON object, no other text, in exactly this form:
{"label": "case" | "control" | "unsure", "justification": "<one sentence citing the specific evidence that drove the call>"}"""








import json
import os
from dotenv import load_dotenv
from google import genai
import time
load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))




def classify(pid, mask=False, retries=4):
    chart = build_chart(pid, mask=mask)
    prompt = SYSTEM_PROMPT + "\n\nPATIENT CHART:\n" + chart
    for attempt in range(retries):
        try:
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            raw = resp.text.strip().replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw)
            return {"pid": pid, "label": parsed["label"],
                    "justification": parsed["justification"]}
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e) or "429" in str(e):
                time.sleep(2 ** attempt)   # 1, 2, 4, 8s backoff
                continue
            return {"pid": pid, "label": "PARSE_ERROR", "justification": str(e)}
    return {"pid": pid, "label": "RETRY_EXHAUSTED", "justification": "503/429 after retries"}











print("\n===== CLASSIFIER — DEBUG 10 (subgroup B) =====")
for pid in sample_B["Id"]:
    result = classify(pid)
    print(f"\n[{result['label']}] {pid[:8]}")
    print(f"  {result['justification']}")