from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Domain(StrEnum):
    GRATUITY = "GRATUITY"
    MATERNITY_BENEFIT = "MATERNITY_BENEFIT"
    WORKPLACE_HARASSMENT = "WORKPLACE_HARASSMENT"
    OTHER = "OTHER"


class ComplianceInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    question: str = Field(min_length=12, max_length=4000)
    domain: Domain | None = None
    establishment_type: str | None = Field(default=None, max_length=100)
    headcount: int | None = Field(default=None, ge=0, le=10_000_000)
    employment_start: date | None = None
    employment_end: date | None = None
    contract_type: str | None = Field(default=None, max_length=80)
    contract_written: bool | None = None
    contract_duration_months: int | None = Field(default=None, ge=1, le=1200)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=128)

    @model_validator(mode="after")
    def ordered_dates(self):
        if (
            self.employment_start
            and self.employment_end
            and self.employment_end < self.employment_start
        ):
            raise ValueError("employment_end must not precede employment_start")
        return self


class FeedbackInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    run_id: str = Field(min_length=36, max_length=36)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def require_reason_for_negative_rating(self):
        if self.rating <= 2 and not self.comment.strip():
            raise ValueError("A reason is required for an unsatisfactory rating")
        return self


class SubmitResponse(BaseModel):
    run_id: str
    status: str
    decision: str | None = None
    domain: str | None = None
    correlation_id: str | None = None
    provider: str | None = None
    idempotent_replay: bool = False


class RunResponse(BaseModel):
    run_id: str
    status: str
    decision: str
    prompt_version: str
    created_at: datetime
    completed_at: datetime | None = None
    result: dict[str, Any] = Field(default_factory=dict)


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    decision: str


class RunHistoryItem(BaseModel):
    run_id: str
    status: str
    decision: str
    prompt_version: str
    created_at: datetime
    completed_at: datetime | None = None


class RunHistoryResponse(BaseModel):
    runs: list[RunHistoryItem]


class TraceEventResponse(BaseModel):
    agent: str
    event: str
    detail: dict[str, Any] = Field(default_factory=dict)
    elapsed_ms: float = Field(ge=0)
    created_at: datetime


class TraceResponse(BaseModel):
    run_id: str
    events: list[TraceEventResponse]


class FeedbackResponse(BaseModel):
    id: str
    accepted: bool


class HealthResponse(BaseModel):
    status: str
    provider: str
    corpus: str


class ReadinessResponse(BaseModel):
    status: str
    legal_corpus_ready: bool
    mode: str


class FeedbackSummaryResponse(BaseModel):
    count: int
    average_rating: float | None = None
    rating_counts: dict[str, int]


class RuntimeSettingsResponse(BaseModel):
    app_env: str
    provider: str
    model: str | None = None
    prompt_version: str
    langsmith_tracing: bool
    otel_exporter_configured: bool
    database_backend: str
    embedding_model_configured: bool


class ProviderHealthResponse(BaseModel):
    provider: str
    model: str | None = None
    mock_mode_active: bool
    tracing_enabled: bool
    tracing_project: str
    langsmith_key_configured: bool
    last_probe_success: bool | None = None
    last_probe_at: datetime | None = None


class ProviderProbeResponse(BaseModel):
    provider: str
    model: str | None = None
    status: Literal["connected", "mock", "failed"]
    connection_attempted: bool
    last_request_succeeded: bool
    response_received: bool = False
    failure_type: str | None = None
    failure_code: str | None = None
    failure_status_code: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class ToolCallOutput(BaseModel):
    tool: str
    query: str
    latency_ms: float = Field(ge=0)
    chunk_ids: list[str] = Field(default_factory=list)


class ResearchOutput(BaseModel):
    passages: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[ToolCallOutput] = Field(default_factory=list)
    strategy: str
    retry_count: int = Field(default=0, ge=0, le=1)
    request_fields: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class VerificationOutput(BaseModel):
    status: Literal[
        "VERIFIED", "INSUFFICIENT_EVIDENCE", "REQUIRES_MORE_INFORMATION", "ESCALATE"
    ]
    verified: bool
    reasons: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    excluded: list[dict[str, str]] = Field(default_factory=list)
