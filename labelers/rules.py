# labelers/rules.py — the rule labeler: PheKB T2DM, wrapped for the cascade.
#
# This is phenotype.py's logic re-expressed against a record dict instead of a
# pandas row. It is a WRAPPER, not a reimplementation: same code lists, same
# five paths in the same order, same first-match-wins. If it disagrees with
# phenotype.py on any patient, this file is wrong, not phenotype.py.
# phenotype.py is the frozen baseline; the whole experiment is only meaningful
# if the baseline stays where it was.
#
# Two responsibilities live here, and it is worth being clear that they are
# different things:
#
#   1. label(record) -> 0|1   the PheKB answer for this patient.
#   2. ROUTE_PREDICATES       which evidence configuration this patient is in.
#
# (2) never consults (1)'s output as a label. It asks "does a PheKB path close
# on this evidence?" — a question about the evidence, not about the patient's
# status. The distinction matters: "this patient is a case" is an answer;
# "the evidence here is sufficient to settle it either way" is a routing fact.

# --- Code lists. Copy-pasted from phenotype.py on purpose, matching the
# --- convention already set by a.py: each method sees exactly the evidence the
# --- rules keyed on. They are NOT imported. Change a list here and you must
# --- change it there, or the comparison stops being apples-to-apples.

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

T1D_DX = ["46635009"]   # Type 1 DM — matches zero patients in Coherent

DM_DX_BROAD = T2D_DX + [
    "15777000",         # Prediabetes
    "80394007",         # Hyperglycemia
    "127013003",        # Diabetic renal disease
    "427089005",        # Diabetes from Cystic Fibrosis
]

T2D_MED = ["860975", "897122", "1373463"]   # metformin ER / liraglutide / canagliflozin
INSULIN = ["106892", "865098"]              # Humulin / insulin lispro

A1C = ["4548-4"]
GLUCOSE = ["2339-0", "2345-7"]

A1C_THRESHOLD = 6.5          # case abnormality
GLUCOSE_THRESHOLD = 200
A1C_THRESHOLD_CTRL = 6.0     # control abnormality — deliberately LOOSER
GLUCOSE_THRESHOLD_CTRL = 110

OFFICE_CLASSES = ("ambulatory", "wellness", "outpatient")


