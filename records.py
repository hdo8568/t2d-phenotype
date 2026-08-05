# records.py — the shared, method-agnostic patient record builder.
#
# Every phenotype in this project (T2D now, Resistant Hypertension next) needs
# the same thing first: one self-contained object per patient holding everything
# we know about them. Nothing in here knows what a phenotype is. It does not
# compute facts, it does not apply thresholds, and it does not label anything.
# It just assembles.
#
# The one rule that matters here: THE SPINE IS patients.csv. Every patient in
# the roster gets a record, including the ones with no conditions and no
# medications. Building the spine by joining conditions or medications instead
# silently drops 4 and 92 patients respectively — and a submission that is
# missing patients is scored as wrong on those patients, not excused.

import os
import re

import pandas as pd


# --- Unusable observation values -------------------------------------------
# Coherent stores EKG waveform arrays and base64-encoded PNGs in the same
# VALUE column as "6.1". Nothing in this project can use them: they are not
# numbers, they are not readable text, and a single one can be tens of
# kilobytes. They are dropped at BUILD time, not render time, because no
# method — rules, LLM, or anything added later — has a use for them, and
# carrying them costs memory on every run.
EXCLUDED_OBS_CODES = {
    "29303009",   # Electrocardiographic procedure — raw waveform arrays / PNGs
}
MAX_VALUE_CHARS = 200
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/\s]{100,}={0,2}$")


def _is_unusable_value(value):
    """True for blobs: overlong strings and base64 payloads."""
    if not isinstance(value, str):
        return False
    if len(value) > MAX_VALUE_CHARS:
        return True
    return bool(_BASE64_RE.match(value))


# --- Lab whitelist ----------------------------------------------------------
# Applied at RENDER time, not build time. The distinction matters: dropping
# these rows from the record would make the record T2D-specific, and the whole
# point of records.py is that Resistant Hypertension reads the same objects.
# So the record keeps every usable observation; the CHART shows the ones that
# bear on metabolic status. Order here is the order they print.
LAB_WHITELIST = {
    "4548-4":  "HbA1c (%)",
    "2339-0":  "Glucose (mg/dL)",
    "2345-7":  "Glucose (mg/dL)",
    "39156-5": "BMI (kg/m2)",
    "8480-6":  "Systolic BP (mmHg)",
    "8462-4":  "Diastolic BP (mmHg)",
    "2093-3":  "Total cholesterol (mg/dL)",
    "2571-8":  "Triglycerides (mg/dL)",
    "2085-9":  "HDL (mg/dL)",
    "18262-6": "LDL (mg/dL)",
    "38483-4": "Creatinine (mg/dL)",
    "33914-3": "eGFR (mL/min)",
    "72166-2": "Smoking status",
}


# The submission roster is fixed. If this ever stops being 3539 the dashboard
# contract has changed and every assertion downstream is meaningless.
EXPECTED_PATIENTS = 3539

# Ages are computed against a fixed reference date, matching phenotype.py.
# Not the diagnosis date — a stable "as of" so ages are comparable across runs.
AGE_REFERENCE = pd.Timestamp("2020-01-01")

# Free-text notes are the one input that may or may not exist. Coherent as
# exported here has no diagnostic_reports.csv; other Synthea exports do. We
# check rather than assume, so this file works on both.
NOTES_FILE = "diagnostic_reports.csv"


def _as_str(df, col):
    """Codes are mixed-width identifiers, not numbers. Every downstream .isin()
    depends on this coercion — read as int, '860975' and 860975 stop matching."""
    df[col] = df[col].astype(str)
    return df


def _group_records(df, key_col, keep):
    """Split a table into one list-of-dicts per patient.

    Returns a plain dict so patients absent from the table simply don't appear —
    the caller fills them with an empty list. Absence means zero, not missing.
    """
    out = {}
    sub = df[[key_col] + keep]
    for pid, chunk in sub.groupby(key_col, sort=False):
        out[pid] = chunk[keep].to_dict("records")
    return out


