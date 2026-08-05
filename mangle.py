# mangle.py — synthesize a second institution's schema from Coherent.
#
# The claim under test (Tim, 7/29) is that LLM phenotyping ports across
# institutions with varying schemas where feature-engineered ML does not.
# Nobody has tested it, and it is not testable on one dataset — so this builds
# a second one: the same patients and the same clinical facts, wearing a
# different schema and a different coding system.
#
# Three transformations, each modelling a real thing that differs between
# institutions:
#
#   COLUMN NAMES   PATIENT -> subject_ref, CODE -> concept_id, and so on. Every
#                  extract has its own names for the same fields.
#   VOCABULARY     SNOMED / RxNorm / LOINC codes remapped to arbitrary local
#                  integers via a saved lookup. This is the realistic case of a
#                  site using internal identifiers, or a different code system,
#                  for the same concepts.
#   MISSING TABLE  careplans.csv deleted outright. Not every site exports every
#                  domain.
#
# DESCRIPTIONS ARE LEFT INTACT, deliberately. That is what makes this a test of
# schema and vocabulary robustness rather than of information loss: the clinical
# meaning is still present in the text, and the question is whether a method can
# still find it once the identifiers it was written against stop matching. A
# rule list keyed on "44054006" cannot. Whether a model can is the experiment.
#
# ZERO API calls. Run: python mangle.py

import json
import os
import shutil

import pandas as pd

OUT_DIR = "mangled"
LOOKUP_PATH = os.path.join(OUT_DIR, "_code_lookup.json")

# Every rename a downstream reader would trip over. Same concepts, new names.
COLUMN_MAP = {
    "PATIENT": "subject_ref",
    "Id": "row_uid",
    "CODE": "concept_id",
    "DESCRIPTION": "concept_name",
    "VALUE": "result_val",
    "UNITS": "result_units",
    "START": "eff_start",
    "STOP": "eff_end",
    "DATE": "svc_date",
    "ENCOUNTER": "visit_ref",
    "ENCOUNTERCLASS": "visit_kind",
    "REASONCODE": "reason_concept_id",
    "REASONDESCRIPTION": "reason_name",
    "BIRTHDATE": "dob",
    "DEATHDATE": "dod",
    "GENDER": "sex_code",
    "RACE": "race_code",
    "ETHNICITY": "ethnicity_code",
    "MARITAL": "marital_code",
    "TYPE": "obs_kind",
    "CITY": "city_name",
    "STATE": "state_name",
}

# Tables to transform. careplans is deliberately absent — it gets deleted.
TABLES = ["patients", "conditions", "medications", "observations", "encounters"]
DROPPED_TABLES = ["careplans"]

# Columns whose values are clinical codes needing remapping, per table.
CODE_COLUMNS = {
    "conditions": ["CODE"],
    "medications": ["CODE", "REASONCODE"],
    "observations": ["CODE"],
    "encounters": ["CODE", "REASONCODE"],
}

CODE_BASE = 700000        # arbitrary local identifier space


def build_lookup(frames):
    """One deterministic code -> local integer map, shared across tables so the
    same concept keeps one identifier — as it would at a real site."""
    codes = set()
    for table, cols in CODE_COLUMNS.items():
        df = frames[table]
        for col in cols:
            if col in df.columns:
                codes |= {str(c) for c in df[col].dropna().unique()}
    # Sorted for reproducibility: same input, same lookup, every run.
    return {code: str(CODE_BASE + i) for i, code in enumerate(sorted(codes))}


def main():
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)

    frames = {t: pd.read_csv(f"{t}.csv", dtype=str) for t in TABLES}
    lookup = build_lookup(frames)

    print(f"=== MANGLE: {os.path.abspath('.')} -> ./{OUT_DIR}/ ===\n")
    print(f"code lookup: {len(lookup):,} distinct clinical codes remapped to "
          f"integers starting at {CODE_BASE}")
    sample = list(lookup.items())[:5]
    for old, new in sample:
        print(f"    {old:<18} -> {new}")
    print()

    for table in TABLES:
        df = frames[table].copy()
        before_cols = list(df.columns)

        for col in CODE_COLUMNS.get(table, []):
            if col in df.columns:
                df[col] = df[col].map(lambda v: lookup.get(str(v), v)
                                      if pd.notna(v) else v)

        renamed = {c: COLUMN_MAP[c] for c in df.columns if c in COLUMN_MAP}
        df = df.rename(columns=renamed)
        df.to_csv(os.path.join(OUT_DIR, f"{table}.csv"), index=False)

        print(f"{table}.csv  {len(df):,} rows")
        print(f"    columns renamed : {len(renamed)}/{len(before_cols)}")
        print(f"    codes remapped  : {CODE_COLUMNS.get(table, []) or 'none'}")
        changed = [f"{c}->{renamed[c]}" for c in before_cols if c in renamed][:6]
        print(f"    e.g. {', '.join(changed)}")

    for table in DROPPED_TABLES:
        print(f"\n{table}.csv  DELETED — not exported by this site")

    with open(LOOKUP_PATH, "w") as fh:
        json.dump(lookup, fh, indent=1, sort_keys=True)

    print(f"\nlookup saved to {LOOKUP_PATH}")
    print("\n--- what this breaks ---")
    print("  descriptions : INTACT (clinical meaning preserved in text)")
    print("  column names : every reader keyed on PATIENT/CODE/VALUE fails")
    print("  code values  : every .isin(T2D_DX) match returns nothing")
    print("  careplans    : absent entirely")
    print("\nZERO API calls made.")


if __name__ == "__main__":
    main()
