# schema.py — build a data dictionary for the code-generating agent.
#
# This is the ONLY view of the data the agent under test is allowed to have.
# It exists because of an experimental control: the agent is being asked to
# implement the PheKB T2DM algorithm from the published definition alone, and
# it must not see phenotype.py, CLAUDE.md, a.py, broad_codes.py, or
# t2d_cohort.csv. If it sees my implementation the comparison is measuring
# transcription, not phenotyping.
#
# So everything here is derived mechanically from the CSVs by rules that know
# nothing about diabetes:
#
#   - every column, its dtype, its null rate
#   - row count and patient coverage per file
#   - the 40 most frequent CODE/DESCRIPTION pairs, ranked by DISTINCT PATIENTS
#   - distinct values for any low-cardinality categorical column
#
# The ranking is by patient count, not row count, on purpose: a code that
# appears 900 times in one patient's chart is not more clinically prevalent
# than a code appearing once in 900 charts, and the agent is choosing code
# lists for a cohort definition.
#
# The low-cardinality rule is applied uniformly to every non-code object
# column under a fixed threshold. It is not a hint. It happens to expose
# ENCOUNTERCLASS values, which the agent needs to map "office visit" onto this
# schema at all — but it exposes MARITAL and RACE by exactly the same rule.
#
# Deliberately NOT here: any diabetes code list, any threshold, any hint that
# a criterion is or isn't satisfiable in this dataset. Emptiness and absence
# are things the agent should have to discover, because whether it notices
# them is one of the things being measured.
#
# Run from the repo root:  python schema.py   ->  schema_summary.md

import os

import pandas as pd

FILES = [
    "patients.csv",
    "conditions.csv",
    "medications.csv",
    "observations.csv",
    "encounters.csv",
    "careplans.csv",
    "supplies.csv",
]

OUT = "schema_summary.md"

TOP_N = 40             # code/description pairs per file
MAX_CATEGORICAL = 25   # a column with <= this many distinct values gets enumerated

# Columns never worth enumerating even when low-cardinality — free-text-ish or
# identifier-ish. Kept short and generic; this is not a diabetes-aware filter.
NEVER_ENUMERATE = {
    "Id", "PATIENT", "ENCOUNTER", "CODE", "DESCRIPTION", "REASONCODE",
    "REASONDESCRIPTION", "START", "STOP", "DATE", "BIRTHDATE", "DEATHDATE",
    "SSN", "DRIVERS", "PASSPORT", "FIRST", "LAST", "MAIDEN", "SUFFIX",
    "PREFIX", "ADDRESS", "LAT", "LON", "ZIP", "VALUE", "PROVIDER",
    "ORGANIZATION", "PAYER",
}


def patient_column(df):
    """Which column identifies the patient. patients.csv calls it Id; every
    other table calls it PATIENT."""
    if "PATIENT" in df.columns:
        return "PATIENT"
    if "Id" in df.columns:
        return "Id"
    return None


def load(path):
    """Read one CSV with every column as string.

    dtype=str is load-bearing, not laziness: CODE columns hold mixed-width
    identifiers (SNOMED, RxNorm, LOINC) that pandas will happily turn into
    floats, silently mangling them. The data dictionary has to report what is
    actually in the file. Numeric columns are described by their raw text; the
    agent will do its own coercion.
    """
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def describe_columns(df):
    """Column table: name, inferred dtype, null rate, distinct count."""
    rows = []
    n = len(df)
    for col in df.columns:
        s = df[col]
        nulls = int(s.isna().sum())
        # Report what the values LOOK like, since we forced str on read.
        non_null = s.dropna()
        if len(non_null) == 0:
            kind = "empty"
        else:
            coerced = pd.to_numeric(non_null, errors="coerce")
            if coerced.notna().all():
                kind = "numeric (as text)"
            else:
                kind = "text"
        rows.append({
            "column": col,
            "type": kind,
            "null_pct": (nulls / n * 100) if n else 0.0,
            "distinct": int(non_null.nunique()),
        })
    return rows


def code_description_pairs(df, pid_col):
    """The TOP_N most common (CODE, DESCRIPTION) pairs, ranked by how many
    DISTINCT PATIENTS carry the code."""
    if "CODE" not in df.columns or "DESCRIPTION" not in df.columns:
        return None, 0

    sub = df[["CODE", "DESCRIPTION", pid_col]].dropna(subset=["CODE"])
    if sub.empty:
        return None, 0

    grouped = (
        sub.groupby(["CODE", "DESCRIPTION"], dropna=False)
        .agg(patients=(pid_col, "nunique"), rows=(pid_col, "size"))
        .reset_index()
        .sort_values(["patients", "rows"], ascending=False)
    )
    return grouped, len(grouped)


def categorical_columns(df):
    """Low-cardinality columns, enumerated with counts. Uniform rule; no
    column is singled out."""
    out = {}
    for col in df.columns:
        if col in NEVER_ENUMERATE:
            continue
        non_null = df[col].dropna()
        if non_null.empty:
            continue
        if non_null.nunique() <= MAX_CATEGORICAL:
            out[col] = non_null.value_counts()
    return out


def numeric_value_summary(df):
    """For observations-style tables, the numeric spread of VALUE per unit.

    Included because a lab-based criterion is unimplementable without knowing
    what units the values are in — mg/dL vs mmol/L changes every threshold.
    Reported by UNITS across the whole file, not per code, so it stays a
    property of the schema rather than a pointer at any particular lab.
    """
    if "VALUE" not in df.columns or "UNITS" not in df.columns:
        return None

    sub = df[["VALUE", "UNITS"]].dropna()
    sub = sub.assign(num=pd.to_numeric(sub["VALUE"], errors="coerce")).dropna(subset=["num"])
    if sub.empty:
        return None

    summary = (
        sub.groupby("UNITS")["num"]
        .agg(n="size", min="min", median="median", max="max")
        .reset_index()
        .sort_values("n", ascending=False)
        .head(MAX_CATEGORICAL)
    )
    return summary


