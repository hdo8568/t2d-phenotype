# run.py — drive the routed cascade end to end and emit a submission.
#
#     python run.py --phenotype t2d --dry-run     route only, zero API calls
#     python run.py --phenotype t2d               cascade: LLM on CONFLICTING only
#     python run.py --phenotype t2d --all         full cohort: LLM on all 3539
#     python run.py --phenotype t2d --all --limit 20    smoke test
#     python run.py --phenotype t2d --all --resume      pick up a killed run
#
# Two modes, and the difference between them is the whole point:
#
#   CASCADE (default)  the LLM sees only the 68 patients where the evidence
#                      conflicts. Cheap, and it caps agreement with the silver
#                      standard at roughly what the rules already achieve.
#   FULL COHORT (--all) every patient goes to the model. This is not an attempt
#                      to win on F1 — it is a measurement. Every T2D submission
#                      on the dashboard reports cost_usd = 0 because every one
#                      of them is deterministic. The contribution here is a
#                      real per-patient agentic method with its cost, latency
#                      and divergence from the rules actually measured.
#
# Only the phenotype config below is T2D-specific; records.py, router.py and
# the runner itself are shared with whatever phenotype comes next.

import argparse
import csv
import json
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

import records as records_mod
import router as router_mod
from labelers import llm as llm_labeler
from labelers import rules as rules_labeler

# --- Pricing. Claude Sonnet 5, dollars per million tokens. Introductory rates
# --- run through 2026-08-31; standard rates are $3.00 / $15.00. Cache writes
# --- bill at 1.25x base input, cache reads at 0.10x. If a run happens after
# --- that date these four constants are the only edit needed.
PRICE_INPUT_PER_MTOK = 2.00
PRICE_OUTPUT_PER_MTOK = 10.00
PRICE_CACHE_WRITE_PER_MTOK = PRICE_INPUT_PER_MTOK * 1.25
PRICE_CACHE_READ_PER_MTOK = PRICE_INPUT_PER_MTOK * 0.10

# Spend gate. Above this, a human says yes before any tokens are bought.
COST_CONFIRM_THRESHOLD_USD = 25.00

# Concurrency and durability. Rate limiting is the failure mode that does not
# announce itself — it just turns into a pile of fallbacks that look like
# results. So 16 is a CEILING, not a commitment: the governor below halves it
# on sustained 429s, and 4 is where this backs off toward rather than where it
# starts. Measured at 16: ~1.5 patients/s, full cohort in ~35 minutes, zero
# 429s and zero halvings.
START_WORKERS = 16
MIN_WORKERS = 1
RATE_LIMIT_WINDOW = 100          # patients per window
RATE_LIMIT_HALVE_THRESHOLD = 0.05
CHECKPOINT_EVERY = 100
CHECKPOINT_PATH = "run_checkpoint.jsonl"
PROGRESS_COST_EVERY = 500

# The most dangerous failure this pipeline has is not a crash — it is a run
# where API calls fail, patients quietly fall back to their rule labels, and
# the submission on disk is the rule baseline wearing an LLM's name. It would
# score fine and mean nothing. Above this rate the run stops, writes what it
# has, and says so loudly.
FALLBACK_ABORT_RATE = 0.05

# Hard ceiling on spend, checked live against measured tokens. Not a
# projection — the run stops when real money crosses this line.
HARD_COST_ABORT_USD = 40.00

FAILURES_PATH = "FAILURES.md"

# --- Submission format. The dashboard's expected column names are the one
# --- thing here not verifiable from the data in this repo, so rather than
# --- guess once and find out from a rejected upload, we emit the same label
# --- vector under every plausible header convention. They are alternates, not
# --- variants: identical by construction and asserted identical after writing.
SUBMISSION_FORMATS = [
    ("submission.csv",              "patient_id", "label"),
    ("submission_PATIENT_pred.csv", "PATIENT",    "prediction"),
    ("submission_id_label.csv",     "patient_id", "label"),
    ("submission_Id_pred.csv",      "Id",         "prediction"),
]

RUN_LOG_PATH = "run_log.csv"
DIVERGENCE_PATH = "divergence.csv"
RESULTS_PATH = "RESULTS.md"
COHORT_PATH = "t2d_cohort.csv"

EXPECTED_TOTAL = records_mod.EXPECTED_PATIENTS   # 3539


PHENOTYPES = {
    "t2d": {
        "rules": rules_labeler,
        "assignment": {
            "DECISIVE_POS": "rules",
            "DECISIVE_NEG": "rules",
            "INDIRECT":     "rules",
            "NO_EVIDENCE":  "rules",
            "CONFLICTING":  "llm",
        },
        # 382 patients carry a T2D dx code, the rules call 314 of them, and
        # these 68 are the remainder — in cascade mode, the only patients where
        # a different method can move the score at all.
        "expected_buckets": {"CONFLICTING": 68},
    },
}


# ---------------------------------------------------------------------------
# Stage 1 — records and routing
# ---------------------------------------------------------------------------

def build_and_route(phenotype, verbose=True):
    rules = PHENOTYPES[phenotype]["rules"]

    t0 = time.time()
    # load_notes=False: diagnostic_reports.csv is 172 MB and the chart does not
    # render notes. Adding them would change the chart and break comparability
    # with the measured token counts.
    recs = records_mod.build_records(verbose=verbose, load_notes=False)
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


# ---------------------------------------------------------------------------
# Stage 2 — cost projection, from measured charts rather than guesses
# ---------------------------------------------------------------------------

def project_cost(charts, assumed_output_tokens):
    """Project spend from real chart sizes. Input is measured; output is the
    assumption, and it is the one worth distrusting — thinking tokens bill as
    output, so a smoke test's measured output is far better than this guess."""
    in_toks = [records_mod.chart_size(c)[1] for c in charts]
    total_in = sum(in_toks) + len(charts) * 300      # + system prompt overhead
    total_out = len(charts) * assumed_output_tokens
    cost = (total_in * PRICE_INPUT_PER_MTOK
            + total_out * PRICE_OUTPUT_PER_MTOK) / 1_000_000
    return {
        "n": len(charts),
        "input_tokens": total_in,
        "output_tokens": total_out,
        "min_in": min(in_toks) if in_toks else 0,
        "mean_in": statistics.mean(in_toks) if in_toks else 0,
        "max_in": max(in_toks) if in_toks else 0,
        "cost": cost,
    }