def build_records(verbose=True, load_notes=True):
    """Assemble one record per patient. Returns {patient_id: record}.

    The record shape is deliberately flat and JSON-ish: dicts and lists of
    scalars, no DataFrames, no pandas types leaking out. A labeler should be
    able to hand a record straight to a renderer without knowing pandas exists.
    """
    if verbose:
        print("[records] loading tables ...")

    patients = pd.read_csv("patients.csv")
    conditions = _as_str(pd.read_csv("conditions.csv"), "CODE")
    medications = _as_str(pd.read_csv("medications.csv"), "CODE")
    observations = _as_str(
        pd.read_csv(
            "observations.csv",
            usecols=["DATE", "PATIENT", "CODE", "DESCRIPTION", "VALUE", "UNITS", "TYPE"],
        ),
        "CODE",
    )
    encounters = pd.read_csv(
        "encounters.csv",
        usecols=["START", "PATIENT", "ENCOUNTERCLASS", "CODE", "DESCRIPTION"],
    )
    encounters = _as_str(encounters, "CODE")
    careplans = _as_str(pd.read_csv("careplans.csv"), "CODE")

    # --- drop unusable observation values, loudly -----------------------------
    # Silence here would be the wrong choice: if a future export encodes
    # something useful as a long string, this counter is how we find out.
    n_obs_before = len(observations)
    by_code = observations["CODE"].isin(EXCLUDED_OBS_CODES)
    by_blob = observations["VALUE"].map(_is_unusable_value)
    observations = observations[~(by_code | by_blob)]
    if verbose:
        print(f"[records]   dropped {int(by_code.sum()):>6} observation rows "
              f"by excluded code {sorted(EXCLUDED_OBS_CODES)}")
        print(f"[records]   dropped {int((by_blob & ~by_code).sum()):>6} observation rows "
              f"with blob VALUEs (>{MAX_VALUE_CHARS} chars or base64)")
        print(f"[records]   observations {n_obs_before} -> {len(observations)} usable")

    if verbose:
        print(f"[records]   patients     {patients.shape}")
        print(f"[records]   conditions   {conditions.shape}")
        print(f"[records]   medications  {medications.shape}")
        print(f"[records]   observations {observations.shape}")
        print(f"[records]   encounters   {encounters.shape}")
        print(f"[records]   careplans    {careplans.shape}")

    # --- the coverage check that motivates the whole spine rule ---------------
    # Print it every run. It is the single cheapest guard against the most
    # expensive mistake available in this project.
    roster = set(patients["Id"])
    if verbose:
        for name, table in (
            ("conditions", conditions),
            ("medications", medications),
            ("observations", observations),
            ("encounters", encounters),
        ):
            missing = len(roster - set(table["PATIENT"]))
            note = "  <-- would be DROPPED if used as the spine" if missing else ""
            print(f"[records]   {name:<13} covers {len(roster)-missing:>5}/{len(roster)}"
                  f"  (missing {missing}){note}")

    # --- notes: present only in some exports ---------------------------------
    # diagnostic_reports.csv is 172 MB and the chart does not render notes yet,
    # so the runner switches this off. Loading it would cost time and memory on
    # every run to populate a field nothing reads.
    notes_by_patient = {}
    if not load_notes:
        if verbose:
            print("[records]   notes        (skipped by request — load_notes=False)")
    elif os.path.exists(NOTES_FILE):
        notes = pd.read_csv(NOTES_FILE)
        text_col = next((c for c in ("TEXT", "NOTE", "REPORT", "DESCRIPTION")
                         if c in notes.columns), None)
        date_col = next((c for c in ("DATE", "START", "ISSUED") if c in notes.columns), None)
        keep = [c for c in (date_col, text_col) if c]
        if "PATIENT" in notes.columns and keep:
            notes_by_patient = _group_records(notes, "PATIENT", keep)
        if verbose:
            print(f"[records]   notes        {notes.shape} from {NOTES_FILE}")
    elif verbose:
        print(f"[records]   notes        (no {NOTES_FILE} — skipping, not an error)")
    if verbose and notes_by_patient:
        print("[records]   NOTE: notes are carried on the record but NOT rendered "
              "into the chart — the chart format is frozen for comparability.")

    # --- per-table grouping ---------------------------------------------------
    # Dates stay as the raw ISO strings the CSVs carry. They are uniform within
    # each table, so lexicographic order is chronological order, and comparisons
    # stay byte-identical to what phenotype.py does with parsed timestamps.
    cond_by = _group_records(conditions, "PATIENT", ["CODE", "DESCRIPTION", "START", "STOP"])
    med_by = _group_records(
        medications, "PATIENT",
        ["CODE", "DESCRIPTION", "START", "STOP", "REASONCODE", "REASONDESCRIPTION"])
    obs_by = _group_records(
        observations, "PATIENT", ["CODE", "DESCRIPTION", "VALUE", "UNITS", "DATE", "TYPE"])
    enc_by = _group_records(encounters, "PATIENT", ["START", "ENCOUNTERCLASS", "DESCRIPTION"])
    plan_by = _group_records(
        careplans, "PATIENT", ["CODE", "DESCRIPTION", "START", "STOP", "REASONDESCRIPTION"])

    # --- assemble, indexed off the roster ------------------------------------
    births = pd.to_datetime(patients["BIRTHDATE"])
    ages = ((AGE_REFERENCE - births).dt.days / 365.25).round(1)

    records = {}
    for row, age in zip(patients.to_dict("records"), ages):
        pid = row["Id"]
        records[pid] = {
            "id": pid,
            "demographics": {
                "birthdate": row["BIRTHDATE"],
                "deathdate": row["DEATHDATE"] if pd.notna(row["DEATHDATE"]) else None,
                "age_at_reference": None if pd.isna(age) else float(age),
                "gender": row["GENDER"],
                "race": row["RACE"],
                "ethnicity": row["ETHNICITY"],
                "marital": row["MARITAL"] if pd.notna(row["MARITAL"]) else None,
                "city": row["CITY"],
                "state": row["STATE"],
            },
            "conditions": cond_by.get(pid, []),
            "medications": med_by.get(pid, []),
            "labs": obs_by.get(pid, []),
            # Encounters and careplans are not in the minimal record spec, but
            # both are load-bearing: the router needs office-visit counts to
            # tell "screened and clean" from "never looked at", and careplans
            # are a known leakage channel the chart renderer has to be able to
            # mask. Cheap to carry, expensive to go back for.
            "encounters": enc_by.get(pid, []),
            "careplans": plan_by.get(pid, []),
            "notes": notes_by_patient.get(pid, []),
        }

    assert len(records) == len(patients), "lost patients while assembling records"
    if len(records) != EXPECTED_PATIENTS:
        print(f"[records] WARNING: roster is {len(records)}, expected {EXPECTED_PATIENTS}")
    if verbose:
        print(f"[records] built {len(records)} records")
    return records


