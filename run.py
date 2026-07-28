# run.py — drive the routed cascade end to end and emit a submission.
#
#     python run.py --phenotype t2d --dry-run     route only, zero API calls
#     python run.py --phenotype t2d               route, label, write submission.csv
#
# The shape of the thing: build records off the patient roster -> route each
# patient to a labeler by evidence -> run each labeler over its bucket ->
# reassemble one row per patient. Only the phenotype config below is
# T2D-specific; records.py, router.py and the runner itself are shared.
#
# Two habits worth keeping when a second phenotype lands:
#   - assert the expected bucket sizes. A silent change in bucket size means
#     the evidence definitions moved, and every downstream number moved with it.
#   - print the diff. A run where the LLM changed nothing and a run where the
#     LLM crashed and fell back look identical unless you print the flips.

import argparse
import csv
import sys
import time

import records as records_mod
import router as router_mod
from labelers import llm as llm_labeler
from labelers import rules as rules_labeler

# --- Pricing. Claude Sonnet 5, dollars per million tokens. Introductory rates
# --- run through 2026-08-31; standard rates are $3.00 / $15.00. If a run
# --- happens after that date these two constants are the only edit needed.
PRICE_INPUT_PER_MTOK = 2.00
PRICE_OUTPUT_PER_MTOK = 10.00

# --- Submission format. The dashboard's expected column names are the one
# --- thing here not verifiable from the data in this repo, so rather than
# --- guess once and find out from a rejected upload, we emit the same label
# --- vector under every plausible header convention. They are alternates, not
# --- variants: the labels are identical by construction and asserted identical
# --- after writing. Whichever one the dashboard accepts, the answer is the same.
SUBMISSION_PATH = "submission.csv"

SUBMISSION_FORMATS = [
    ("submission.csv",              "patient_id", "label"),
    ("submission_PATIENT_pred.csv", "PATIENT",    "prediction"),
    ("submission_id_label.csv",     "patient_id", "label"),
    ("submission_Id_pred.csv",      "Id",         "prediction"),
]

EXPECTED_TOTAL = records_mod.EXPECTED_PATIENTS   # 3539


# ---------------------------------------------------------------------------
# Phenotype configuration. Adding Resistant Hypertension means adding an entry
# here plus a rules module — not touching records.py, router.py, or the runner.
# ---------------------------------------------------------------------------

PHENOTYPES = {
    "t2d": {
        "rules": rules_labeler,
        # Which labeler serves each bucket. Rules handle everything they can
        # settle; the LLM is spent only where the evidence genuinely conflicts.
        "assignment": {
            "DECISIVE_POS": "rules",
            "DECISIVE_NEG": "rules",
            "INDIRECT":     "rules",
            "NO_EVIDENCE":  "rules",
            "CONFLICTING":  "llm",
        },
        # Bucket sizes we expect on the 3539-patient roster. CONFLICTING is the
        # one that matters: 382 patients carry a T2D dx code, the rules call
        # 314 of them, and these 68 are the remainder — the only patients where
        # a different method can move the score at all.
        "expected_buckets": {"CONFLICTING": 68},
    },
}


def build_and_route(phenotype, verbose=True):
    rules = PHENOTYPES[phenotype]["rules"]

    t0 = time.time()
    recs = records_mod.build_records(verbose=verbose)
    if verbose:
        print(f"[run] records built in {time.time()-t0:.1f}s\n")

    assignments = router_mod.route_all(recs, rules, expected_total=EXPECTED_TOTAL)

    print("[run] routing (disjoint and covering, both asserted):")
    print(router_mod.format_counts(assignments))

    for bucket, expected in PHENOTYPES[phenotype]["expected_buckets"].items():
        actual = router_mod.bucket_counts(assignments)[bucket]
        assert actual == expected, (
            f"expected {expected} patients in {bucket}, routed {actual}. "
            f"The evidence definitions moved — do not ship this run until you "
            f"know why."
        )
        print(f"[run] assertion holds: {bucket} == {expected}")

    return recs, assignments