def print_projection(proj, label, assumed_output_tokens):
    print(f"\n[run] PROJECTED COST — {label}")
    print(f"  patients            {proj['n']:,}")
    print(f"  chart tokens        min {proj['min_in']:,} / "
          f"mean {proj['mean_in']:,.0f} / max {proj['max_in']:,}")
    print(f"  projected input     {proj['input_tokens']:,} tokens")
    print(f"  projected output    {proj['output_tokens']:,} tokens "
          f"(assuming {assumed_output_tokens}/call)")
    print(f"  PROJECTED COST      ${proj['cost']:.2f}")


def confirm_spend(cost, assume_yes):
    """Above the threshold, a human says yes. Non-interactive runs must pass
    --yes explicitly rather than have consent inferred from a missing tty."""
    if cost <= COST_CONFIRM_THRESHOLD_USD:
        return True
    print(f"\n[run] projected ${cost:.2f} exceeds the "
          f"${COST_CONFIRM_THRESHOLD_USD:.2f} confirmation threshold.")
    if assume_yes:
        print("[run] --yes given; proceeding.")
        return True
    if not sys.stdin.isatty():
        print("[run] no tty and no --yes — refusing to spend. Re-run with --yes.")
        return False
    reply = input(f"[run] proceed and spend ~${cost:.2f}? [y/N] ").strip().lower()
    return reply in ("y", "yes")


# ---------------------------------------------------------------------------
# Stage 2b — preflight. Everything here must pass before bulk calls begin.
# ---------------------------------------------------------------------------

class PreflightReport:
    """Collects PASS/FAIL lines so the whole preflight prints as one block
    rather than as scattered asserts."""

    def __init__(self):
        self.rows = []
        self.ok = True

    def check(self, name, passed, detail=""):
        self.rows.append((name, bool(passed), detail))
        if not passed:
            self.ok = False
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
        return passed

    def summary(self):
        n_pass = sum(1 for _, p, _ in self.rows if p)
        return f"{n_pass}/{len(self.rows)} preflight checks passed"


def check_roster_integrity(report, recs):
    """Preflight 3: the spine is patients.csv and nothing else.

    conditions.csv and medications.csv are each missing patients (4 and 92).
    Building the index off either silently shortens the submission, and an
    uncovered patient is scored against us. So we prove the index came from
    patients.csv by showing it still contains the patients the other tables
    lack.
    """
    patients = pd.read_csv("patients.csv")
    ids = patients["Id"]
    report.check("patients.csv has exactly 3539 rows", len(ids) == EXPECTED_TOTAL,
                 f"{len(ids)} rows")
    report.check("patients.csv IDs are unique", ids.nunique() == len(ids),
                 f"{ids.nunique()} unique")
    report.check("record index == patients.csv IDs, in order",
                 list(recs.keys()) == list(ids),
                 f"{len(recs)} records")

    cond_ids = set(pd.read_csv("conditions.csv", usecols=["PATIENT"])["PATIENT"])
    med_ids = set(pd.read_csv("medications.csv", usecols=["PATIENT"])["PATIENT"])
    missing_cond = set(ids) - cond_ids
    missing_med = set(ids) - med_ids
    report.check("index is NOT built from conditions.csv",
                 missing_cond and missing_cond <= set(recs),
                 f"{len(missing_cond)} patients absent from conditions are present "
                 f"in the index")
    report.check("index is NOT built from medications.csv",
                 missing_med and missing_med <= set(recs),
                 f"{len(missing_med)} patients absent from medications are present "
                 f"in the index")


def check_env_in_worker(report):
    """Preflight 2: the key resolves inside a worker thread, not just here.

    os.environ is process-wide so this should hold trivially — but "should" is
    how you end up with 3539 fallbacks, so it is proven rather than assumed.
    """
    print(f"  resolved model string: {llm_labeler.resolved_model()}")
    main_ok = bool(os.getenv("ANTHROPIC_API_KEY"))
    with ThreadPoolExecutor(max_workers=2) as pool:
        worker_ok = pool.submit(lambda: bool(os.getenv("ANTHROPIC_API_KEY"))).result()
        worker_model = pool.submit(llm_labeler.resolved_model).result()
    report.check("ANTHROPIC_API_KEY visible on main thread", main_ok,
                 "set" if main_ok else "NOT SET — export it or add it to .env")
    report.check("ANTHROPIC_API_KEY visible inside worker thread", worker_ok,
                 "set" if worker_ok else "NOT SET inside worker")
    report.check("model string identical inside worker thread",
                 worker_model == llm_labeler.resolved_model(), worker_model)
    return main_ok and worker_ok


def preflight(recs, effort, skip_api=False):
    """Run every pre-bulk check. Returns (report, ok_to_proceed)."""
    print(f"\n{'='*78}\nPREFLIGHT\n{'='*78}")
    report = PreflightReport()

    check_roster_integrity(report, recs)
    have_key = check_env_in_worker(report)

    if skip_api:
        print("  [SKIP] single live API call (--skip-preflight-call)")
        return report, report.ok

    if not have_key:
        report.check("single live API call", False,
                     "no API key — cannot make the call. STOPPING before bulk calls.")
        return report, False

    print("  making ONE live API call ...")
    ok, info = llm_labeler.preflight_call(effort=effort)
    if not ok:
        report.check("single live API call", False, info.get("error", "unknown"))
        if info.get("fatal"):
            print("  -> fatal (auth / model string / missing package). "
                  "NOT retrying in a loop.")
        return report, False

    print(f"    status          ok")
    print(f"    model requested {info['model_requested']}")
    print(f"    model echoed    {info['model_echoed']}")
    print(f"    stop_reason     {info['stop_reason']}")
    print(f"    input tokens    {info['input_tokens']}")
    print(f"    output tokens   {info['output_tokens']}")
    print(f"    cache w/r       {info['cache_creation_tokens']} / {info['cache_read_tokens']}")
    print(f"    latency         {info['latency_s']:.2f}s")
    report.check("single live API call", True,
                 f"{info['latency_s']:.2f}s, {info['output_tokens']} output tokens")
    report.check("response parses to a label in {0,1}",
                 _preflight_parses(info["raw_text"]),
                 "schema-valid verdict")
    report.check("response was not truncated", info["stop_reason"] != "max_tokens",
                 f"stop_reason={info['stop_reason']}")
    return report, report.ok


def _preflight_parses(raw):
    try:
        label, _, _ = llm_labeler._parse_verdict(raw)
        return label in (0, 1)
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Stage 2c — concurrency governor
# ---------------------------------------------------------------------------

