# labelers/llm.py — the LLM labeler: one Claude call per patient.
#
# Same contract as the rule labeler: label(record) -> 0|1. The runner does not
# know or care that this one costs money and takes a second.
#
# The design pressure on this file is not accuracy. It is that a 3539-call run
# has many ways to produce a plausible-looking result that means nothing:
#
#   STRICT OUTPUT   verdicts are schema-validated JSON. A response we had to
#                   guess at is logged raw and counted as a parse failure, not
#                   quietly coerced into a label.
#   HONEST FAILURE  on repeated API failure we fall back to the rule label and
#                   SAY SO, per patient. A silent fallback looks exactly like
#                   the model agreeing with the rules — the single most
#                   misleading result this experiment could produce.
#   MEASURED        every call reports its own tokens, latency, and stop reason.
#                   Cost is the headline result here, so it is measured per
#                   call rather than estimated afterwards.
#   IMPORTABLE      no key, no network, no anthropic package? This module still
#                   imports. Dry runs must work on a machine with no credentials.

import json
import os
import random
import re
import threading
import time
from dataclasses import dataclass, field

# Load .env at import so the key is in os.environ for the whole process,
# worker threads included — os.environ is process-wide, so a value loaded here
# on the main thread is visible from every worker. preflight() proves that
# rather than assuming it.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MODEL = "claude-sonnet-5"

# Dollars per million tokens, (input, output). Sonnet is on introductory rates
# through 2026-08-31; standard is $3/$15. Kept here rather than in run.py
# because a cascade bills two models in one run and the cost of a row depends
# on which model produced it — the pricing has to travel with the model name.
MODEL_PRICING = {
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
}


def price_of(model):
    if model not in MODEL_PRICING:
        raise KeyError(f"no pricing for {model!r} — add it to MODEL_PRICING "
                       f"before running, or the cost report is a guess")
    return MODEL_PRICING[model]

# Retry policy for 429 / 503 / 5xx / connection drops. We turn the SDK's own
# retries OFF and own the loop here, so "we retried five times and then fell
# back" is something we can log rather than something that happened invisibly.
MAX_ATTEMPTS = 6
BASE_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 60.0

# Generous on purpose. Reasoning tokens bill as output and a truncated verdict
# is a lost verdict, so we would rather pay for headroom than lose a reason
# mid-sentence. Truncations are counted and asserted to be zero.
MAX_TOKENS = 16000
DEFAULT_EFFORT = "medium"

PARSE_FAILURE_LOG = "parse_failures.log"

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "has_type_2_diabetes": {
            "type": "boolean",
            "description": "True if this patient has Type 2 diabetes mellitus.",
        },
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "reason": {
            "type": "string",
            "description": "One or two sentences citing the specific evidence "
                           "in the chart that decided it.",
        },
    },
    "required": ["has_type_2_diabetes", "confidence", "reason"],
    "additionalProperties": False,
}

