# labelers/consensus.py — escalate on measured disagreement, not self-report.
#
# Agent B's escalation trigger never fired. Haiku returned "high" confidence on
# 2,686 of 2,686 screens — a constant, and a constant cannot route anything.
# Self-reported confidence turned out to be a property of the model's writing
# style rather than a measurement of its own uncertainty.
#
# This replaces it with a signal that is measured rather than claimed: ask the
# cheap model the same question k times at temperature 1.0 and look at whether
# the answers agree. Sampling disagreement is not a self-assessment; the model
# cannot round it up to "high". If the three votes split, the patient is
# genuinely near the model's decision boundary and gets the strong model.
#
# The honest failure mode, and the reason step 4 of the spec exists: if every
# patient comes back 3-0, this signal is ALSO constant and no better than the
# last one. That would not be a bug — it would be the finding that the task is
# easy enough that sampling cannot separate anything.

from collections import Counter

from labelers import llm as llm_labeler

SCREEN_MODEL = "claude-haiku-4-5-20251001"
ESCALATE_MODEL = "claude-sonnet-5"

K_VOTES = 3
VOTE_TEMPERATURE = 1.0      # sampling variation is the measurement


def adjudicate(record, rule_label=0, chart=None, escalate_chart=None,
               effort=llm_labeler.DEFAULT_EFFORT, governor=None, k=K_VOTES):
    """k independent cheap votes; escalate only if they disagree.

    Returns (final_verdict, info). info records the full vote vector, so the
    report can distinguish "unanimous and right" from "unanimous and wrong" —
    the second being the failure this design cannot see, exactly as
    self-reported confidence could not see its own overconfidence.
    """
    votes = []
    for _ in range(k):
        votes.append(llm_labeler.adjudicate(
            record, rule_label=rule_label, chart=chart, effort=effort,
            governor=governor, model=SCREEN_MODEL, temperature=VOTE_TEMPERATURE))

    good = [v for v in votes if not v.fell_back]
    tally = Counter(v.label for v in good)
    majority = tally.most_common(1)[0][0] if tally else rule_label

    # A SPLIT and a FAILED VOTE are different events and must never share a
    # counter. Agent B's escalations turned out to be all failure recovery
    # while looking like a working confidence trigger; counting an incomplete
    # vote as a "2-1 split" would reproduce that mistake exactly one layer
    # down. Only genuine disagreement among *successful* votes is signal.
    genuine_split = len(tally) > 1
    incomplete = len(good) < k
    unanimous = not genuine_split and not incomplete

    if genuine_split:
        split = "-".join(str(c) for _, c in tally.most_common())
    elif incomplete:
        split = f"incomplete-{len(good)}of{k}"
    else:
        split = f"{k}-0"

    info = {
        "tier": "consensus",
        "screen_model": SCREEN_MODEL,
        "k": k,
        "votes": "".join(str(v.label) for v in votes),
        "vote_split": split,
        "unanimous": int(unanimous),
        "genuine_split": int(genuine_split),
        "escalate_reason": ("split" if genuine_split
                            else "vote_failure" if incomplete else ""),
        "screen_label": majority,
        "screen_confidences": "|".join(v.confidence for v in votes),
        "screen_in": sum(v.input_tokens for v in votes),
        "screen_out": sum(v.output_tokens for v in votes),
        "screen_fell_back": int(len(good) < k),
        "escalate_model": "",
        "escalate_in": 0,
        "escalate_out": 0,
        "escalated": 0,
        "screen_was_wrong": 0,
    }

    if unanimous:
        winner = good[0]
        winner.label = majority
        winner.confidence = f"unanimous-{k}-0"
        winner.input_tokens = info["screen_in"]
        winner.output_tokens = info["screen_out"]
        winner.latency_s = sum(v.latency_s for v in votes)
        return winner, info

    strong = llm_labeler.adjudicate(record, rule_label=rule_label,
                                    chart=escalate_chart or chart, effort=effort,
                                    governor=governor, model=ESCALATE_MODEL)
    info.update({
        "tier": "escalated",
        "escalate_model": ESCALATE_MODEL,
        "escalate_in": strong.input_tokens,
        "escalate_out": strong.output_tokens,
        "escalated": 1,
        "screen_was_wrong": int(strong.label != majority and not strong.fell_back),
    })
    strong.latency_s += sum(v.latency_s for v in votes)
    strong.attempts += sum(v.attempts for v in votes)
    return strong, info


def cost_of(row):
    """Per-row cost across both price tiers. The screen bills k times."""
    s_in, s_out = llm_labeler.price_of(SCREEN_MODEL)
    e_in, e_out = llm_labeler.price_of(ESCALATE_MODEL)
    return ((int(row.get("screen_in") or 0) * s_in
             + int(row.get("screen_out") or 0) * s_out
             + int(row.get("escalate_in") or 0) * e_in
             + int(row.get("escalate_out") or 0) * e_out) / 1_000_000)