# ---------------------------------------------------------------------------
# Chart rendering. Also method-agnostic: this is how a record is shown to a
# human reviewer or to a model. The mask flag suppresses the two channels that
# name the answer out loud — diabetes-adjacent condition descriptions and
# diabetes-named care plans — so the same patient can be presented with and
# without the giveaway. Anything that names a phenotype must sit behind mask.
# ---------------------------------------------------------------------------

MASK_TERMS = ("diabet", "prediabet", "hyperglycemia", "glycemic", "insulin",
              "metformin", "a1c", "hemoglobin a1c")


def _names_the_answer(text):
    low = str(text).lower()
    return any(term in low for term in MASK_TERMS)


def _fmt(rows, line, limit=None):
    if not rows:
        return ["  (none)"]
    shown = rows if limit is None else rows[:limit]
    out = ["  " + line(r) for r in shown]
    if limit is not None and len(rows) > limit:
        out.append(f"  ... and {len(rows) - limit} more")
    return out


def render_chart(record, mask=False, max_labs_per_code=4, include_notes=False):
    """Render one patient as plain text. Deterministic — same record, same bytes.

    include_notes defaults to FALSE even when notes are present on the record.
    The chart format is the experiment's control variable: a run whose charts
    gained a notes section is not comparable to the run that measured token
    counts without one. Turning notes on is a deliberate, separate experiment.
    """
    d = record["demographics"]
    L = [f"PATIENT {record['id']}",
         f"  age {d['age_at_reference']} | {d['gender']} | {d['race']}/{d['ethnicity']}"
         + (f" | deceased {d['deathdate']}" if d["deathdate"] else "")]

    L.append("\nCONDITIONS (code, onset):")
    conds = record["conditions"]
    if mask:
        conds = [c for c in conds if not _names_the_answer(c["DESCRIPTION"])]
    L += _fmt(sorted(conds, key=lambda c: c["START"]),
              lambda c: f"{c['START']}  {c['CODE']:<16} {c['DESCRIPTION']}")

    # Synthea re-issues the same prescription at every refill, so a patient on
    # metformin for forty years carries ~200 near-identical medication rows.
    # Printing them verbatim costs a fortune in input tokens and buries the one
    # fact that matters — that the drug was started, and when. Collapse to one
    # line per drug: first start, last stop, number of fills. No information
    # the phenotype depends on is lost; the earliest start date, which is what
    # every PheKB path compares, is preserved exactly.
    L.append("\nMEDICATIONS (first start -> last stop, fills):")
    by_drug = {}
    for m in record["medications"]:
        key = (m["CODE"], m["DESCRIPTION"])
        agg = by_drug.setdefault(key, {"start": m["START"], "stop": m["STOP"], "n": 0})
        agg["n"] += 1
        agg["start"] = min(agg["start"], m["START"])
        if pd.isna(m["STOP"]):
            agg["stop"] = None          # an open prescription outranks any stop date
        elif agg["stop"] is not None:
            agg["stop"] = max(str(agg["stop"]), m["STOP"])
    med_rows = sorted(by_drug.items(), key=lambda kv: kv[1]["start"])
    L += _fmt(med_rows,
              lambda kv: f"{kv[1]['start'][:10]} -> "
                         f"{(str(kv[1]['stop'])[:10] if kv[1]['stop'] else 'ongoing'):<10} "
                         f"{kv[1]['n']:>3} fills  {kv[0][0]:<10} {kv[0][1]}")

    # Labs: whitelist, don't dump. A patient carries ~400 observations across
    # ~150 distinct codes, the overwhelming majority of which say nothing about
    # metabolic status. Showing all of them is not "being thorough" — it buries
    # the twelve values that decide the question under a wall of ferritin.
    # Anything not on the list is summarised as a count, so the reader can see
    # that it was withheld rather than absent.
    L.append(f"\nLABS (most recent {max_labs_per_code} per test):")
    by_code = {}
    for lab in record["labs"]:
        by_code.setdefault(lab["CODE"], []).append(lab)

    lab_lines, n_shown = [], 0
    for code, name in LAB_WHITELIST.items():
        rows = by_code.get(code)
        if not rows:
            continue
        if mask and _names_the_answer(name):
            continue
        rows = sorted(rows, key=lambda r: r["DATE"], reverse=True)[:max_labs_per_code]
        vals = ", ".join(f"{r['VALUE']}{'' if pd.isna(r['UNITS']) else ' ' + str(r['UNITS'])}"
                         f" ({r['DATE'][:10]})" for r in rows)
        lab_lines.append(f"  {name:<26} {vals}")
        n_shown += 1
    L += lab_lines or ["  (none on the metabolic panel)"]

    n_other = sum(1 for c in by_code if c not in LAB_WHITELIST)
    if n_other:
        L.append(f"  ({n_other} other lab types on file, not shown)")

    L.append("\nENCOUNTERS (by class):")
    counts = {}
    for e in record["encounters"]:
        counts[e["ENCOUNTERCLASS"]] = counts.get(e["ENCOUNTERCLASS"], 0) + 1
    L += _fmt(sorted(counts.items(), key=lambda kv: -kv[1]),
              lambda kv: f"{kv[0]:<14} {kv[1]}")

    plans = record["careplans"]
    if mask:
        plans = [p for p in plans if not _names_the_answer(p["DESCRIPTION"])]
    L.append("\nCARE PLANS:")
    L += _fmt(sorted(plans, key=lambda p: p["START"]),
              lambda p: f"{p['START'][:10]}  {p['DESCRIPTION']}")

    if include_notes and record["notes"]:
        L.append("\nNOTES:")
        L += ["  " + " | ".join(str(v) for v in n.values()) for n in record["notes"][:5]]

    return "\n".join(L)


def chart_size(chart):
    """Characters and a rough token estimate (~4 chars/token) for one chart.

    Deliberately an estimate, not a count_tokens() call: knowing the size of a
    prompt should never itself require an API call, least of all during a dry
    run whose whole promise is that it makes none.
    """
    return len(chart), len(chart) // 4


if __name__ == "__main__":
    recs = build_records()
    first = next(iter(recs.values()))
    print("\n" + render_chart(first))