class ConcurrencyGovernor:
    """Adaptive in-flight limit. Starts at START_WORKERS and halves whenever
    429s exceed the threshold over a window.

    A semaphore rather than a resized pool: you cannot change a
    ThreadPoolExecutor's width after construction, but you can starve it.
    """

    def __init__(self, start=START_WORKERS, window=RATE_LIMIT_WINDOW,
                 threshold=RATE_LIMIT_HALVE_THRESHOLD):
        self.limit = start
        self.window = window
        self.threshold = threshold
        self._sem = threading.Semaphore(start)
        self._lock = threading.Lock()
        self._window_calls = 0
        self._window_429s = 0
        self.halvings = []

    def acquire(self):
        self._sem.acquire()

    def release(self):
        self._sem.release()

    def note_rate_limit(self):
        with self._lock:
            self._window_429s += 1

    def note_completion(self):
        """Called once per patient. Closes the window and adapts if needed."""
        with self._lock:
            self._window_calls += 1
            if self._window_calls < self.window:
                return
            rate = self._window_429s / self._window_calls
            if rate > self.threshold and self.limit > MIN_WORKERS:
                new_limit = max(MIN_WORKERS, self.limit // 2)
                # Starve the semaphore down to the new limit.
                for _ in range(self.limit - new_limit):
                    self._sem.acquire()
                print(f"  [GOVERNOR] 429 rate {rate:.1%} over last "
                      f"{self._window_calls} patients — halving concurrency "
                      f"{self.limit} -> {new_limit}", flush=True)
                self.halvings.append({"at_patient": None, "rate": rate,
                                      "from": self.limit, "to": new_limit})
                self.limit = new_limit
            self._window_calls = 0
            self._window_429s = 0


# ---------------------------------------------------------------------------
# Stage 3 — checkpointing
# ---------------------------------------------------------------------------

def load_checkpoint(path=CHECKPOINT_PATH, include_fallbacks=False):
    """Rows already adjudicated in a previous run, keyed by patient id.

    Fallback rows are EXCLUDED by default, and that is the whole subtlety of
    resume. A fallback is not a completed patient — it is a patient whose call
    failed and who is currently wearing a rule label. If resume treated it as
    done, the failure would be frozen into the submission permanently and the
    resumed run would look complete while quietly carrying every failure from
    the run before it. Resume exists to retry exactly these.
    """
    if not os.path.exists(path):
        return {}
    done, skipped = {}, 0
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue          # a torn final line from a killed run
            if row.get("fell_back") and not include_fallbacks:
                skipped += 1
                continue
            done[row["patient_id"]] = row
    if skipped:
        print(f"[run] checkpoint holds {skipped} fallback row(s) — these will be "
              f"RETRIED, not treated as done")
    return done


class Checkpointer:
    """Append-only JSONL, flushed every N patients. Append-only on purpose: a
    run killed mid-flight leaves a readable file, and at worst loses the tail."""

    def __init__(self, path=CHECKPOINT_PATH, every=CHECKPOINT_EVERY):
        self.path = path
        self.every = every
        self.pending = []
        self.count = 0
        self._lock = threading.Lock()

    def add(self, row):
        with self._lock:
            self.pending.append(row)
            self.count += 1
            if len(self.pending) >= self.every:
                self._flush_locked()

    def _flush_locked(self):
        if not self.pending:
            return
        with open(self.path, "a") as fh:
            for row in self.pending:
                fh.write(json.dumps(row) + "\n")
        self.pending = []

    def flush(self):
        with self._lock:
            self._flush_locked()


# ---------------------------------------------------------------------------
# Stage 4 — labeling
# ---------------------------------------------------------------------------

def live_cost():
    return llm_labeler.USAGE.cost(PRICE_INPUT_PER_MTOK, PRICE_OUTPUT_PER_MTOK,
                                  PRICE_CACHE_WRITE_PER_MTOK, PRICE_CACHE_READ_PER_MTOK)


def adjudicate_many(targets, recs, rule_labels, charts, effort, checkpoint):
    """Run the LLM over `targets` with an adaptively-throttled worker pool.

    Returns (results, stop_reason). Three things can stop it early, and all
    three write the checkpoint first: the spend ceiling, the fallback ceiling,
    and a fatal credential/model error.
    """
    results = {}
    started = time.time()
    total = len(targets)
    progress_lock = threading.Lock()
    done_count = [0]
    fallback_count = [0]
    stop_reason = [None]
    abort = threading.Event()
    governor = ConcurrencyGovernor()

    def work(pid):
        if abort.is_set():
            return pid, None
        verdict = llm_labeler.adjudicate(
            recs[pid], rule_label=rule_labels[pid], chart=charts[pid], effort=effort,
            governor=governor)
        llm_labeler.USAGE.record(verdict)
        return pid, verdict

    # The pool is wider than the governor's limit on purpose: the governor is
    # what actually gates concurrent calls, so it can throttle below the pool
    # width without the pool needing to be rebuilt.
    with ThreadPoolExecutor(max_workers=max(START_WORKERS, 8)) as pool:
        futures = [pool.submit(work, pid) for pid in targets]
        for future in as_completed(futures):
            pid, verdict = future.result()
            if verdict is None:
                continue
            governor.note_completion()
            row = {
                "patient_id": pid,
                "rule_label": rule_labels[pid],
                "llm_label": verdict.label,
                "confidence": verdict.confidence,
                "reason": verdict.reason,
                "input_tokens": verdict.input_tokens,
                "output_tokens": verdict.output_tokens,
                "cache_read_tokens": verdict.cache_read_tokens,
                "cache_creation_tokens": verdict.cache_creation_tokens,
                "latency_s": round(verdict.latency_s, 3),
                "attempts": verdict.attempts,
                "api_calls": verdict.api_calls,
                "fell_back": int(verdict.fell_back),
                "rate_limited": int(verdict.rate_limited),
                "truncated": int(verdict.truncated),
                "refused": int(verdict.refused),
                "empty": int(verdict.empty),
                "parse_failed": int(verdict.parse_failed),
            }
            results[pid] = row
            checkpoint.add(row)

            with progress_lock:
                if verdict.fell_back:
                    # Loud, per patient, at the moment it happens. A fallback
                    # buried in an end-of-run total is a fallback nobody sees.
                    fallback_count[0] += 1
                    print(f"  [FALLBACK] {pid[:8]} after {verdict.attempts} attempt(s): "
                          f"{verdict.errors[-1][:160] if verdict.errors else 'unknown'}",
                          flush=True)
                done_count[0] += 1
                n = done_count[0]

                if n % 25 == 0 or n == total:
                    elapsed = time.time() - started
                    rate = n / elapsed if elapsed else 0
                    eta = (total - n) / rate if rate else 0
                    print(f"  [{n}/{total}] {rate:.1f} pt/s  "
                          f"elapsed {elapsed/60:.1f}m  eta {eta/60:.1f}m", flush=True)
                if n % PROGRESS_COST_EVERY == 0:
                    print(f"  [COST] ${live_cost():.4f} spent after {n} patients "
                          f"(concurrency {governor.limit})", flush=True)

                # --- live abort conditions, checked every patient -------------
                if not abort.is_set():
                    cost_now = live_cost()
                    if cost_now >= HARD_COST_ABORT_USD:
                        stop_reason[0] = (f"hard cost ceiling: ${cost_now:.2f} >= "
                                          f"${HARD_COST_ABORT_USD:.2f}")
                        abort.set()
                    elif (n >= 20 and fallback_count[0] / n > FALLBACK_ABORT_RATE):
                        stop_reason[0] = (
                            f"fallback rate {fallback_count[0]}/{n} "
                            f"({fallback_count[0]/n:.1%}) exceeds "
                            f"{FALLBACK_ABORT_RATE:.0%} — these are not LLM labels")
                        abort.set()
                    if abort.is_set():
                        print(f"\n  [ABORT] {stop_reason[0]}", flush=True)
                        print("  [ABORT] draining in-flight calls and writing "
                              "the checkpoint ...", flush=True)

    checkpoint.flush()
    return results, stop_reason[0], governor


# ---------------------------------------------------------------------------
# Stage 5 — outputs
# ---------------------------------------------------------------------------

def write_submissions(labels, roster_order):
    """Write every header convention from one label vector, then prove they
    agree. IDs are written exactly as they appear in patients.csv — no case
    change, no stripping, no reordering."""
    written = []
    for path, id_col, label_col in SUBMISSION_FORMATS:
        with open(path, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow([id_col, label_col])
            for pid in roster_order:
                writer.writerow([pid, int(labels[pid])])
        written.append(path)

    # Read all four back and assert the label vectors are identical. Writing
    # four files from one dict and then trusting them is not verification.
    vectors, id_vectors = {}, {}
    for path, _, _ in SUBMISSION_FORMATS:
        frame = pd.read_csv(path, dtype=str)
        id_vectors[path] = frame.iloc[:, 0].tolist()
        vectors[path] = frame.iloc[:, 1].astype(int).tolist()

    reference = vectors[SUBMISSION_FORMATS[0][0]]
    reference_ids = id_vectors[SUBMISSION_FORMATS[0][0]]
    for path in vectors:
        assert vectors[path] == reference, f"{path} label vector differs"
        assert id_vectors[path] == reference_ids, f"{path} id vector differs"
        assert len(vectors[path]) == EXPECTED_TOTAL, f"{path} is not {EXPECTED_TOTAL} rows"
    print(f"\n[run] all {len(written)} submission files agree "
          f"({EXPECTED_TOTAL} rows, identical labels and ids)")

    for path, _, _ in SUBMISSION_FORMATS:
        print(f"\n--- {path} (first 3 lines) ---")
        with open(path) as fh:
            for line in list(fh)[:3]:
                print("   " + line.rstrip())
    return written


def write_run_log(rows, path=RUN_LOG_PATH):
    fields = ["patient_id", "bucket", "rule_label", "llm_label", "confidence",
              "input_tokens", "output_tokens", "cache_read_tokens",
              "cache_creation_tokens", "latency_s", "attempts", "api_calls",
              "fell_back", "truncated", "refused", "empty", "parse_failed", "reason"]
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"[run] wrote {path} ({len(rows)} rows)")


def write_divergence(rows, cohort, path=DIVERGENCE_PATH):
    """Every patient where the model disagreed with the frozen rule baseline.

    This file, not the submission, is the interesting artifact: it is where a
    reader can check whether the model is finding real misses or inventing
    diabetes out of an elevated triglyceride.
    """
    fields = ["patient_id", "rule_status", "rule_label", "llm_label", "direction",
              "has_t2d_dx_code", "t2dm_dx_count", "confidence", "reason"]
    out = []
    for row in rows:
        if row["llm_label"] == row["rule_label"] or row.get("fell_back"):
            continue
        pid = row["patient_id"]
        cohort_row = cohort.loc[pid] if pid in cohort.index else None
        dx_count = int(cohort_row["t2dm_dx_count"]) if cohort_row is not None else 0
        out.append({
            "patient_id": pid,
            "rule_status": cohort_row["status"] if cohort_row is not None else "?",
            "rule_label": row["rule_label"],
            "llm_label": row["llm_label"],
            "direction": "rule_neg_llm_pos" if row["llm_label"] == 1 else "rule_pos_llm_neg",
            "has_t2d_dx_code": int(dx_count > 0),
            "t2dm_dx_count": dx_count,
            "confidence": row["confidence"],
            "reason": row["reason"],
        })
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out)
    print(f"[run] wrote {path} ({len(out)} divergences)")
    return out


