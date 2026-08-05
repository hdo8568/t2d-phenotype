# labelers/cascade.py — model tiering: screen cheap, escalate when unsure.
#
# The project's central question, and the reason this file exists: the rules
# resolve a quarter of the cohort for nothing, and most of the rest is not
# genuinely hard. If a cheap model can answer the easy majority and hand up
# only the cases it is unsure about, the cost of a per-patient agentic method
# collapses without the accuracy going with it. Nobody on the dashboard has
# measured whether that holds.
#
# The design rests on one assumption that must be checked rather than assumed:
# THAT THE SCREEN'S CONFIDENCE IS INFORMATIVE. A cheap screen whose "high
# confidence" answers are wrong is worse than no screen at all — it is a
# confident wrong answer bought at a discount. So this module records the
# screen's verdict even when it escalates, which lets the runner report how
# often the screen was wrong on exactly the patients it was unsure about, and
# how often it was wrong while sure. Averaging those together would hide the
# only failure mode that matters.

from labelers import llm as llm_labeler

SCREEN_MODEL = "claude-haiku-4-5-20251001"
ESCALATE_MODEL = "claude-sonnet-5"

# The escalation predicate, as a tunable constant. Raising this to
# ("low", "medium") escalates more and costs more; emptying it disables
# escalation entirely and measures the screen alone.
ESCALATE_ON_CONFIDENCE = ("low",)

TIER_RULES = "rules"
TIER_SCREEN = "screen"
TIER_ESCALATED = "escalated"


def should_escalate(verdict):
    """Escalate when the screen says it is unsure — or when it failed outright,
    since a fallback is not an answer and handing it to the strong model is
    strictly better than shipping a rule label."""
    if verdict.fell_back:
        return True
    return verdict.confidence in ESCALATE_ON_CONFIDENCE


def adjudicate(record, rule_label=0, chart=None, escalate_chart=None,
               effort=llm_labeler.DEFAULT_EFFORT, governor=None):
    """Screen, then escalate if unsure. Returns (final_verdict, info).

    Two charts, deliberately. The screen sees the MINIMAL six-fact chart and the
    escalation sees the FULL one. Tiering only pays if the cheap tier is cheap
    on both axes — a cheap model reading an expensive prompt still bills for
    every input token, and input is ~80% of the screen's cost. So the cascade
    spends few tokens on the many and many tokens on the few. The escalated
    patient gets the whole chart precisely because the screen said the short
    version was not enough to decide.

    info carries the screen's own verdict even when it was overridden, because
    the interesting result is not the final label — it is whether the cheap
    model would have got there alone.
    """
    screen = llm_labeler.adjudicate(record, rule_label=rule_label, chart=chart,
                                    effort=effort, governor=governor,
                                    model=SCREEN_MODEL)
    info = {
        "tier": TIER_SCREEN,
        "screen_model": SCREEN_MODEL,
        "screen_label": screen.label,
        "screen_confidence": screen.confidence,
        "screen_reason": screen.reason,
        "screen_in": screen.input_tokens,
        "screen_out": screen.output_tokens,
        "screen_fell_back": int(screen.fell_back),
        "escalate_model": "",
        "escalate_in": 0,
        "escalate_out": 0,
        "escalated": 0,
        "screen_was_wrong": 0,
    }

    if not should_escalate(screen):
        return screen, info

    strong = llm_labeler.adjudicate(record, rule_label=rule_label,
                                    chart=escalate_chart or chart,
                                    effort=effort, governor=governor,
                                    model=ESCALATE_MODEL)
    info.update({
        "tier": TIER_ESCALATED,
        "escalate_model": ESCALATE_MODEL,
        "escalate_in": strong.input_tokens,
        "escalate_out": strong.output_tokens,
        "escalated": 1,
        # Did the cheap screen actually get this one wrong, or was it merely
        # unsure and right? Those are very different, and only this comparison
        # tells them apart.
        "screen_was_wrong": int(strong.label != screen.label and not strong.fell_back),
    })
    # Latency of the pair is what the patient actually cost in wall-clock.
    strong.latency_s += screen.latency_s
    strong.attempts += screen.attempts
    return strong, info


def cost_of(row):
    """Per-row cost, billed per model. A cascade row can carry tokens from two
    different price tiers, so a single price constant cannot describe it."""
    s_in, s_out = llm_labeler.price_of(SCREEN_MODEL)
    e_in, e_out = llm_labeler.price_of(ESCALATE_MODEL)
    return ((int(row.get("screen_in") or 0) * s_in
             + int(row.get("screen_out") or 0) * s_out
             + int(row.get("escalate_in") or 0) * e_in
             + int(row.get("escalate_out") or 0) * e_out) / 1_000_000)
