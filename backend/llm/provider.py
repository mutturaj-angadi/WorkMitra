from dataclasses import dataclass
from functools import lru_cache
from time import sleep

from backend.config import get_settings
from backend.reliability import CircuitBreaker


@dataclass
class ModelReply:
    text: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost: float | None = None


class MockProvider:
    provider = "mock"
    model = "deterministic-no-source"

    def invoke(self, prompt: str) -> ModelReply:
        return ModelReply(
            "Mock provider active: no statutory answer was generated. Use official evidence and verification before advising.",
            self.provider,
            self.model,
            0,
            0,
            0.0,
        )


class GeminiProvider:
    provider = "gemini"

    def __init__(self):
        settings = get_settings()
        settings.validate_provider()
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as e:
            raise RuntimeError("Install langchain-google-genai to enable Gemini") from e
        self.client = ChatGoogleGenerativeAI(
            model=settings.google_model,
            google_api_key=settings.google_api_key,
            timeout=20,
            max_retries=0,
        )
        self.model = settings.google_model

    def invoke(self, prompt: str) -> ModelReply:
        response = self.client.invoke(prompt)
        usage = getattr(response, "usage_metadata", {}) or {}
        return ModelReply(
            str(response.content),
            self.provider,
            self.model,
            usage.get("input_tokens"),
            usage.get("output_tokens"),
            None,
        )


class ResilientProvider:
    """Bounded provider retries with a shared per-process breaker."""

    def __init__(self, delegate, threshold=3, max_attempts=3):
        self.delegate = delegate
        self.breaker = CircuitBreaker(threshold=threshold, reset_seconds=30)
        self.max_attempts = max_attempts
        self.provider = getattr(delegate, "provider", "unknown")
        self.model = getattr(delegate, "model", "unknown")

    def invoke(self, prompt: str) -> ModelReply:
        if self.breaker.is_open:
            raise RuntimeError(
                "Provider circuit is open; use the safe escalation path."
            )
        last_error = None
        for attempt in range(self.max_attempts):
            try:
                reply = self.delegate.invoke(prompt)
                self.breaker.success()
                return reply
            # SDK exceptions vary by provider; normalize them at this boundary.
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                self.breaker.failure()
                if attempt + 1 < self.max_attempts and not self.breaker.is_open:
                    sleep(min(0.25 * (2**attempt), 1.0))
        raise RuntimeError(
            "Provider call failed after bounded retries."
        ) from last_error


@lru_cache(maxsize=1)
def get_provider():
    settings = get_settings()
    settings.validate_provider()
    provider = settings.llm_provider
    if provider == "gemini":
        delegate = GeminiProvider()
    elif provider == "stub":
        delegate = FixedResponseStub(get_settings().stub_delay_seconds)
    elif provider == "mock":
        delegate = MockProvider()
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
    return ResilientProvider(delegate, max_attempts=2)


class FixedResponseStub:
    """Deterministic latency stub for load tests; it never returns legal content."""

    provider = "stub"
    model = "fixed-response"

    def __init__(self, delay_seconds: float = 1.2):
        self.delay_seconds = max(0.0, min(delay_seconds, 10.0))

    def invoke(self, prompt: str) -> ModelReply:
        sleep(self.delay_seconds)
        return ModelReply(
            "Fixed response from performance stub; not a legal answer.",
            self.provider,
            self.model,
            8,
            10,
            0.0,
        )