def _numeric(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _distinct_dx_dates(record, codes):
    """Diagnosis counts are distinct DATES, not row counts — two codes entered
    at the same visit are one diagnosis event, not two."""
    return len({c["START"] for c in record["conditions"] if c["CODE"] in codes})


def _earliest_med_date(record, codes):
    dates = [m["START"] for m in record["medications"] if m["CODE"] in codes]
    return min(dates) if dates else None


def facts(record):
    """Compute the PheKB per-patient facts. Memoized onto the record — the
    router asks five predicates per patient and none of them should pay for
    this five times."""
    cached = record.get("_rule_facts")
    if cached is not None:
        return cached

    a1c_vals, glu_vals = [], []
    glucose_drawn = False
    for lab in record["labs"]:
        code = lab["CODE"]
        if code in A1C:
            v = _numeric(lab["VALUE"])
            if v is not None:
                a1c_vals.append(v)
        elif code in GLUCOSE:
            glucose_drawn = True
            v = _numeric(lab["VALUE"])
            if v is not None:
                glu_vals.append(v)

    office_visits = len({e["START"][:10] for e in record["encounters"]
                         if e["ENCOUNTERCLASS"] in OFFICE_CLASSES})

    t2dm_dx_count = _distinct_dx_dates(record, T2D_DX)
    f = {
        "t1dm_dx_count": _distinct_dx_dates(record, T1D_DX),
        "t2dm_dx_count": t2dm_dx_count,
        # No billing stream in Coherent — every condition arrives via an
        # encounter, so the clinician-entered count IS the diagnosis count.
        "physician_dx_count": t2dm_dx_count,
        "t2dm_med_date": _earliest_med_date(record, T2D_MED),
        "insulin_date": _earliest_med_date(record, INSULIN),
        "abnormal_lab": (any(v >= A1C_THRESHOLD for v in a1c_vals)
                         or any(v > GLUCOSE_THRESHOLD for v in glu_vals)),
        "dm_broad_count": _distinct_dx_dates(record, DM_DX_BROAD),
        "glucose_drawn": glucose_drawn,
        "ctrl_abnormal_lab": (any(v >= A1C_THRESHOLD_CTRL for v in a1c_vals)
                              or any(v > GLUCOSE_THRESHOLD_CTRL for v in glu_vals)),
        "office_visits": office_visits,
        "on_dm_med": any(m["CODE"] in T2D_MED or m["CODE"] in INSULIN
                         for m in record["medications"]),
    }
    record["_rule_facts"] = f
    return f


def which_path(record):
    """Return 'P1'..'P5' for the first PheKB case path that closes, else None.

    Order is the algorithm's order and first match wins. Read against
    T2DM-CASE-SELECTION; do not reorder to be tidy.
    """
    p = facts(record)
    no_t1d = p["t1dm_dx_count"] == 0          # the exclusion gate at the top
    has_t2d = p["t2dm_dx_count"] > 0
    on_med = p["t2dm_med_date"] is not None
    on_insln = p["insulin_date"] is not None

    if not no_t1d:
        return None
    # P1: T2D dx, on both agents, oral agent came FIRST => T2D, not T1D
    if has_t2d and on_med and on_insln and p["t2dm_med_date"] < p["insulin_date"]:
        return "P1"
    # P2: T2D dx, on oral agent, never on insulin
    if has_t2d and not on_insln and on_med:
        return "P2"
    # P3: T2D dx, untreated, but the labs are abnormal
    if has_t2d and not on_insln and not on_med and p["abnormal_lab"]:
        return "P3"
    # P4: no T2D dx at all — treated-but-uncoded, confirmed by abnormal labs
    if not has_t2d and on_med and p["abnormal_lab"]:
        return "P4"
    # P5: T2D dx, insulin only, but the clinician wrote the dx on >= 2 dates
    if has_t2d and on_insln and not on_med and p["physician_dx_count"] >= 2:
        return "P5"
    return None


def label(record):
    """The labeler contract: 0 or 1. A closed PheKB path is a case."""
    return 1 if which_path(record) is not None else 0


# ---------------------------------------------------------------------------
# Routing predicates. Each is a boolean expression over EVIDENCE PRESENCE ONLY:
# does a dx code exist, is an oral agent on file, is insulin on file, were labs
# abnormal, was glucose ever drawn, did the patient show up to clinic. No
# predicate reads label(), a silver label, or t2d_cohort.csv.
#
# They are written fully guarded rather than as an if/elif chain, so the router
# can assert that exactly one fires instead of taking whichever came first.
# ---------------------------------------------------------------------------

def _has_dx(record):
    return facts(record)["t2dm_dx_count"] > 0


def _chain_closes(record):
    """Does any PheKB path close on this evidence? A question about the
    sufficiency of the evidence, not about the patient's status."""
    return which_path(record) is not None


def _screened_and_clean(record):
    """PheKB Algorithm 8, the control side: no diabetes-adjacent code, glucose
    actually drawn, clean at the LOOSER control thresholds, seen in clinic at
    least twice, on no diabetes medication.

    The glucose-drawn condition is what makes this decisive rather than merely
    silent — it is the difference between 'screened and clean' and 'nobody ever
    looked'. Family history would be a sixth condition; Coherent has none, so
    it passes vacuously for everyone and is not implemented as a filter.
    """
    f = facts(record)
    return (f["dm_broad_count"] == 0
            and f["glucose_drawn"]
            and not f["ctrl_abnormal_lab"]
            and f["office_visits"] >= 2
            and not f["on_dm_med"])


def _any_signal(record):
    """Some diabetes-adjacent trace exists, short of a T2D diagnosis code."""
    f = facts(record)
    return (f["on_dm_med"] or f["abnormal_lab"] or f["ctrl_abnormal_lab"]
            or f["dm_broad_count"] > 0)


ROUTE_PREDICATES = {
    # A closing chain: the rules have everything they need. Note this covers
    # the dx-free P4 path too (treated-but-uncoded) — which fires for zero
    # patients in Coherent, but the bucket is written to accept it rather than
    # to assume the count stays zero.
    "DECISIVE_POS": lambda r: _chain_closes(r),

    # A dx code on file but no path closes. This is the interesting bucket:
    # the patient is coded diabetic and the algorithm still drops them, mostly
    # on the insulin branch — a T1D exclusion doing work in a dataset with no
    # T1D patients. Exactly where a reader would be expected to disagree with
    # the algorithm, so it is the bucket the LLM adjudicates.
    "CONFLICTING": lambda r: _has_dx(r) and not _chain_closes(r),

    # No dx code, no chain, and the control criteria positively rule it out.
    "DECISIVE_NEG": lambda r: (not _has_dx(r) and not _chain_closes(r)
                               and _screened_and_clean(r)),

    # No dx code, not clean either — a med, an odd lab, a prediabetes code.
    # Oblique evidence that never settles the question on its own.
    "INDIRECT": lambda r: (not _has_dx(r) and not _chain_closes(r)
                           and not _screened_and_clean(r) and _any_signal(r)),

    # The record is simply silent. Abstain, which for this phenotype means
    # negative — and the silver standard agrees, since a patient with no T2D
    # code is silver-negative.
    "NO_EVIDENCE": lambda r: (not _has_dx(r) and not _chain_closes(r)
                              and not _screened_and_clean(r) and not _any_signal(r)),
}