def main():
    all_patients = None
    lines = []

    lines.append("# Data dictionary\n")
    lines.append(
        "Machine-generated from the CSV files in the working directory. "
        "Every figure below is computed directly from the data.\n"
    )
    lines.append(
        "Code/description pairs are ranked by **distinct patients** carrying "
        "the code, not by row count.\n"
    )

    # patients.csv first so we can express coverage as a fraction of the roster.
    roster = load("patients.csv")
    all_patients = set(roster["Id"].dropna())
    lines.append(f"\n**Patient roster: {len(all_patients)} patients in `patients.csv`.**\n")

    for path in FILES:
        if not os.path.exists(path):
            lines.append(f"\n---\n\n## `{path}`\n\n_File not present in the working directory._\n")
            print(f"[schema] MISSING {path}")
            continue

        print(f"[schema] reading {path} ...")
        df = roster if path == "patients.csv" else load(path)

        n_rows = len(df)
        pid = patient_column(df)

        lines.append(f"\n---\n\n## `{path}`\n")

        if n_rows == 0:
            # Stated as a plain fact, with no commentary about what it implies.
            lines.append("\n**This file contains 0 data rows (header only).**\n")

        lines.append(f"\n- Rows: **{n_rows}**")

        if pid is not None:
            covered = set(df[pid].dropna())
            n_cov = len(covered)
            pct = (n_cov / len(all_patients) * 100) if all_patients else 0.0
            lines.append(
                f"\n- Distinct patients: **{n_cov}** "
                f"({pct:.1f}% of the {len(all_patients)}-patient roster)"
            )
            unknown = covered - all_patients
            if unknown:
                lines.append(
                    f"\n- Patient ids not present in `patients.csv`: **{len(unknown)}**"
                )
        lines.append("\n")

        # ---- columns
        lines.append("\n### Columns\n")
        lines.append("\n| column | type | % null | distinct values |")
        lines.append("\n| --- | --- | ---: | ---: |")
        for r in describe_columns(df):
            lines.append(
                f"\n| `{r['column']}` | {r['type']} | {r['null_pct']:.1f} | {r['distinct']} |"
            )
        lines.append("\n")

        if n_rows == 0:
            continue

        # ---- code / description pairs
        pairs, total_pairs = code_description_pairs(df, pid)
        if pairs is not None:
            def pair_table(frame):
                lines.append("\n| CODE | DESCRIPTION | patients | rows |")
                lines.append("\n| --- | --- | ---: | ---: |")
                for _, r in frame.iterrows():
                    desc = str(r["DESCRIPTION"]).replace("|", "\\|")
                    lines.append(
                        f"\n| `{r['CODE']}` | {desc} | {r['patients']} | {r['rows']} |"
                    )
                lines.append("\n")

            head = pairs.head(TOP_N)
            lines.append(
                f"\n### Most frequent CODE / DESCRIPTION pairs\n\n"
                f"Top {len(head)} of **{total_pairs}** distinct pairs, ranked by "
                f"distinct patients.\n"
            )
            pair_table(head)

            # Then every remaining pair. Ranking by frequency is informative,
            # but truncating at it is not: a code list for a cohort definition
            # is chosen by clinical meaning, and the rarest codes in a file are
            # often exactly the ones a definition turns on. The full inventory
            # is a few hundred rows per file, so there is no reason to make the
            # agent guess at what it cannot see. Selection here is by nothing
            # at all — this is every code in the file.
            rest = pairs.iloc[TOP_N:]
            if len(rest):
                lines.append(
                    f"\n### Complete code inventory — remaining {len(rest)} pairs\n\n"
                    "Same ranking continued, so the full set of codes present in "
                    "this file is listed.\n"
                )
                pair_table(rest)

        # ---- low-cardinality categoricals
        cats = categorical_columns(df)
        if cats:
            lines.append("\n### Low-cardinality columns\n")
            lines.append(
                f"\nEvery non-identifier column with {MAX_CATEGORICAL} or fewer "
                "distinct values, enumerated with row counts.\n"
            )
            for col, vc in cats.items():
                lines.append(f"\n**`{col}`** — {len(vc)} distinct\n")
                lines.append("\n| value | rows |")
                lines.append("\n| --- | ---: |")
                for val, cnt in vc.items():
                    v = str(val).replace("|", "\\|")
                    lines.append(f"\n| {v} | {cnt} |")
                lines.append("\n")

        # ---- numeric spread (observations)
        nums = numeric_value_summary(df)
        if nums is not None:
            lines.append("\n### Numeric `VALUE` spread by `UNITS`\n")
            lines.append("\n| UNITS | n | min | median | max |")
            lines.append("\n| --- | ---: | ---: | ---: | ---: |")
            for _, r in nums.iterrows():
                u = str(r["UNITS"]).replace("|", "\\|")
                lines.append(
                    f"\n| {u} | {int(r['n'])} | {r['min']:.2f} | "
                    f"{r['median']:.2f} | {r['max']:.2f} |"
                )
            lines.append("\n")

    with open(OUT, "w") as f:
        f.write("".join(lines))

    size_kb = os.path.getsize(OUT) / 1024
    print(f"\n[schema] wrote {OUT} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
