# router.py — assign each patient to exactly one labeler.
#
# The router is the load-bearing idea of the cascade. It decides WHICH method
# gets to answer for a patient, based only on what evidence is present in that
# patient's record. It never looks at a phenotype label, not the rule label and
# not a silver label, because a router that peeks at the answer is not a router
# — it is a way of laundering the answer into the routing decision and then
# congratulating yourself on the accuracy.
#
# This file is phenotype-agnostic. It knows five bucket names and two
# invariants. Everything specific to T2D or Resistant Hypertension lives in the
# rules module that gets passed in, which must expose:
#
#     rules.ROUTE_PREDICATES : {bucket_name: callable(record) -> bool}
#
# The two invariants, both asserted rather than hoped for:
#
#   DISJOINT  every patient matches exactly one predicate. Not "the first one
#             that fires wins" — genuinely one. First-match-wins hides the case
#             where two buckets overlap, and the overlap is exactly where the
#             interesting patients are.
#   COVERING  every patient in the roster gets routed. An unrouted patient is
#             an unlabeled patient, and the dashboard counts uncovered patients
#             against the score.

ROUTES = (
    "DECISIVE_POS",   # evidence is sufficient and points one way: positive
    "DECISIVE_NEG",   # evidence is sufficient and points one way: negative
    "CONFLICTING",    # evidence exists on both sides, or the chain doesn't close
    "INDIRECT",       # only oblique evidence — nothing that settles it
    "NO_EVIDENCE",    # the record is silent on this phenotype
)


def route(record, rules):
    """Return the bucket for one patient. Asserts disjointness on the spot."""
    matched = [name for name in ROUTES if rules.ROUTE_PREDICATES[name](record)]
    assert len(matched) == 1, (
        f"routing is not disjoint for patient {record['id']}: matched {matched or 'nothing'}"
    )
    return matched[0]


def route_all(records, rules, expected_total=None):
    """Route every patient. Returns {patient_id: bucket}.

    Coverage is checked here rather than left to the caller: routing 3538 of
    3539 patients without noticing is exactly the failure this exists to catch.
    """
    assignments = {pid: route(rec, rules) for pid, rec in records.items()}

    assert len(assignments) == len(records), "routing dropped patients"
    assert set(assignments) == set(records), "routing invented or lost patient ids"
    if expected_total is not None:
        assert len(assignments) == expected_total, (
            f"routed {len(assignments)} patients, expected {expected_total}"
        )
    return assignments


def bucket_counts(assignments):
    """Counts in declared bucket order, zeros included — a bucket that never
    fires is a fact worth seeing, not a row to omit."""
    counts = {name: 0 for name in ROUTES}
    for bucket in assignments.values():
        counts[bucket] += 1
    return counts


def bucket_members(assignments, bucket):
    return [pid for pid, b in assignments.items() if b == bucket]


def format_counts(assignments):
    counts = bucket_counts(assignments)
    total = sum(counts.values())
    lines = []
    for name in ROUTES:
        n = counts[name]
        lines.append(f"  {name:<13} {n:>5}  ({n/total:>5.1%})")
    lines.append(f"  {'TOTAL':<13} {total:>5}")
    return "\n".join(lines)