def write_preflight_failure_md(report, path=FAILURES_PATH):
    """Preflight failing IS an abort, and gets the same treatment: written
    down, not just printed into a scrollback nobody keeps."""
    failed = [(n, d) for n, p, d in report.rows if not p]
    lines = [
        "# Run aborted at preflight",
        "",
        "No bulk API calls were made. Nothing was written and nothing was spent.",
        "",
        f"**{report.summary()}**",
        "",
        "## Failed checks",
        "",
        "| check | detail |",
        "| --- | --- |",
    ]
    lines += [f"| {name} | {detail} |" for name, detail in failed]
    lines += [
        "",
        "## Passed checks",
        "",
    ] + [f"- {name}" + (f" — {detail}" if detail else "")
         for name, p, detail in report.rows if p]
    lines += [
        "",
        "## To proceed",
        "",
        "```bash",
        "export ANTHROPIC_API_KEY=sk-ant-...      # or add it to .env",
        "/Users/henry/miniforge3/bin/python3 run.py --all --limit 20   # smoke test",
        "/Users/henry/miniforge3/bin/python3 run.py --all --yes        # full cohort",
        "```",
        "",
        "Preflight makes exactly one API call to prove the key and model string",
        "before spending anything on the other 3538 patients.",
        "",
    ]
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"[run] wrote {path}")