# NOTE ON CACHING: this prompt is identical across every call and is sent with
# cache_control. It is also only ~300 tokens, and the minimum cacheable prefix
# on Sonnet is 1024 — so the marker is accepted and then does nothing. The
# runner reports measured cache_creation / cache_read tokens instead of
# claiming a saving: if they come back zero, the cache is a no-op and the
# honest thing is to be able to see that.
SYSTEM_PROMPT = """You are adjudicating Type 2 diabetes status from a structured patient chart.

Judge the chart on its clinical merits. Relevant considerations:
- A recorded Type 2 diabetes diagnosis code is strong evidence.
- Insulin use does NOT rule out Type 2 diabetes. Type 2 patients are commonly \
escalated to insulin as the disease progresses. A rule-based algorithm that \
treats insulin as evidence against Type 2 will misclassify these patients.
- Age at onset, obesity (BMI >= 30), hypertension, hyperlipidemia, metabolic \
syndrome, and diabetic complications (retinopathy, neuropathy, nephropathy, \
diabetic renal disease) support Type 2.
- Elevated HbA1c (>= 6.5%) or glucose (> 200 mg/dL) confirms diabetes. Note \
that prediabetes or an isolated mildly elevated glucose is NOT diabetes.
- A patient on metformin, a GLP-1 agonist, or an SGLT2 inhibitor is being \
treated for Type 2 diabetes.
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
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    api_calls: int = 0
    attempts: int = 0
    latency_s: float = 0.0
    model: str = MODEL
    fell_back: bool = False
    truncated: bool = False
    refused: bool = False
    empty: bool = False
    parse_failed: bool = False
    rate_limited: int = 0
    errors: list = field(default_factory=list)


class _Usage:
    """Process-wide accounting. Thread-safe, because the runner fans these out
    across a worker pool and a lost increment is a wrong cost figure."""

    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with getattr(self, "_lock", threading.Lock()):
            self.api_calls = 0
            self.input_tokens = 0
            self.output_tokens = 0
            self.cache_creation_tokens = 0
            self.cache_read_tokens = 0
            self.fallbacks = 0
            self.retries = 0
            self.rate_limit_hits = 0
            self.parse_failures = 0
            self.refusals = 0
            self.empty_responses = 0
            self.truncations = 0
            self.latencies = []

    def record(self, verdict):
        with self._lock:
            self.api_calls += verdict.api_calls
            self.input_tokens += verdict.input_tokens
            self.output_tokens += verdict.output_tokens
            self.cache_creation_tokens += verdict.cache_creation_tokens
            self.cache_read_tokens += verdict.cache_read_tokens
            self.retries += max(0, verdict.attempts - 1)
            self.rate_limit_hits += verdict.rate_limited
            self.latencies.append(verdict.latency_s)
            self.fallbacks += int(verdict.fell_back)
            self.parse_failures += int(verdict.parse_failed)
            self.refusals += int(verdict.refused)
            self.empty_responses += int(verdict.empty)
            self.truncations += int(verdict.truncated)

    def cost(self, p_in, p_out, p_cache_write, p_cache_read):
        with self._lock:
            return (self.input_tokens * p_in
                    + self.output_tokens * p_out
                    + self.cache_creation_tokens * p_cache_write
                    + self.cache_read_tokens * p_cache_read) / 1_000_000


USAGE = _Usage()

_client = None
_client_lock = threading.Lock()
_parse_log_lock = threading.Lock()

# Feature degradation. If the API rejects a request parameter, we turn that
# parameter off once, globally, and carry on rather than failing 3539 times in
# a row. Reported by the runner so a degraded run is never mistaken for clean.
def _default_features(model):
    """Per-model, not global. Agent B disabled 'effort' because Haiku rejects
    it — and that switched it off for the Sonnet escalations too, silently
    changing the strong model's behavior because the cheap one complained.
    Capability is a property of the model, so the flags are keyed by model.

    Haiku is seeded as unsupported up front rather than learned from a 400:
    the round trip is free to skip and the rejection is already known."""
    supports_effort = not model.startswith("claude-haiku")
    return {"effort": supports_effort, "structured_output": True, "caching": True}


FEATURES_BY_MODEL = {}
_features_lock = threading.Lock()


def features_for(model):
    with _features_lock:
        if model not in FEATURES_BY_MODEL:
            FEATURES_BY_MODEL[model] = _default_features(model)
        return dict(FEATURES_BY_MODEL[model])


# Back-compat view for callers that only ever used the default model.
FEATURES = _default_features(MODEL)

# Bumped every time a feature is disabled. Without it, feature degradation is
# only safe for the ONE worker that happens to trip the 400 first: it flips the
# flag, retries, and succeeds, while every other in-flight worker gets the same
# 400, finds the flag already off, classifies a BadRequestError as
# non-retryable, and falls back. At 16 workers that silently converts a whole
# wave of patients into fallbacks and — in a cascade — escalates every one of
# them to the expensive model. Comparing this counter across an attempt tells a
# worker "someone else already fixed this, try again" instead.
_features_version = 0


def features_version():
    with _features_lock:
        return _features_version


def resolved_model():
    return MODEL


def _get_client():
    """Build the client on first use. Deliberately NOT at import time: a dry run
    on a machine with no key and no anthropic package must still import this."""
    global _client
    with _client_lock:
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
                "ANTHROPIC_API_KEY is not set. Export it or put it in .env; "
                "do not hardcode it."
            )
        _client = anthropic.Anthropic(api_key=api_key, max_retries=0, timeout=120.0)
        return _client


def _is_rate_limit(exc):
    try:
        import anthropic
    except ImportError:
        return False
    return isinstance(exc, anthropic.RateLimitError)


def _is_retryable(exc):
    """429 and 503 explicitly, plus the rest of the 5xx family and connection
    drops — same class of transient failure, same response. A 401 or a bad
    model string is NOT retryable: retrying credentials in a loop just burns
    time to arrive at the same answer."""
    import anthropic
    if isinstance(exc, (anthropic.RateLimitError, anthropic.APIConnectionError,
                        anthropic.APITimeoutError)):
        return True
    if isinstance(exc, anthropic.APIStatusError):
        return exc.status_code >= 500
    return False


def is_fatal(exc):
    """Errors where retrying anywhere in the run is pointless: bad credentials,
    bad model string, missing key, missing package."""
    if isinstance(exc, RuntimeError):
        return True
    try:
        import anthropic
    except ImportError:
        return True
    if isinstance(exc, (anthropic.AuthenticationError, anthropic.PermissionDeniedError,
                        anthropic.NotFoundError)):
        return True
    return False


def _degrade_on_bad_request(exc, model):
    """A 400 usually means a parameter this SDK/model pair does not accept.
    Turn that feature off once and let the caller retry, rather than losing the
    whole run to one unsupported field."""
    import anthropic
    if not isinstance(exc, anthropic.BadRequestError):
        return False
    global _features_version
    msg = str(exc).lower()
    with _features_lock:
        feats = FEATURES_BY_MODEL.setdefault(model, _default_features(model))
        for key, needles in (("effort", ("effort",)),
                             ("structured_output", ("output_config", "json_schema", "format")),
                             ("caching", ("cache_control", "cache"))):
            if feats[key] and any(n in msg for n in needles):
                feats[key] = False
                _features_version += 1
                print(f"[llm] {model} rejected '{key}' — disabling it for that "
                      f"model for the rest of this run and retrying. ({exc})")
                return True
    return False


def _retry_after(exc, attempt):
    """Honour the server's retry-after when it sends one; otherwise exponential
    backoff with jitter so parallel workers do not retry in lockstep."""
    headers = getattr(getattr(exc, "response", None), "headers", None)
    if headers is not None:
        try:
            return min(float(headers.get("retry-after")), MAX_DELAY_SECONDS)
        except (TypeError, ValueError):
            pass
    return min(BASE_DELAY_SECONDS * (2 ** attempt) + random.uniform(0, 1),
               MAX_DELAY_SECONDS)


def _build_request(chart, effort, model=MODEL, temperature=None):
    feats = features_for(model)
    use_effort = feats["effort"]
    use_structured = feats["structured_output"]
    use_cache = feats["caching"]

    system_block = {"type": "text", "text": SYSTEM_PROMPT}
    if use_cache:
        system_block["cache_control"] = {"type": "ephemeral"}

    kwargs = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": [system_block],
        "messages": [{"role": "user", "content": USER_TEMPLATE.format(chart=chart)}],
    }
    output_config = {}
    if use_effort and effort:
        output_config["effort"] = effort
    if use_structured:
        output_config["format"] = {"type": "json_schema", "schema": VERDICT_SCHEMA}
    else:
        kwargs["messages"][0]["content"] += (
            '\n\nRespond with ONLY a JSON object: '
            '{"has_type_2_diabetes": true|false, "confidence": "low"|"medium"|"high", '
            '"reason": "..."}'
        )
    if output_config:
        kwargs["output_config"] = output_config
    if temperature is not None:
        # Sampling variation is the entire point for consensus voting: three
        # calls at temperature 0 would be three copies of one opinion, and a
        # unanimous vote would mean nothing.
        kwargs["temperature"] = temperature
    return kwargs


def _log_parse_failure(patient_id, raw, note):
    """Raw text, verbatim, so a parse failure can actually be diagnosed later
    rather than guessed at from a counter."""
    with _parse_log_lock:
        with open(PARSE_FAILURE_LOG, "a") as fh:
            fh.write(f"\n{'='*70}\npatient: {patient_id}\nnote: {note}\n"
                     f"{'-'*70}\n{raw}\n")


def _parse_verdict(text):
    """Strip fences, take the first JSON object, and accept only a boolean the
    schema would have accepted. Anything else raises and is logged raw."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise ValueError("no JSON object found in response")
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict) or "has_type_2_diabetes" not in parsed:
        raise ValueError("response JSON lacks has_type_2_diabetes")

    raw_label = parsed["has_type_2_diabetes"]
    if isinstance(raw_label, bool):
        label = int(raw_label)
    elif isinstance(raw_label, (int, float)) and int(raw_label) in (0, 1):
        label = int(raw_label)
    elif isinstance(raw_label, str) and raw_label.strip().lower() in (
            "true", "false", "0", "1", "yes", "no"):
        label = int(raw_label.strip().lower() in ("true", "1", "yes"))
    else:
        raise ValueError(f"label not in {{0,1}}: {raw_label!r}")

    return label, parsed.get("confidence", "n/a"), parsed.get("reason", "")


