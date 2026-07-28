# labelers/llm.py — the LLM labeler: one Claude call per patient.
#
# Same contract as the rule labeler: label(record) -> 0|1. The runner does not
# know or care that this one costs money and takes a second.
#
# Three things this file is careful about, because all three are ways a model
# labeler quietly stops being an experiment and starts being noise:
#
#   STRICT OUTPUT   the verdict comes back as schema-validated JSON, not prose
#                   we regex. A verdict we had to guess at is not a verdict.
#   HONEST FAILURE  on repeated API failure we fall back to the rule label and
#                   SAY SO. A silent fallback would look like the model agreeing
#                   with the rules, which is the single most misleading result
#                   this experiment could produce.
#   IMPORTABLE      no key, no network, no anthropic package? This module still
#                   imports. Dry runs must work on a machine with no credentials.

import os
import random
import time
from dataclasses import dataclass, field

MODEL = "claude-sonnet-5"

# Retry policy for 429 / 503 / 5xx / connection drops. We turn the SDK's own
# retries OFF and own the loop here, so that "we retried three times and then
# fell back" is something we can log rather than something that happened
# invisibly inside the client.
MAX_ATTEMPTS = 4
BASE_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 30.0

MAX_TOKENS = 8000
EFFORT = "medium"

# The verdict schema. `reason` is required and required to cite evidence,
# because the diff report is only useful if every flip comes with a stated
# reason we can read and disagree with.
VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "has_type_2_diabetes": {
            "type": "boolean",
            "description": "True if this patient has Type 2 diabetes mellitus.",
        },
        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "reason": {
            "type": "string",
            "description": "One or two sentences citing the specific evidence "
                           "in the chart that decided it.",
        },
    },
    "required": ["has_type_2_diabetes", "confidence", "reason"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are adjudicating Type 2 diabetes status from a structured patient chart.

You are being asked only about patients where a rule-based phenotype algorithm \
(PheKB T2DM, eMERGE) could not reach a verdict. Every one of these patients has \
at least one Type 2 diabetes diagnosis code on file, but the algorithm's case \
paths did not close — most often because the patient is on insulin, which the \
algorithm treats as evidence against Type 2.

Judge the chart on its clinical merits. Relevant considerations:
- A recorded Type 2 diabetes diagnosis code is strong evidence.
- Insulin use does not rule out Type 2 diabetes. Type 2 patients are commonly \
escalated to insulin as the disease progresses.
- Age at onset, obesity, hypertension, hyperlipidemia, and diabetic \
complications (retinopathy, neuropathy, nephropathy) support Type 2.
- Elevated HbA1c (>= 6.5%) or glucose (> 200 mg/dL) confirms diabetes.
- Answer for the patient's lifetime status, not their status on any one date.

Return only the JSON verdict."""

USER_TEMPLATE = """Does this patient have Type 2 diabetes?

{chart}"""


@dataclass
class Verdict:
    """What one adjudication produced. The runner logs all of it."""
    label: int
    reason: str
    confidence: str = "n/a"
    input_tokens: int = 0
    output_tokens: int = 0
    api_calls: int = 0
    fell_back: bool = False
    errors: list = field(default_factory=list)


class _Usage:
    """Process-wide accounting. Kept here rather than in the runner so that any
    caller of this labeler gets the same numbers without re-implementing them."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.api_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.fallbacks = 0
        self.retries = 0

    def record(self, verdict):
        self.api_calls += verdict.api_calls
        self.input_tokens += verdict.input_tokens
        self.output_tokens += verdict.output_tokens
        self.retries += len(verdict.errors)
        if verdict.fell_back:
            self.fallbacks += 1


USAGE = _Usage()

_client = None


def _get_client():
    """Build the client on first use. Deliberately NOT at import time: a dry run
    on a machine with no key and no anthropic package must still import this."""
    global _client
    if _client is not None:
        return _client

    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError(
            "the anthropic package is not installed — `pip install anthropic`"
        ) from exc

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Export it; do not hardcode it."
        )

    # max_retries=0: we run our own backoff so failures are visible in the log.
    _client = anthropic.Anthropic(api_key=api_key, max_retries=0)
    return _client


def _is_retryable(exc):
    """429 and 503 explicitly, plus the rest of the 5xx family and connection
    drops — same class of transient failure, same response."""
    import anthropic

    if isinstance(exc, (anthropic.RateLimitError, anthropic.APIConnectionError)):
        return True
    if isinstance(exc, anthropic.APIStatusError):
        return exc.status_code >= 500
    return False


def _retry_after(exc, attempt):
    """Honour the server's retry-after when it sends one; otherwise exponential
    backoff with jitter so a batch of 68 calls does not retry in lockstep."""
    header = getattr(getattr(exc, "response", None), "headers", None)
    if header is not None:
        try:
            return min(float(header.get("retry-after")), MAX_DELAY_SECONDS)
        except (TypeError, ValueError):
            pass
    return min(BASE_DELAY_SECONDS * (2 ** attempt) + random.uniform(0, 1),
               MAX_DELAY_SECONDS)


def adjudicate(record, rule_label=0, chart=None, render=None):
    """One patient, one call (plus retries). Returns a Verdict.

    `rule_label` is the fallback answer, used only if every attempt fails. It is
    NOT shown to the model — the point of this labeler is an independent read.
    """
    import json

    if chart is None:
        if render is None:
            from records import render_chart as render
        chart = render(record)

    verdict = Verdict(label=rule_label, reason="")
    last_exc = None

    for attempt in range(MAX_ATTEMPTS):
        try:
            client = _get_client()
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                output_config={
                    "effort": EFFORT,
                    "format": {"type": "json_schema", "schema": VERDICT_SCHEMA},
                },
                messages=[{"role": "user",
                           "content": USER_TEMPLATE.format(chart=chart)}],
            )
            verdict.api_calls += 1
            verdict.input_tokens += response.usage.input_tokens
            verdict.output_tokens += response.usage.output_tokens

            if response.stop_reason == "refusal":
                raise RuntimeError("model refused to answer")

            text = next(b.text for b in response.content if b.type == "text")
            parsed = json.loads(text)
            verdict.label = 1 if parsed["has_type_2_diabetes"] else 0
            verdict.confidence = parsed["confidence"]
            verdict.reason = parsed["reason"]
            return verdict

        except Exception as exc:  # noqa: BLE001 — we classify below
            last_exc = exc
            verdict.errors.append(f"{type(exc).__name__}: {exc}")

            retryable = False
            try:
                retryable = _is_retryable(exc)
            except ImportError:
                retryable = False   # no SDK installed: nothing to retry into

            if not retryable or attempt == MAX_ATTEMPTS - 1:
                break
            time.sleep(_retry_after(exc, attempt))

    # Every attempt failed. Fall back to the rule label and mark it loudly:
    # an unmarked fallback would read as the model agreeing with the rules.
    verdict.label = rule_label
    verdict.fell_back = True
    verdict.confidence = "n/a"
    verdict.reason = f"LLM FAILED after {len(verdict.errors)} attempt(s); " \
                     f"fell back to rule label {rule_label}. Last error: {last_exc}"
    print(f"[llm] FALLBACK for {record['id']}: {last_exc}")
    return verdict


def label(record):
    """The labeler contract. Abstains to negative if the API is unreachable."""
    verdict = adjudicate(record, rule_label=0)
    USAGE.record(verdict)
    return verdict.label