def write_failures_md(stop_reason, fresh, n_fell_back, n_targets, governor,
                      path=FAILURES_PATH):
    u = llm_labeler.USAGE
    lines = [
        "# Run aborted",
        "",
        f"**Reason:** {stop_reason}",
        "",
        "| | |",
        "| --- | --- |",
        f"| patients targeted | {n_targets:,} |",
        f"| patients adjudicated before abort | {len(fresh):,} |",
        f"| of those, fell back to the rule label | {n_fell_back:,} |",
        f"| API calls | {u.api_calls:,} |",
        f"| 429s seen | {u.rate_limit_hits:,} |",
        f"| parse failures | {u.parse_failures:,} |",
        f"| refusals | {u.refusals:,} |",
        f"| empty responses | {u.empty_responses:,} |",
        f"| truncated responses | {u.truncations:,} |",
        f"| spend before abort | ${live_cost():.4f} |",
        f"| final concurrency | {governor.limit} |",
        "",
        "No submission was written. A partial cohort is scored as wrong on every",
        "patient it omits, and a cohort padded out with rule labels is not an LLM",
        "run — it is the baseline wearing a different name.",
        "",
        f"Adjudicated work is preserved in `{CHECKPOINT_PATH}`. Fix the cause and",
        "re-run with `--resume`; already-labeled patients will not be re-called.",
        "",
    ]
    if fresh:
        sample = next((r for r in fresh.values() if r["fell_back"]), None)
        if sample:
            lines += ["## Representative failure", "", "```",
                      str(sample["reason"])[:800], "```", ""]
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"[run] wrote {path}")


def write_results_md(stats, path=RESULTS_PATH):
    lines = [
        "# Full-cohort agentic T2D phenotyping — measured run",
        "",
        "Every T2D submission on the dashboard to date is deterministic and reports",
        "`cost_usd = 0`. This one does not. What follows is measured, not estimated.",
        "",
        "## Run integrity — read this first",
        "",
        "| check | count | meaning |",
        "| --- | --- | --- |",
        f"| fallbacks to rule label | **{stats['fallbacks']:,}** | "
        f"patients with no LLM verdict; NOT model agreement |",
        f"| parse failures (all recovered by retry) | {stats['parse_recovered']:,} | "
        f"a response hit the token ceiling mid-JSON; the retry succeeded |",
        f"| parse failures (unrecovered) | **{stats['parse_unrecovered']:,}** | "
        f"never parsed, raw text in `parse_failures.log` |",
        f"| refusals | {stats['refusals']:,} | model declined to answer |",
        f"| empty responses | {stats['empty_responses']:,} | no text returned |",
        f"| truncated responses | {stats['truncations']:,} | hit the max_tokens ceiling |",
        f"| 429s absorbed | {stats['rate_limit_hits']:,} | retried with backoff |",
        "",
    ]

    if stats["n_divergent"] == 0:
        lines += [
            "> ### The LLM added nothing.",
            "> Zero patients diverge from the rule baseline. Every label in this",
            "> submission is one the rules would have produced for free and in",
            "> under a second. Whatever this run cost, it bought no new information.",
            "",
        ]
    else:
        lines += [
            f"> **{stats['n_divergent']:,} of {stats['n_llm']:,} adjudicated patients "
            f"({stats['divergence_rate']:.1%}) diverge from the rule baseline** — "
            f"{stats['n_rule_neg_llm_pos']:,} negative->positive, "
            f"{stats['n_rule_pos_llm_neg']:,} positive->negative.",
            "",
        ]

    lines += [
        "## Method",
        "",
        f"- Model: `{stats['model']}`, one call per patient, "
        f"reasoning effort `{stats['effort']}`.",
        f"- Mode: **{stats['mode']}** — {stats['n_llm']:,} of {stats['n_total']:,} "
        f"patients adjudicated by the LLM; the remainder carry the rule label.",
        "- Chart: structured render of demographics, conditions, collapsed",
        "  medications, a 13-test metabolic lab panel, encounter counts and care",
        "  plans. Clinical notes were deliberately **not** included, to keep the",
        "  chart identical to the one the cost projection was measured on.",
        f"- Concurrency: started at {stats['start_workers']} workers, "
        + (f"**reduced to {stats['final_workers']} by the 429 backoff logic "
           f"({stats['halvings']} halving(s))**."
           if stats["halvings"] else
           f"never throttled — finished at {stats['final_workers']}."),
        "  Retries on 429/503 with exponential backoff and jitter; on repeated",
        "  failure the patient falls back to the rule label and is recorded as a",
        "  fallback rather than as agreement.",
        "",
        "## Cost and latency",
        "",
        "| metric | value |",
        "| --- | --- |",
        f"| wall clock | **{stats['wall_min']:.2f} min**"
        + (f" (final pass only; {stats['resumed_from_prior']:,} patients were "
           f"labeled in an earlier pass and resumed from checkpoint)"
           if stats["resumed_from_prior"] else "") + " |",
        f"| API calls | {stats['api_calls']:,} |",
        f"| input tokens | {stats['input_tokens']:,} |",
        f"| output tokens | {stats['output_tokens']:,} |",
        f"| cache write tokens | {stats['cache_creation_tokens']:,} |",
        f"| cache read tokens | {stats['cache_read_tokens']:,} |",
        f"| **total cost** | **${stats['cost']:.4f}** |",
        f"| cost per patient | ${stats['cost_per_patient']:.5f} |",
        f"| mean latency | {stats['mean_latency']:.2f} s |",
        f"| median latency | {stats['median_latency']:.2f} s |",
        f"| p95 latency | {stats['p95_latency']:.2f} s |",
        f"| retries | {stats['retries']:,} |",
        f"| fallbacks | {stats['fallbacks']:,} |",
        "",
        f"Pricing: ${PRICE_INPUT_PER_MTOK:.2f}/MTok input, "
        f"${PRICE_OUTPUT_PER_MTOK:.2f}/MTok output "
        f"(Sonnet introductory rates, valid through 2026-08-31).",
        "",
    ]

    if stats["cache_creation_tokens"] == 0 and stats["cache_read_tokens"] == 0:
        lines += [
            "**On prompt caching.** The system prompt is identical across every call",
            "and is sent with `cache_control`, but it is roughly 275 tokens and the",
            "minimum cacheable prefix on Sonnet is 1024. The cache therefore never",
            "engages, which is exactly what the two zero rows above report. Caching",
            "would only pay here if the shared prefix were padded past the minimum —",
            "worth doing deliberately, not worth pretending already happened.",
            "",
        ]

    lines += [
        "## Divergence from the rule baseline",
        "",
        f"- Patients adjudicated by the LLM: **{stats['n_llm']:,}**",
        f"- Labels matching the rule baseline: **{stats['n_agree']:,}**",
        f"- Divergent from the PheKB rule label: **{stats['n_divergent']:,}** "
        f"({stats['divergence_rate']:.1%} of adjudicated)",
        f"  - rules negative -> LLM positive: **{stats['n_rule_neg_llm_pos']:,}**",
        f"  - rules positive -> LLM negative: **{stats['n_rule_pos_llm_neg']:,}**",
        f"- Of the rule-negative flips, **{stats['n_flip_with_dx']:,}** carry a T2D",
        "  diagnosis code and " f"{stats['n_flip_without_dx']:,} do not.",
        "",
        f"Final submission: **{stats['n_positive']:,} positive** / "
        f"{stats['n_negative']:,} negative out of {stats['n_total']:,}.",
        f"The frozen rule baseline calls {stats['n_rule_positive']:,} positive.",
        "",
        "The flips with a diagnosis code are the defensible ones: those patients are",
        "coded diabetic and were dropped by the algorithm's insulin branch, a Type 1",
        "exclusion doing work in a dataset with no Type 1 patients. The flips without",
        "a diagnosis code are the risky ones — against a silver standard derived from",
        "the rules themselves, they can only cost precision, however clinically",
        "reasonable the model's stated reason is. `divergence.csv` has every case with",
        "the model's own words.",
        "",
        "## Files",
        "",
        "| file | contents |",
        "| --- | --- |",
        "| `submission.csv` | 3539 rows, `patient_id,label` |",
        "| `submission_PATIENT_pred.csv` | same labels, `PATIENT,prediction` |",
        "| `submission_id_label.csv` | same labels, `patient_id,label` |",
        "| `submission_Id_pred.csv` | same labels, `Id,prediction` |",
        "| `run_log.csv` | per patient: label, reason, tokens, latency, attempts |",
        "| `divergence.csv` | every disagreement with the rules, with reasons |",
    ]
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"[run] wrote {path}")


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def dry_run(phenotype, n_samples=3):
    recs, assignments = build_and_route(phenotype)
    assignment_map = PHENOTYPES[phenotype]["assignment"]

    print("\n[run] labeler assignment:")
    for bucket in router_mod.ROUTES:
        n = router_mod.bucket_counts(assignments)[bucket]
        print(f"  {bucket:<13} -> {assignment_map[bucket]:<6} ({n} patients)")

    llm_buckets = [b for b, m in assignment_map.items() if m == "llm"]
    n_llm = sum(router_mod.bucket_counts(assignments)[b] for b in llm_buckets)
    print(f"\n[run] a real cascade run would make {n_llm} API calls")
    print("[run] DRY RUN — zero API calls made")

    sample_bucket = llm_buckets[0] if llm_buckets else router_mod.ROUTES[0]
    members = sorted(router_mod.bucket_members(assignments, sample_bucket))[:n_samples]
    print(f"\n[run] {len(members)} sample charts from {sample_bucket} "
          f"(this is verbatim what the model would be shown):")
    for pid in members:
        chart = records_mod.render_chart(recs[pid])
        chars, toks = records_mod.chart_size(chart)
        print("\n" + "=" * 78)
        f = rules_labeler.facts(recs[pid])
        print(f"rule facts: dx_dates={f['t2dm_dx_count']} med={f['t2dm_med_date']} "
              f"insulin={f['insulin_date']} abnormal_lab={f['abnormal_lab']} "
              f"-> rule label {rules_labeler.label(recs[pid])}")
        print(f"chart size: {chars:,} chars, ~{toks:,} tokens")
        print("=" * 78)
        print(chart)

    for bucket_name, charts in (
            (sample_bucket, [records_mod.render_chart(recs[p])
                             for p in router_mod.bucket_members(assignments, sample_bucket)]),
            ("FULL COHORT", [records_mod.render_chart(r) for r in recs.values()])):
        print_projection(project_cost(charts, 400), bucket_name, 400)