def adjudicate(record, rule_label=0, chart=None, render=None, effort=DEFAULT_EFFORT,
               governor=None, model=MODEL, temperature=None):
    """One patient, one call (plus retries). Returns a Verdict.

    `rule_label` is the fallback answer, used only if every attempt fails. It is
    NOT shown to the model — the point of this labeler is an independent read.
    """
    if chart is None:
        if render is None:
            from records import render_chart as render
        chart = render(record)

    verdict = Verdict(label=rule_label, reason="", model=model)
    last_exc = None
    started = time.time()

    for attempt in range(MAX_ATTEMPTS):
        try:
            verdict.attempts += 1
            features_at_send = features_version()
            client = _get_client()
            if governor is not None:
                governor.acquire()
            try:
                response = client.messages.create(
                    **_build_request(chart, effort, model, temperature))
            finally:
                if governor is not None:
                    governor.release()

            verdict.api_calls += 1
            usage = response.usage
            verdict.input_tokens += usage.input_tokens
            verdict.output_tokens += usage.output_tokens
            verdict.cache_creation_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0
            verdict.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0

            # Refusal and truncation are distinct failures from a parse failure
            # and are counted separately — lumping them together would hide
            # which one is actually happening.
            if response.stop_reason == "refusal":
                verdict.refused = True
                raise ValueError("model refused to answer")

            # ASSIGNMENT, not |=. This flag must describe the response we
            # actually accept, not any attempt we made. A response that hits
            # the ceiling mid-JSON fails to parse and gets retried; if the
            # retry returns a clean verdict, the patient is fine and flagging
            # them as truncated would condemn a good label for a discarded
            # attempt. (Token counts still accumulate across attempts — we paid
            # for the discarded one, so it belongs in the cost.)
            verdict.truncated = response.stop_reason == "max_tokens"

            text = next((b.text for b in response.content if b.type == "text"), "")
            if not text.strip():
                verdict.empty = True
                raise ValueError("empty response body")

            try:
                label, confidence, reason = _parse_verdict(text)
            except (ValueError, json.JSONDecodeError) as parse_exc:
                verdict.parse_failed = True
                _log_parse_failure(record["id"], text, str(parse_exc))
                raise

            verdict.label = label
            verdict.confidence = confidence
            verdict.reason = reason
            verdict.latency_s = time.time() - started
            return verdict

        except Exception as exc:  # noqa: BLE001 — classified immediately below
            last_exc = exc
            verdict.errors.append(f"{type(exc).__name__}: {exc}")

            if _is_rate_limit(exc):
                verdict.rate_limited += 1
                if governor is not None:
                    governor.note_rate_limit()

            try:
                if _degrade_on_bad_request(exc, model):
                    continue          # same attempt budget, one fewer feature
                # Another worker disabled the offending feature while this
                # request was in flight. The request we sent is stale, not
                # invalid — rebuild and retry rather than falling back.
                if features_version() != features_at_send:
                    continue
                if is_fatal(exc):
                    break             # credentials/model: retrying cannot help
                retryable = _is_retryable(exc)
            except ImportError:
                retryable = False

            # Parse failures, refusals and empty bodies are worth one more roll
            # of the dice — they are usually not deterministic.
            if isinstance(exc, (ValueError, json.JSONDecodeError)):
                retryable = True

            if not retryable or attempt == MAX_ATTEMPTS - 1:
                break
            time.sleep(_retry_after(exc, attempt))

    verdict.label = rule_label
    verdict.fell_back = True
    verdict.confidence = "n/a"
    verdict.latency_s = time.time() - started
    verdict.reason = (f"LLM FAILED after {verdict.attempts} attempt(s); fell back to "
                      f"rule label {rule_label}. Last error: {last_exc}")
    return verdict


def preflight_call(chart="PATIENT test\n  age 60 | M\n\nCONDITIONS:\n  (none)",
                   effort=DEFAULT_EFFORT, model=MODEL):
    """Exactly ONE API call, no retry loop. Returns (ok, info-dict).

    This exists so a bad key or a bad model string costs one request and a
    clear message, instead of 3539 requests and a confusing pile of fallbacks.
    """
    info = {"model_requested": model}
    started = time.time()
    try:
        client = _get_client()
        response = client.messages.create(**_build_request(chart, effort, model))
    except Exception as exc:  # noqa: BLE001
        info["error"] = f"{type(exc).__name__}: {exc}"
        info["fatal"] = is_fatal(exc)
        info["latency_s"] = time.time() - started
        return False, info

    info.update({
        "latency_s": time.time() - started,
        "model_echoed": getattr(response, "model", "?"),
        "stop_reason": response.stop_reason,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_creation_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        "raw_text": next((b.text for b in response.content if b.type == "text"), ""),
    })
    return True, info


def label(record):
    """The labeler contract. Abstains to negative if the API is unreachable."""
    verdict = adjudicate(record, rule_label=0)
    USAGE.record(verdict)
    return verdict.label