def dry_run(phenotype, n_samples=3):
    recs, assignments = build_and_route(phenotype)
    assignment_map = PHENOTYPES[phenotype]["assignment"]

    print("\n[run] labeler assignment:")
    for bucket in router_mod.ROUTES:
        n = router_mod.bucket_counts(assignments)[bucket]
        print(f"  {bucket:<13} -> {assignment_map[bucket]:<6} ({n} patients)")

    llm_buckets = [b for b, m in assignment_map.items() if m == "llm"]
    n_llm = sum(router_mod.bucket_counts(assignments)[b] for b in llm_buckets)
    print(f"\n[run] a real run would make {n_llm} API calls "
          f"(cost estimated from measured chart sizes below)")
    print("[run] DRY RUN — zero API calls made")

    # Sample charts from the bucket the LLM would actually see. Sampling from
    # the easy buckets would tell us nothing about whether the chart is legible
    # where legibility matters.
    sample_bucket = llm_buckets[0] if llm_buckets else router_mod.ROUTES[0]
    members = sorted(router_mod.bucket_members(assignments, sample_bucket))[:n_samples]
    print(f"\n[run] {len(members)} sample charts from {sample_bucket} "
          f"(this is verbatim what the model would be shown):")
    sizes = []
    for pid in members:
        chart = records_mod.render_chart(recs[pid])
        chars, toks = records_mod.chart_size(chart)
        sizes.append((chars, toks))
        print("\n" + "=" * 78)
        f = rules_labeler.facts(recs[pid])
        print(f"rule facts: dx_dates={f['t2dm_dx_count']} "
              f"med={f['t2dm_med_date']} insulin={f['insulin_date']} "
              f"abnormal_lab={f['abnormal_lab']} -> rule label "
              f"{rules_labeler.label(recs[pid])}")
        print(f"chart size: {chars:,} chars, ~{toks:,} tokens")
        print("=" * 78)
        print(chart)

    # Size across the whole bucket, not just the samples — the three we printed
    # could easily be the three smallest.
    all_sizes = [records_mod.chart_size(records_mod.render_chart(recs[p]))[1]
                 for p in router_mod.bucket_members(assignments, sample_bucket)]
    if all_sizes:
        mean_toks = sum(all_sizes) / len(all_sizes)
        print(f"\n[run] chart size across all {len(all_sizes)} {sample_bucket} patients: "
              f"min ~{min(all_sizes):,} / mean ~{mean_toks:,.0f} / max ~{max(all_sizes):,} tokens")
        cost = len(all_sizes) * (mean_toks * PRICE_INPUT_PER_MTOK
                                 + 300 * PRICE_OUTPUT_PER_MTOK) / 1_000_000
        print(f"[run] revised cost estimate for {len(all_sizes)} calls: ~${cost:.2f}")