def full_run(phenotype, use_all=False, limit=None, resume=False,
             effort=llm_labeler.DEFAULT_EFFORT, assume_yes=False,
             assumed_output_tokens=400, skip_preflight_call=False):
    started = time.time()
    recs, assignments = build_and_route(phenotype)

    report, ok = preflight(recs, effort, skip_api=skip_preflight_call)
    print(f"\n[run] {report.summary()}")
    if not ok:
        write_preflight_failure_md(report)
        print("[run] PREFLIGHT FAILED — stopping before any bulk API calls.")
        print("[run] Nothing was written and nothing was spent.")
        raise SystemExit(3)
    assignment_map = PHENOTYPES[phenotype]["assignment"]
    rules = PHENOTYPES[phenotype]["rules"]
    roster_order = list(recs.keys())          # patients.csv order, verbatim ids

    # Rule labels for everybody: the baseline, and the fallback for any patient
    # the model does not or cannot answer for.
    rule_labels = {pid: rules.label(rec) for pid, rec in recs.items()}
    n_rule_positive = sum(rule_labels.values())
    print(f"\n[run] rule baseline: {n_rule_positive} positive / "
          f"{len(rule_labels)-n_rule_positive} negative")

    # Who goes to the model?
    if use_all:
        targets = list(roster_order)
        mode = "full cohort (--all)"
    else:
        targets = [pid for pid in roster_order
                   if assignment_map[assignments[pid]] == "llm"]
        mode = "routed cascade"
    print(f"[run] mode: {mode} — {len(targets)} patients to the LLM")

    charts = {pid: records_mod.render_chart(recs[pid]) for pid in targets}

    # Resume before limiting, so --resume --limit N means "N more".
    done = load_checkpoint() if resume else {}
    if resume:
        print(f"[run] resuming: {len(done)} patients already in {CHECKPOINT_PATH}")
        targets = [pid for pid in targets if pid not in done]
    elif os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)     # a fresh run starts a fresh checkpoint

    if limit is not None:
        targets = targets[:limit]
        print(f"[run] --limit {limit}: capping this pass at {len(targets)} patients")

    proj = project_cost([charts[p] for p in targets], assumed_output_tokens)
    print_projection(proj, f"this pass ({len(targets)} patients)", assumed_output_tokens)
    if not confirm_spend(proj["cost"], assume_yes):
        print("[run] aborted before any API calls.")
        return None

    llm_labeler.USAGE.reset()
    checkpoint = Checkpointer()
    print(f"\n[run] labeling {len(targets)} patients, starting at "
          f"{START_WORKERS} workers ...")
    fresh, stop_reason, governor = adjudicate_many(
        targets, recs, rule_labels, charts, effort, checkpoint)

    # --- an aborted run still writes what it has, and says why ----------------
    # The instruction that matters: a run that silently falls back to rules for
    # 800 patients is worse than a crash, because it looks like a result. So an
    # abort is loud, is written down, and is never folded into RESULTS.md as if
    # it were a clean run.
    n_fell_back = sum(1 for r in fresh.values() if r["fell_back"])
    if stop_reason:
        write_failures_md(stop_reason, fresh, n_fell_back, len(targets), governor)
        print(f"\n{'='*78}")
        print(f"[run] RUN ABORTED — {stop_reason}")
        print(f"[run] {len(fresh)} of {len(targets)} patients were adjudicated before "
              f"the abort; {n_fell_back} of those fell back to the rule label.")
        print(f"[run] Work is preserved in {CHECKPOINT_PATH}; see {FAILURES_PATH}.")
        print(f"[run] Re-run with --resume after fixing the cause.")
        print(f"[run] No submission was written — a partial cohort would be scored "
              f"as wrong on every patient it omits.")
        print("=" * 78)
        raise SystemExit(2)

    # --- assemble the final label vector -------------------------------------
    all_rows = dict(done)
    all_rows.update(fresh)
    labels = dict(rule_labels)                       # rules cover everyone first
    for pid, row in all_rows.items():
        labels[pid] = row["llm_label"]

    for pid, row in all_rows.items():
        row["bucket"] = assignments.get(pid, "?")

    # --- checks BEFORE writing. A malformed submission is worse than none:
    # --- uncovered patients are counted against the score, so a short file
    # --- scores worse than a wrong-but-complete one.
    assert len(labels) == EXPECTED_TOTAL, (
        f"submission would have {len(labels)} rows, expected {EXPECTED_TOTAL}")
    assert set(labels) == set(recs), "submission patient ids do not match the roster"
    assert len(roster_order) == EXPECTED_TOTAL, "roster order is the wrong length"
    bad = {p: v for p, v in labels.items() if v is None or v not in (0, 1)}
    assert not bad, f"null or non-binary labels for {len(bad)} patients: {list(bad)[:5]}"

    # Preflight 6: nobody's reason got cut off mid-sentence. A truncated
    # verdict is a lost verdict, and MAX_TOKENS exists to make this impossible.
    # This counts ACCEPTED responses that were truncated. An attempt that hit
    # the ceiling, failed to parse, and was retried successfully is not a
    # truncated verdict — it is a retry that worked, and it is reported as a
    # recovered parse failure instead.
    n_truncated = sum(1 for r in all_rows.values() if r.get("truncated"))
    assert n_truncated == 0, (
        f"{n_truncated} ACCEPTED response(s) hit the {llm_labeler.MAX_TOKENS}-token "
        f"ceiling; raise MAX_TOKENS — their reasons are truncated and unreliable")

    write_submissions(labels, roster_order)

    ordered_rows = [all_rows[pid] for pid in roster_order if pid in all_rows]
    write_run_log(ordered_rows)

    cohort = None
    if os.path.exists(COHORT_PATH):
        cohort = pd.read_csv(COHORT_PATH, index_col=0)
    else:
        print(f"[run] WARNING: {COHORT_PATH} missing — divergence rule_status "
              f"will be unavailable. Run phenotype.py first.")
        cohort = pd.DataFrame(columns=["status", "t2dm_dx_count"])
    divergences = write_divergence(ordered_rows, cohort)

    # --- accounting -----------------------------------------------------------
    # Totals come from the ROWS, not from USAGE. USAGE only covers this process,
    # so on a resumed run it would report the cost of the final pass as if it
    # were the cost of the cohort — understating the headline number of this
    # whole project by however much the earlier passes spent. The rows carry
    # their own tokens, so summing them gives the true cohort cost across every
    # pass that contributed a label.
    u = llm_labeler.USAGE
    rows_all = list(all_rows.values())

    def total(field):
        return sum(int(r.get(field) or 0) for r in rows_all)

    tok_in, tok_out = total("input_tokens"), total("output_tokens")
    tok_cw, tok_cr = total("cache_creation_tokens"), total("cache_read_tokens")
    # api_calls was added late; fall back to attempts for rows written before it.
    api_calls = sum(int(r.get("api_calls") or r.get("attempts") or 0) for r in rows_all)

    cost = (tok_in * PRICE_INPUT_PER_MTOK
            + tok_out * PRICE_OUTPUT_PER_MTOK
            + tok_cw * PRICE_CACHE_WRITE_PER_MTOK
            + tok_cr * PRICE_CACHE_READ_PER_MTOK) / 1_000_000
    elapsed = time.time() - started
    lat = sorted(float(r.get("latency_s") or 0.0) for r in rows_all) or [0.0]
    n_pos = sum(labels.values())

    stats = {
        "model": llm_labeler.MODEL,
        "effort": effort,
        "mode": mode,
        "n_total": len(labels),
        "n_llm": len(all_rows),
        "wall_min": elapsed / 60,
        "resumed_from_prior": len(done),
        "api_calls": api_calls,
        "input_tokens": tok_in,
        "output_tokens": tok_out,
        "cache_creation_tokens": tok_cw,
        "cache_read_tokens": tok_cr,
        "cost": cost,
        "cost_per_patient": cost / max(1, len(all_rows)),
        "mean_latency": statistics.mean(lat),
        "median_latency": statistics.median(lat),
        "p95_latency": lat[int(len(lat) * 0.95) - 1] if len(lat) > 1 else lat[0],
        "retries": u.retries,
        # The concurrency the run ACTUALLY used, not the constant it started
        # from — if the governor throttled us, that is a fact about this run's
        # latency numbers and belongs next to them.
        "start_workers": START_WORKERS,
        "final_workers": governor.limit,
        "halvings": len(governor.halvings),
        # All row-derived so they describe the COHORT, not just this pass. On a
        # resumed run the USAGE counters cover only the final process, which
        # would report a clean zero for failures that really happened earlier.
        "fallbacks": sum(1 for r in rows_all if r.get("fell_back")),
        "refusals": sum(1 for r in rows_all if r.get("refused")),
        "empty_responses": sum(1 for r in rows_all if r.get("empty")),
        "truncations": n_truncated,
        "rate_limit_hits": sum(int(r.get("rate_limited") or 0) for r in rows_all),
        "parse_failures": sum(1 for r in rows_all if r.get("parse_failed")),
        # A parse failure that a retry rescued is a very different fact from
        # one that ended in a fallback; reporting them as one number would
        # make a healthy run look broken, or a broken one look healthy.
        "parse_recovered": sum(1 for r in rows_all
                               if r.get("parse_failed") and not r.get("fell_back")),
        "parse_unrecovered": sum(1 for r in rows_all
                                 if r.get("parse_failed") and r.get("fell_back")),
        "n_agree": sum(1 for r in ordered_rows
                       if r["llm_label"] == r["rule_label"] and not r.get("fell_back")),
        "n_divergent": len(divergences),
        "divergence_rate": len(divergences) / max(1, len(all_rows)),
        "n_rule_neg_llm_pos": sum(1 for d in divergences
                                  if d["direction"] == "rule_neg_llm_pos"),
        "n_rule_pos_llm_neg": sum(1 for d in divergences
                                  if d["direction"] == "rule_pos_llm_neg"),
        "n_flip_with_dx": sum(1 for d in divergences
                              if d["direction"] == "rule_neg_llm_pos"
                              and d["has_t2d_dx_code"]),
        "n_flip_without_dx": sum(1 for d in divergences
                                 if d["direction"] == "rule_neg_llm_pos"
                                 and not d["has_t2d_dx_code"]),
        "n_positive": n_pos,
        "n_negative": len(labels) - n_pos,
        "n_rule_positive": n_rule_positive,
    }
    write_results_md(stats)

    print(f"\n{'='*78}\nRUN ACCOUNTING\n{'='*78}")
    print(f"  model            {stats['model']} (effort={effort})")
    print(f"  mode             {mode}")
    # Cohort totals, summed from the rows — on a resumed run these span every
    # pass. `u.*` would only describe this process and would understate the
    # cohort cost by however much earlier passes spent.
    if stats["resumed_from_prior"]:
        print(f"  (cohort totals across passes; {stats['resumed_from_prior']:,} "
              f"patients resumed from checkpoint, {len(fresh):,} called this pass)")
    print(f"  wall clock       {elapsed:.1f}s ({stats['wall_min']:.2f} min"
          + (", final pass only" if stats["resumed_from_prior"] else "") + ")")
    print(f"  API calls        {stats['api_calls']:,}")
    print(f"  retries          {u.retries:,} (this pass)")
    print(f"  fallbacks        {sum(1 for r in rows_all if r.get('fell_back')):,}")
    print(f"  input tokens     {stats['input_tokens']:,}")
    print(f"  output tokens    {stats['output_tokens']:,}")
    print(f"  cache write/read {stats['cache_creation_tokens']:,} / "
          f"{stats['cache_read_tokens']:,}")
    print(f"  cost_usd         ${cost:.4f}")
    print(f"  per patient      ${stats['cost_per_patient']:.5f}")
    print(f"  latency          mean {stats['mean_latency']:.2f}s / "
          f"median {stats['median_latency']:.2f}s / p95 {stats['p95_latency']:.2f}s")
    print(f"  submission       {n_pos} positive / {len(labels)-n_pos} negative")
    print(f"  divergences      {len(divergences)} "
          f"(+{stats['n_rule_neg_llm_pos']} / -{stats['n_rule_pos_llm_neg']})")

    if u.fallbacks:
        print(f"\n[run] WARNING: {u.fallbacks} patient(s) fell back to the rule label "
              f"after API failure. Those are NOT model agreement — they are missing "
              f"verdicts, and they are excluded from divergence.csv.")
    disabled = [k for k, v in llm_labeler.FEATURES.items() if not v]
    if disabled:
        print(f"[run] WARNING: features disabled mid-run after API rejection: {disabled}")

    return stats


def main():
    ap = argparse.ArgumentParser(
        prog="run.py",
        description="Routed-cascade phenotyping over the Coherent synthetic EHR. "
                    "Builds one record per patient, routes each patient to a "
                    "labeler by what evidence exists in their chart, and writes "
                    "a full-roster submission with measured cost and latency.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  run.py --phenotype t2d --dry-run          route only; zero API calls
  run.py --phenotype t2d                    cascade: LLM on the 68 CONFLICTING
  run.py --phenotype t2d --all --limit 20   smoke test on 20 patients
  run.py --phenotype t2d --all              full cohort: all 3539 to the LLM
  run.py --phenotype t2d --all --resume     continue an interrupted full run
""")
    ap.add_argument("--phenotype", default="t2d", choices=sorted(PHENOTYPES),
                    help="which phenotype definition to run (default: t2d)")
    ap.add_argument("--dry-run", action="store_true",
                    help="build records and route only; make zero API calls")
    ap.add_argument("--all", dest="use_all", action="store_true",
                    help="send every patient to the LLM, not just CONFLICTING")
    ap.add_argument("--limit", type=int, metavar="N",
                    help="cap this pass at N patients (smoke testing)")
    ap.add_argument("--resume", action="store_true",
                    help=f"skip patients already recorded in {CHECKPOINT_PATH}")
    ap.add_argument("--effort", default=llm_labeler.DEFAULT_EFFORT,
                    choices=["low", "medium", "high"],
                    help="model reasoning effort (default: %(default)s)")
    ap.add_argument("--assumed-output-tokens", type=int, default=400, metavar="N",
                    help="output tokens per call assumed by the cost projection; "
                         "recalibrate from a smoke test (default: %(default)s)")
    ap.add_argument("--yes", action="store_true",
                    help=f"skip the confirmation prompt above "
                         f"${COST_CONFIRM_THRESHOLD_USD:.0f}")
    ap.add_argument("--skip-preflight-call", action="store_true",
                    help="run preflight but omit the single live API call")
    args = ap.parse_args()

    if args.dry_run:
        dry_run(args.phenotype)
    else:
        full_run(args.phenotype, use_all=args.use_all, limit=args.limit,
                 resume=args.resume, effort=args.effort, assume_yes=args.yes,
                 assumed_output_tokens=args.assumed_output_tokens,
                 skip_preflight_call=args.skip_preflight_call)
    return 0


if __name__ == "__main__":
    sys.exit(main())