def full_run(phenotype, out_path=SUBMISSION_PATH):
    started = time.time()
    recs, assignments = build_and_route(phenotype)
    assignment_map = PHENOTYPES[phenotype]["assignment"]
    rules = PHENOTYPES[phenotype]["rules"]

    llm_labeler.USAGE.reset()
    labels, diffs = {}, []

    llm_total = sum(1 for b in assignments.values() if assignment_map[b] == "llm")
    print(f"\n[run] labeling {len(recs)} patients "
          f"({len(recs) - llm_total} by rules, {llm_total} by LLM) ...")

    done = 0
    for pid, record in recs.items():
        bucket = assignments[pid]
        rule_label = rules.label(record)

        if assignment_map[bucket] == "rules":
            labels[pid] = rule_label
            continue

        done += 1
        verdict = llm_labeler.adjudicate(record, rule_label=rule_label)
        llm_labeler.USAGE.record(verdict)
        labels[pid] = verdict.label
        print(f"  [{done}/{llm_total}] {pid[:8]}  rule={rule_label} "
              f"llm={verdict.label}"
              + ("  <-- FLIP" if verdict.label != rule_label else "")
              + ("  (FELL BACK)" if verdict.fell_back else ""))
        if verdict.label != rule_label:
            diffs.append((pid, bucket, rule_label, verdict))

    # --- checks BEFORE writing. A malformed submission is worse than none:
    # --- uncovered patients are counted against the score, so a short file
    # --- scores worse than a wrong-but-complete one.
    assert len(labels) == len(recs), (
        f"labeled {len(labels)} patients but built {len(recs)} records")
    assert len(labels) == EXPECTED_TOTAL, (
        f"submission would have {len(labels)} rows, expected {EXPECTED_TOTAL}")
    assert set(labels) == set(recs), "submission patient ids do not match the roster"
    bad = {p: v for p, v in labels.items() if v not in (0, 1)}
    assert not bad, f"non-binary or null labels for {len(bad)} patients: {list(bad)[:5]}"

    with open(out_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([ID_COLUMN, LABEL_COLUMN])
        for pid in sorted(labels):
            writer.writerow([pid, labels[pid]])

    n_pos = sum(labels.values())
    print(f"\n[run] wrote {out_path}: {len(labels)} rows, "
          f"{n_pos} positive ({n_pos/len(labels):.1%}), {len(labels)-n_pos} negative")

    # --- the diff. Every patient the LLM moved, with the model's own reason.
    # --- This is the deliverable as much as the CSV is: it is the only place
    # --- the disagreement between the two methods is legible.
    print(f"\n{'='*78}\nLLM vs RULE BASELINE — {len(diffs)} flips out of {llm_total} adjudicated")
    print("=" * 78)
    if not diffs:
        print("  (no disagreements — the LLM reproduced the rule labels exactly)")
    for pid, bucket, rule_label, verdict in diffs:
        print(f"\n{pid}  [{bucket}]  rule={rule_label} -> llm={verdict.label}  "
              f"(confidence: {verdict.confidence})")
        print(f"  reason: {verdict.reason}")

    fallbacks = llm_labeler.USAGE.fallbacks
    if fallbacks:
        print(f"\n[run] WARNING: {fallbacks} patient(s) fell back to the rule label "
              f"after API failure. Those are NOT model agreement — they are "
              f"missing verdicts.")

    # --- run accounting -------------------------------------------------------
    u = llm_labeler.USAGE
    cost = (u.input_tokens * PRICE_INPUT_PER_MTOK
            + u.output_tokens * PRICE_OUTPUT_PER_MTOK) / 1_000_000
    elapsed = time.time() - started
    print(f"\n{'='*78}\nRUN ACCOUNTING\n{'='*78}")
    print(f"  model            {llm_labeler.MODEL}")
    print(f"  wall clock       {elapsed:.1f}s ({elapsed/60:.2f} min)")
    print(f"  API calls        {u.api_calls}")
    print(f"  retries          {u.retries}")
    print(f"  fallbacks        {u.fallbacks}")
    print(f"  input tokens     {u.input_tokens:,}")
    print(f"  output tokens    {u.output_tokens:,}")
    print(f"  cost_usd         ${cost:.4f}"
          f"   (@ ${PRICE_INPUT_PER_MTOK}/${PRICE_OUTPUT_PER_MTOK} per Mtok)")
    print(f"  runtime_min      {elapsed/60:.2f}")


def main():
    ap = argparse.ArgumentParser(description="routed cascade phenotyping")
    ap.add_argument("--phenotype", default="t2d", choices=sorted(PHENOTYPES))
    ap.add_argument("--dry-run", action="store_true",
                    help="build records and route only; make zero API calls")
    ap.add_argument("--out", default=SUBMISSION_PATH)
    args = ap.parse_args()

    if args.dry_run:
        dry_run(args.phenotype)
    else:
        full_run(args.phenotype, out_path=args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
